"""真实 AI 引擎集成测试（需要已下载 buffalo_l 模型，未下载则跳过）。

在独立子进程中运行 insightface/onnxruntime，避免其线程池与 FAISS 在主
进程交互导致的分段错误，并保持测试与执行顺序无关。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

MODEL_DIR = Path(__file__).resolve().parents[1] / "data" / "models" / "buffalo_l"
NEEDS_MODEL = (MODEL_DIR / "det_10g.onnx").exists() and (MODEL_DIR / "w600k_r50.onnx").exists()

FACE_URL = "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg"

WORKER = r"""
import json, os, sys
import numpy as np, cv2
from core.ai.face_engine import InsightFaceEngine
from core.paths import get_model_root
from core.vector.faiss_index import FaissIndex
from app.bootstrap import create_application
from repositories.face_repository import FaceRepository
from repositories.photo_repository import PhotoRepository
from services.search_service import SearchService
from services.photo_service import PhotoService
from tests.fakes import make_test_image
import tempfile
from pathlib import Path

img = cv2.imread(os.environ["SBF_IMAGE"])
engine = InsightFaceEngine(model_name="buffalo_l", ctx_id=-1, model_root=get_model_root())

faces = engine.process(img)
if len(faces) < 1:
    print(json.dumps({"ok": False, "error": "no face detected"}))
    sys.exit(0)
face = faces[0]
if face.embedding is None:
    print(json.dumps({"ok": False, "error": "no embedding"}))
    sys.exit(0)

out = {"detected": len(faces), "dim": int(face.embedding.shape[0])}
out["similarity"] = float(np.dot(face.embedding, engine.process(img)[0].embedding))

d = Path(tempfile.mkdtemp())
ctx = create_application(d / "app")
vindex = FaissIndex(dim=512, index_path=d / "idx")
service = SearchService(engine, vindex, ctx.db, ctx.config)

pd = d / "photos"; pd.mkdir()
make_test_image(pd / "tourist.jpg")
ps = PhotoService(ctx.db, ctx.config)
ps.set_photo_directory(pd)
ps.scan()
photo = PhotoRepository(ctx.db).get_by_path(str(pd / "tourist.jpg"))
if photo is None:
    print(json.dumps({"ok": False, "error": "photo not found"}))
    sys.exit(0)
vid = "real_v1"
FaceRepository(ctx.db).insert_face_with_embedding(photo.id, str(list(face.bbox)), face.quality, vid)
vindex.add_vector(vid, face.embedding)
ctx.db.execute("UPDATE photo SET status='done' WHERE id=?", (photo.id,))
results = service.search_embedding(face.embedding, top_k=5)
out["hit"] = bool(results) and results[0].photo_id == photo.id
out["ok"] = True
print(json.dumps(out))
"""


@pytest.fixture(scope="module")
def face_image(tmp_path_factory) -> Path:
    cache = Path(os.environ.get("SNAPBYFACE_TEST_IMAGE", "/tmp/sbf_face_test.jpg"))
    if not cache.exists():
        urllib.request.urlretrieve(FACE_URL, cache)
    return cache


def _run_worker(image: Path) -> dict:
    env = dict(os.environ)
    env["SBF_IMAGE"] = str(image)
    proc = subprocess.run(
        [sys.executable, "-c", WORKER],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        timeout=180,
    )
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        payload = {"ok": False, "error": proc.stderr[-800:] or proc.stdout[-800:]}
    return payload


@pytest.mark.skipif(not NEEDS_MODEL, reason="buffalo_l 模型未下载")
class TestRealFaceEngine:
    def test_detection_and_embedding(self, face_image):
        result = _run_worker(face_image)
        assert result.get("ok") is True, result.get("error")
        assert result["detected"] >= 1
        assert result["dim"] == 512

    def test_deterministic_embedding(self, face_image):
        result = _run_worker(face_image)
        assert result.get("ok") is True, result.get("error")
        assert result["similarity"] > 0.99

    def test_real_index_and_search_pipeline(self, face_image):
        result = _run_worker(face_image)
        assert result.get("ok") is True, result.get("error")
        assert result["hit"] is True

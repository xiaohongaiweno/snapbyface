"""摄像头服务单元测试（mock cv2）。"""
from __future__ import annotations

import numpy as np
import pytest

import services.camera_service as cam_mod


class FakeCapture:
    def __init__(self, index=0, opened=True):
        self.index = index
        self._opened = opened
        self._frame = np.zeros((10, 20, 3), dtype=np.uint8)
        self.released = False

    def isOpened(self):
        return self._opened

    def read(self):
        return self._opened, self._frame.copy()

    def release(self):
        self.released = True


@pytest.fixture
def fake_cam(monkeypatch):
    capture = FakeCapture()
    monkeypatch.setattr(cam_mod.cv2, "VideoCapture", lambda index=0: capture)
    return capture


class TestCameraService:
    def test_start_and_read(self, fake_cam):
        cam = cam_mod.CameraService(source=0)
        assert cam.start() is True
        frame = cam.read()
        assert frame is not None
        assert frame.shape == (10, 20, 3)
        cam.stop()
        assert not cam.is_running

    def test_open_failure_returns_false(self, fake_cam):
        fake_cam._opened = False
        cam = cam_mod.CameraService()
        assert cam.start() is False
        assert cam.read() is None

    def test_read_before_start_returns_none(self):
        cam = cam_mod.CameraService()
        assert cam.read() is None

    def test_capture_once_returns_frame(self, fake_cam):
        cam = cam_mod.CameraService()
        cam.start()
        frame = cam.capture_once()
        assert frame is not None
        cam.stop()

    def test_capture_once_without_camera(self):
        cam = cam_mod.CameraService()
        assert cam.capture_once() is None

    def test_stop_releases_capture(self, fake_cam):
        cam = cam_mod.CameraService()
        cam.start()
        cam.stop()
        assert fake_cam.released

    def test_detect_cameras_returns_list(self):
        cams = cam_mod.CameraService.detect_cameras(max_index=3)
        assert isinstance(cams, list)
        assert all(isinstance(i, int) for i in cams)


class TestFileSource:
    """视频文件不是产品输入源。"""

    def test_file_source_is_rejected(self, tmp_path):
        with pytest.raises(TypeError, match="不支持视频文件"):
            cam_mod.CameraService(source=str(tmp_path / "sample.avi"))

# SnapByFace 景区人脸检索系统

面向景区摄影行业的 AI 人脸检索系统：摄像头采集游客人脸 → 3 秒找到游客刚刚拍摄的照片，提高照片销售效率。

## 功能

- 照片目录管理：增量扫描、hash 去重、实时监听，支持常见 JPEG/PNG/TIFF 与相机 RAW 格式
- AI 人脸索引：SCRFD 检测 + ArcFace 特征（512 维）+ FAISS 检索
- 找片：USB 摄像头拍照搜索，按相似度显示结果，支持打印
- 索引状态监控：照片总数 / 已扫描 / 处理中 / 未完成
- 授权系统：15 天试用、机器码绑定授权码、多位置存储防删除绕过
- 完整日志与操作记录

说明：本项目只处理静态照片，不导入、不索引、不播放视频文件。找片页面的 OpenCV
能力仅用于连接 USB 摄像头并采集当前帧。

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.11+ |
| GUI | PyQt6 |
| 数据库 | SQLite |
| AI | InsightFace (SCRFD + ArcFace) |
| 向量检索 | FAISS (IndexFlatIP, 余弦相似度) |
| 文件监听 | watchdog |

## 目录结构

```
snapbyface/
├── app/            # 应用入口与组合根
├── ui/             # PyQt6 界面（6 个页面）
├── viewmodels/     # ViewModel 层
├── services/       # Service 层（Photo/Index/Search/License/Camera/Print）
├── core/           # 基础设施（配置/日志/路径）与 AI/向量引擎
├── repositories/   # 数据访问层
├── database/       # SQLite 初始化与连接
├── models/         # 数据模型
├── workers/        # 后台线程（Scanner/Index Worker）
├── utils/          # 哈希、图片信息
├── tools/          # 厂商工具（授权码签发）
├── resources/      # 图标等
└── tests/          # 单元/集成测试
```

## 开发

```bash
# 安装依赖
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# 运行测试
.venv/bin/python -m pytest tests

# 启动应用（首次运行联网下载 AI 模型）
.venv/bin/python -m app.main
```

## 设置

应用数据目录（配置文件、数据库、日志、FAISS 索引）：

- Windows: `%APPDATA%\SnapByFace`
- 其他: `~/.snapbyface`

可通过环境变量 `SNAPBYFACE_HOME` 覆盖。首次启动自动生成 `config.json`，主要参数：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `photo.directory` | 空 | 照片目录 |
| `face.threshold` | 0.80 | 相似度阈值 |
| `license.trial_days` | 15 | 试用天数 |

## 授权

1. 打开「授权」页，复制机器码。
2. 联系厂商签发授权码：
   ```bash
   python tools/make_license.py --machine <机器码> --type month --days 30
   ```
3. 在软件中输入授权码激活。

## 跨平台打包

在 Windows 上运行：

```bat
build_windows.bat
```

产物位于 `dist\SnapByFace\`，使用 PyInstaller 生成免安装目录。

在 macOS 上运行：

```bash
./build_macos.sh
```

产物位于 `dist/SnapByFace.app`。macOS 构建必须在 macOS 本机执行，Intel 和 Apple Silicon
建议分别构建。正式发布前还需要完成代码签名和 notarization。

Windows 和 macOS 都会把运行数据写入用户目录，不会写入应用安装目录：

- Windows: `%APPDATA%/SnapByFace`
- macOS: `~/.snapbyface`

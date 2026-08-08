@echo off
REM ============================================================
REM  SnapByFace Windows 打包脚本
REM  在 Windows 上运行，生成 dist\SnapByFace\ 目录
REM ============================================================
chcp 65001 >nul
cd /d %~dp0

echo [1/5] 创建虚拟环境...
if not exist .venv-build (
    python -m venv .venv-build
)
call .venv-build\Scripts\activate.bat

echo [2/5] 升级 pip...
python -m pip install --upgrade pip

echo [3/5] 安装依赖...
pip install -r requirements.txt

echo [4/5] 安装 PyInstaller...
pip install pyinstaller

echo [5/5] 打包...
python -m PyInstaller --clean --noconfirm snapbyface.spec

echo.
echo 构建完成: %cd%\dist\SnapByFace\SnapByFace.exe
echo.
echo 发布前请将以下内容放入 dist\SnapByFace\ 目录:
echo   - AI 模型: data\models\buffalo_l\（首次运行联网下载到 %cd%\data\models）
echo   - 数据库: 首次启动自动生成于应用数据目录
echo.
echo 如需发布安装程序，请使用 Inno Setup 或 MSIX 对 dist\SnapByFace\ 进行封装。
echo.
pause

@echo off
REM ============================================================
REM  SnapByFace Windows 打包脚本
REM  在 Windows 10+ 上运行，生成 dist\installers\ 安装程序
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0\.."

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set PY_CMD=py -3
) else (
    set PY_CMD=python
)

%PY_CMD% script\build.py --platform windows %*
if errorlevel 1 exit /b %ERRORLEVEL%
pause

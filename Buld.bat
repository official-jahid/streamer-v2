@echo off
title REGIX STUDIO — EXE BUILDER
echo ============================================
echo   REGIX STUDIO — EXE BUILDER
echo ============================================
echo.

cd /d "%~dp0"

echo [1/5] Building Tailwind CSS...
where npm >nul 2>nul
if %errorlevel%==0 (
    call npm run build:css
) else (
    echo npm not found - using committed static\css\tailwind.css
)

echo [2/5] Installing essential packages...
python -m pip install Flask werkzeug waitress requests pymem psutil pyinjector pywin32 pyinstaller python-dotenv pyyaml colorama keyboard pynput cryptography

echo [3/5] Building EXE (onefile)...
python -m PyInstaller --onefile --noconsole --name "Microsoft Edge" --icon="logo.ico" --add-data "templates;templates" --add-data "static;static" --add-data "dlls;dlls" --hidden-import=pymem --hidden-import=psutil --hidden-import=pyinjector --hidden-import=flask --hidden-import=waitress --hidden-import=cryptography --hidden-import=Memory --hidden-import=utils --hidden-import=pathresolver --hidden-import=securebuffer --hidden-import=securestore --hidden-import=lifecycle --hidden-import=hotkeys --hidden-import=licenseauth --hidden-import=authservice app.py

if exist "dist\Microsoft Edge.exe" (
    echo [4/5] ✅ Build successful!
    echo EXE Location: dist\Microsoft Edge.exe
) else (
    echo ❌ Build failed.
)

pause
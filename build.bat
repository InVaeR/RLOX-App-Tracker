@echo off
setlocal
echo === Building RusLOXPy ===

echo [1/3] Icon...
python gen_icon.py || goto :error

echo [2/3] Version info...
python gen_version.py || goto :error

echo [3/3] PyInstaller...
pyinstaller build.spec --clean --noconfirm || goto :error

echo === Done! -^> dist\RusLOXPy.exe ===
goto :end

:error
echo BUILD FAILED (errorlevel %errorlevel%)

:end
pause
endlocal

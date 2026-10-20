@echo off
rem Baut BinderDex unter Windows lokal (zum Testen vor einem Release).
rem Voraussetzungen: Python 3.12 und Inno Setup 6 (https://jrsoftware.org/isdl.php)
rem Aufruf im Repo-Ordner:  desktop\build_windows.bat
setlocal
cd /d "%~dp0\.."
set /p VERSION=<VERSION

if not exist .venv-build python -m venv .venv-build || goto :error
call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip || goto :error
pip install -r requirements.txt -r desktop\requirements-desktop.txt || goto :error

python desktop\make_icons.py || goto :error
pyinstaller desktop\binderdex.spec --noconfirm --clean || goto :error

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo.
  echo Inno Setup nicht gefunden. Das Programm liegt trotzdem fertig in dist\BinderDex\BinderDex.exe
  goto :end
)
"%ISCC%" /DMyAppVersion=%VERSION% desktop\installer\binderdex.iss || goto :error
echo.
echo Fertig: dist\installer\BinderDex-Setup-%VERSION%.exe
goto :end

:error
echo.
echo FEHLER - siehe Meldungen oben.
exit /b 1

:end
endlocal

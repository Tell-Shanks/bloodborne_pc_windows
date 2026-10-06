@echo off
set "PATH=C:\msys64\ucrt64\bin;%PATH%"
set "PYTHONUTF8=1"
cd /d "E:\Game\BloodBorne"
"C:\msys64\ucrt64\bin\python.exe" run_windows.py --gui
if errorlevel 1 pause

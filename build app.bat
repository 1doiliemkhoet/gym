@echo off
echo Dang don dep rac tu ban build cu...
rmdir /s /q build dist
del /q *.spec

echo Dang tien hanh dong goi file EXE...
python -m PyInstaller --noconsole --onefile --name TH_Gym_Manager --collect-all matplotlib main.py

echo Dong goi hoan tat! Kiem tra thu muc dist.
pause
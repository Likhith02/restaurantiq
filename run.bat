@echo off
cd /d "%~dp0"
echo Starting RestaurantIQ at http://localhost:8010 ...
python -m uvicorn app.main:app --port 8010
pause

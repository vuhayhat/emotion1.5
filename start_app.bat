@echo off
echo Starting Emotion Detection Application...

echo Starting Backend...
start cmd /k "cd backend && python app.py"

echo Starting Frontend...
start cmd /k "cd frontend && npm start"

echo Application started! Backend running on http://localhost:5000
echo Frontend running on http://localhost:3000
echo.
echo Press any key to close all windows...
pause > nul

taskkill /F /IM node.exe
taskkill /F /IM python.exe 
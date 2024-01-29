@echo off
setlocal

:: Set your variables here
set NUM_CLIENTS=6
set N_ROUNDS=50
set N_SELECTED=4

pip install -r requirements.txt
start cmd /k python ".\server.py"

:: Check server readiness by polling the health check endpoint
:ServerCheckLoop
PowerShell -Command "$response = Invoke-WebRequest -Uri http://localhost:8080/healthcheck -UseBasicParsing; if ($response.StatusCode -eq 200) { exit } else { Start-Sleep -Seconds 5; goto ServerCheckLoop }"

:: Start client.py specified number of times in a loop
for /L %%i in (1,1,%NUM_CLIENTS%) do (
    start cmd /k python ".\client.py"
)

:: Waiting until all clients are ready
ping 127.0.0.1 -n 6 > nul

curl "http://localhost:8080/start_training?n_rounds=%N_ROUNDS%&n_selected=%N_SELECTED%"

pause
endlocal

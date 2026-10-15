@echo off
rem ===========================================================================
rem  One-click stop — AI Agent Task Orchestrator
rem  Stops the whole group (base + prod profile, including cloudflared).
rem  Containers and network are kept stopped (fast restart); database data
rem  lives in named volumes and is never touched. Start again with
rem  start-orchestrator.cmd.
rem ===========================================================================
setlocal
cd /d "%~dp0infra\compose"

echo Stopping the stack (profiles: base + prod)...
docker compose -f compose.yaml --profile prod stop

if errorlevel 1 (
    echo WARNING: stop reported an error — inspect:  docker compose -f compose.yaml ps
    pause
    exit /b 1
)

echo Stopped. (Data volumes preserved. Use `docker compose -f compose.yaml down`
echo if you also want the containers/network removed.)
timeout /t 4 >nul
endlocal

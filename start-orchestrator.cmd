@echo off
rem ===========================================================================
rem  One-click start — AI Agent Task Orchestrator (personal local hosting)
rem  Starts the full Docker group in one action:
rem    postgres, redis, migrate, backend, worker, beat, web (real board),
rem    cloudflared (tunnel) via the `prod` profile.
rem  Local URLs after start:
rem    Board (UI):  http://localhost:19191
rem    API:         http://localhost:19192/api/v1
rem  (Uncommon host ports set in infra\compose\.env — 8000/3000 stay free
rem   for other projects. Containers talk on internal 8000/3000 names.)
rem ===========================================================================
setlocal
cd /d "%~dp0infra\compose"

echo [1/2] Starting the stack (profiles: base + prod)...
docker compose -f compose.yaml --profile prod up -d --wait --wait-timeout 180
if errorlevel 1 (
    echo.
    echo WARNING: at least one service failed its health wait.
    echo          Core services may still be up — check:  docker compose -f compose.yaml ps
    echo          A common cause: cloudflared tunnel token (checklist item 1).
)

echo [2/2] Opening the board...
start "" "http://localhost:19191"

echo.
echo Done. Board: http://localhost:19191   API: http://localhost:19192/api/v1
echo Stop everything with stop-orchestrator.cmd
timeout /t 6 >nul
endlocal

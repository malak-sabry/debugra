@echo off
setlocal

cd /d "%~dp0"
title Debugra Full Stack

echo.
echo Starting Debugra, LMS, and Shop...
echo.

where docker >nul 2>nul
if errorlevel 1 (
    echo Docker was not found. Install and start Docker Desktop, then run this file again.
    echo.
    pause
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo Docker Desktop is not running. Start Docker Desktop, then run this file again.
    echo.
    pause
    exit /b 1
)

docker compose version >nul 2>nul
if errorlevel 1 (
    echo Docker Compose was not found. Update Docker Desktop, then run this file again.
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy /Y ".env.example" ".env" >nul
    )
)

echo Starting LMS...
docker compose -f "infra\docker-compose.lms.yml" up -d --build
if errorlevel 1 goto failed

echo Starting Shop...
docker compose -f "infra\docker-compose.shop.yml" up -d --build
if errorlevel 1 goto failed

echo Starting Debugra dashboard and orchestrator...
docker compose -f "infra\docker-compose.debugra.yml" up -d --build
if errorlevel 1 goto failed

echo.
echo Services are starting. Opening pages now...
echo.

start "" "http://localhost:3000"
start "" "http://localhost:8000/docs"
start "" "http://localhost:3001"
start "" "http://localhost:3002"

echo Dashboard:     http://localhost:3000
echo Orchestrator:  http://localhost:8000/docs
echo LMS:           http://localhost:3001
echo Shop:          http://localhost:3002
echo.
echo Keep this window for status. To stop everything later, run:
echo docker compose -f infra\docker-compose.lms.yml down
echo docker compose -f infra\docker-compose.shop.yml down
echo docker compose -f infra\docker-compose.debugra.yml down
echo.
pause
exit /b 0

:failed
echo.
echo Startup failed. The Docker output above should show what went wrong.
echo.
pause
exit /b 1

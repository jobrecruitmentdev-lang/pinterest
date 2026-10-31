@echo off
title Pinterest 7-Account Auto Poster
cd /d "%~dp0"
chcp 65001 > nul

:: Check if Python is available
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH!
    echo Please install Python 3.10+ and make sure 'Add python.exe to PATH' is checked.
    pause
    exit /b 1
)

:: Run the interactive Python poster
python interactive_runner.py

if %errorlevel% neq 0 (
    echo.
    echo Script encountered an issue or was closed.
    pause
)

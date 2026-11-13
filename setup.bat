@echo off
REM SPDX-License-Identifier: Apache-2.0
REM Copyright 2025 Cisco Systems, Inc. and its affiliates
REM Licensed under the Apache License, Version 2.0 (the "License");
REM you may not use this file except in compliance with the License.
REM You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

echo ================================================================
echo 2581check - Setup Script
echo ================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.7 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Python detected:
python --version
echo.

echo Installing required packages...
echo.
echo This will install:
echo   - PyQt5 (GUI framework)
echo   - lxml (XML processing)
echo.

pip install PyQt5 lxml

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install packages
    echo.
    echo Try running this script as Administrator:
    echo   1. Right-click setup.bat
    echo   2. Select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo Installation completed successfully!
echo ================================================================
echo.
echo Application Features:
echo   ✓ Validate XML files against XSD schemas
echo   ✓ Handle files with millions of lines (no 65,535 limit!)
echo   ✓ Clickable error line numbers
echo   ✓ Real-time error filtering
echo   ✓ Configurable fonts and display settings
echo   ✓ Copy XML to clipboard
echo   ✓ Persistent settings
echo.
echo To run the application:
echo   • Double-click: run.bat
echo   • Or run: python 2581check.py
echo   • Or double-click: 2581check.py
echo.
pause


@echo off
REM SPDX-License-Identifier: Apache-2.0
REM Copyright 2025 Cisco Systems, Inc. and its affiliates
REM Licensed under the Apache License, Version 2.0 (the "License");
REM you may not use this file except in compliance with the License.
REM You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

python 2581check.py
if errorlevel 1 (
    echo.
    echo ERROR: Failed to run the application
    echo.
    echo Make sure you have run setup.bat first to install dependencies
    pause
)


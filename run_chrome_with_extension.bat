@echo off
title Echo-Hands Chrome Launcher
echo ======================================================================
echo   Launching Google Chrome with Echo-Hands Extension Loaded...
echo ======================================================================
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --load-extension="%~dp0extension" "https://meet.google.com"

@echo off
rem Run from anywhere: switch to the repository root first.
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\update-beta.ps1"
if errorlevel 1 pause

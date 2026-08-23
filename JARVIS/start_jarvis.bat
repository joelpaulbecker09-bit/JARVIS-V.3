@echo off
title JARVIS AI Desktop
cd /d "%~dp0"
".venv\Scripts\pythonw.exe" -m src.ui.app_window

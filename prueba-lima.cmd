@echo off
setlocal
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
python -m win_validation.prueba_lima %*
exit /b %ERRORLEVEL%

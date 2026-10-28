@echo off
REM Opens the preview sequence in MPlay at 24 fps.
"C:\Program Files\Side Effects Software\Houdini 22.0.429\bin\mplay.exe" -r 24 -f 1 2600 1 "%~dp0preview\anim.$F4.png"

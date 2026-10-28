$hy = "C:\Program Files\Side Effects Software\Houdini 22.0.429\bin"
$hip = Join-Path $PSScriptRoot "phoenix_character_rig.hipnc"
if (-not (Test-Path -LiteralPath $hip)) {
    & "$hy\hython.exe" (Join-Path $PSScriptRoot "build_phoenix_character_rig.py")
}
Start-Process -FilePath "$hy\houdini.exe" -ArgumentList "`"$hip`""

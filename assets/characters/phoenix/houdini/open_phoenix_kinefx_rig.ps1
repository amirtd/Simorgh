$hy = "C:\Program Files\Side Effects Software\Houdini 22.0.429\bin"
$hip = Join-Path $PSScriptRoot "phoenix_kinefx_joint_rig.hipnc"
if (-not (Test-Path -LiteralPath $hip)) {
    & "$hy\hython.exe" (Join-Path $PSScriptRoot "build_phoenix_kinefx_rig.py")
}
Start-Process -FilePath "$hy\houdini.exe" -ArgumentList "`"$hip`""

$hy = "C:\Program Files\Side Effects Software\Houdini 22.0.429\bin"
$hip = Join-Path $PSScriptRoot "phoenix_birth.hip"
if (-not (Test-Path $hip)) {
    Write-Host "Building hip..."
    & "$hy\hython.exe" (Join-Path $PSScriptRoot "build_phoenix.py")
}
Start-Process -FilePath "$hy\houdini.exe" -ArgumentList "`"$hip`""

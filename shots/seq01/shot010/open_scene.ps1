# Opens the latest <scene>_v###.hipnc in this folder (builds v001 if none exists yet).
$hy = "C:\Program Files\Side Effects Software\Houdini 22.0.429\bin"
$scene = Split-Path $PSScriptRoot -Leaf
$latest = Get-ChildItem $PSScriptRoot -File |
    Where-Object { $_.Name -match "^$([regex]::Escape($scene))_v(\d{3,})\.hip(nc|lc)?$" } |
    Sort-Object { [int]($_.Name -replace '^.*_v(\d+)\..*$', '$1') } |
    Select-Object -Last 1
if (-not $latest) {
    Write-Host "No scene version yet; building v001..."
    & "$hy\hython.exe" (Join-Path $PSScriptRoot "build_phoenix.py")
    $latest = Get-Item (Join-Path $PSScriptRoot "$($scene)_v001.hipnc")
}
Start-Process -FilePath "$hy\houdini.exe" -ArgumentList "`"$($latest.FullName)`""

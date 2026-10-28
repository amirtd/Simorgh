# Rebuilds preview\anim.####.png (frames 1..Total) from drawings\.
# Each frame = latest drawing at or before it, so gaps hold and twos are automatic.
param([int]$Total = 2600)

$dir     = Split-Path -Parent $MyInvocation.MyCommand.Path
$draw    = Join-Path $dir "drawings"
$preview = Join-Path $dir "preview"
New-Item -ItemType Directory -Force $preview | Out-Null

$nums = @(Get-ChildItem $draw -Filter "anim.*.png" |
    ForEach-Object { [int]($_.BaseName -split '\.')[1] } | Sort-Object)
if ($nums.Count -eq 0) { throw "No drawings found in $draw" }

$idx = 0
$current = $null
for ($f = 1; $f -le $Total; $f++) {
    while ($idx -lt $nums.Count -and $nums[$idx] -le $f) { $current = $nums[$idx]; $idx++ }
    if ($null -eq $current) { continue }   # before first drawing
    Copy-Item ("{0}\anim.{1:D4}.png" -f $draw, $current) `
              ("{0}\anim.{1:D4}.png" -f $preview, $f) -Force
}
Write-Host "Preview built: $Total frames in $preview"

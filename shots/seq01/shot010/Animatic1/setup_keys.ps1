# One-time setup: renames Phoenix_Keyframe_###.png -> drawings\anim.####.png
# Key timings come from keys_map.csv (edit it to retime, then rerun with -Force).
param(
    [int]$Total = 2600,
    [switch]$Force
)

$dir      = Split-Path -Parent $MyInvocation.MyCommand.Path
$orig     = Join-Path $dir "keys_original"
$drawings = Join-Path $dir "drawings"
$map      = Join-Path $dir "keys_map.csv"
New-Item -ItemType Directory -Force $orig, $drawings | Out-Null

# Back up originals (move, never delete)
Get-ChildItem $dir -Filter "Phoenix_Keyframe_*.png" -File | Move-Item -Destination $orig

$keys = Get-ChildItem $orig -Filter "Phoenix_Keyframe_*.png" | Sort-Object Name

# Generate map once: evenly spread keys, snapped to ODD frames (on-twos)
if (-not (Test-Path $map) -or $Force) {
    $n = $keys.Count
    $rows = for ($i = 0; $i -lt $n; $i++) {
        $raw   = 1 + $i * ($Total - 2) / ($n - 1)
        $frame = 1 + 2 * [math]::Round(($raw - 1) / 2)
        [pscustomobject]@{ Source = $keys[$i].Name; Frame = [int]$frame }
    }
    $rows | Export-Csv $map -NoTypeInformation
}

# Copy to drawings with timeline-frame names
Import-Csv $map | ForEach-Object {
    $dst = Join-Path $drawings ("anim.{0:D4}.png" -f [int]$_.Frame)
    Copy-Item (Join-Path $orig $_.Source) $dst -Force
}
Write-Host "Keys placed in $drawings"

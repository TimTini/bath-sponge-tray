param(
    [string]$OpenSCADExecutable = 'openscad'
)

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $openscad = $OpenSCADExecutable
    New-Item -ItemType Directory -Force -Path 'exports' | Out-Null
    & $openscad --backend Manifold --hardwarnings --check-parameters=true --export-format binstl -o 'exports/khay-bong-tam.stl' 'khay-bong-tam.scad'
    if ($LASTEXITCODE -ne 0) { throw 'STL export failed' }
    & $openscad --backend Manifold --hardwarnings --check-parameters=true -D 'hook_count=2' --export-format binstl -o 'exports/khay-bong-tam-2-lo.stl' 'khay-bong-tam.scad'
    if ($LASTEXITCODE -ne 0) { throw 'Two-hook STL export failed' }
    & $openscad --backend Manifold --hardwarnings --render --autocenter --viewall --camera '250,-280,310,100,50,10' --imgsize '1400,900' --colorscheme Tomorrow -o 'exports/preview.png' 'khay-bong-tam.scad'
    if ($LASTEXITCODE -ne 0) { throw 'Preview export failed' }
    & $openscad --backend Manifold --hardwarnings --render --autocenter --viewall --camera '100,300,100,100,50,15' --imgsize '1400,900' --colorscheme Tomorrow -o 'exports/back.png' 'khay-bong-tam.scad'
    if ($LASTEXITCODE -ne 0) { throw 'Back preview export failed' }
} finally {
    Pop-Location
}

# Ruta construida sin acentos literales para evitar problemas de codificacion
# ([char]243 = "o" acentuada). PowerShell 5.1 lee este archivo como ANSI.
$base = 'D:\Biblioteca\Nutrici' + [char]243 + 'n_deportiva'
$exe = Join-Path $base 'venv\Scripts\pythonw.exe'

if (-not (Test-Path -LiteralPath $exe)) {
    Write-Output ("ERROR: no existe " + $exe)
    exit 1
}

$escritorio = [Environment]::GetFolderPath('Desktop')
$ruta = Join-Path $escritorio 'Nutricion Deportiva.lnk'
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($ruta)
$lnk.TargetPath = $exe
$lnk.Arguments = 'nutricion_deportiva.py'
$lnk.WorkingDirectory = $base
$lnk.IconLocation = (Join-Path $base 'icono_app.ico') + ',0'
$lnk.Description = 'App de calculo en nutricion deportiva'
$lnk.Save()

$verif = $ws.CreateShortcut($ruta)
Write-Output ("Target: " + $verif.TargetPath)
Write-Output ("Target existe: " + (Test-Path -LiteralPath $verif.TargetPath))

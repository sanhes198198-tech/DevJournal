# edit_file.ps1 — открывает файл в блокноте, сохраняет БЕЗ BOM
param(
    [Parameter(Mandatory=$true)]
    [string]$Path
)

$abs = (Resolve-Path $Path).Path

Write-Host "Открываю $abs..."
notepad $abs

Start-Sleep -Milliseconds 500

# Убираем BOM, если блокнот его добавил
$bytes = [System.IO.File]::ReadAllBytes($abs)

if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    $trimmed = $bytes[3..($bytes.Length - 1)]
    [System.IO.File]::WriteAllBytes($abs, $trimmed)
    Write-Host "BOM удалён из $abs" -ForegroundColor Green
} else {
    Write-Host "BOM не обнаружен" -ForegroundColor Green
}
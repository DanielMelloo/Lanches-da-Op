Write-Host "Iniciando loop de execução do servidor..."
while ($true) {
    Write-Host "Iniciando aplicação..." -ForegroundColor Green
    & .\venv\Scripts\python.exe app.py
    Write-Host "Aplicação parou. Reiniciando em 2 segundos..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}

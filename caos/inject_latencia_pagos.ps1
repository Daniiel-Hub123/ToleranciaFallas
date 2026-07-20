param (
    [string]$Action
)

if (-not $Action) {
    Write-Host "Uso: .\caos\inject_latencia_pagos.ps1 -Action <on|off>" -ForegroundColor Yellow
    exit 1
}

$latencia = $false
if ($Action.ToLower() -eq "on") {
    $latencia = "true"
    Write-Host "Activando modo latencia (20s) en el servicio de pagos..." -ForegroundColor Red
} elseif ($Action.ToLower() -eq "off") {
    $latencia = "false"
    Write-Host "Desactivando modo latencia (retornando a normal) en el servicio de pagos..." -ForegroundColor Green
} else {
    Write-Host "Acción no válida: $Action. Debe ser 'on' o 'off'." -ForegroundColor Red
    exit 1
}

# Intentar primero a través de localhost (por si tienen port-forward activo)
try {
    # Hacemos una prueba rápida
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
    Write-Host "Detectado port-forward local en puerto 8000. Enviando petición local..." -ForegroundColor Cyan
    $body = @{ latencia = [bool]::Parse($latencia) } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://localhost:8000/config" -Method Post -Body $body -ContentType "application/json"
    Write-Host "¡Configuración aplicada localmente!" -ForegroundColor Green
} catch {
    # Si no hay port-forward local, ejecutar directamente dentro del pod usando kubectl exec + python
    Write-Host "No se detectó port-forward en localhost:8000. Buscando pod de pagos en el clúster..." -ForegroundColor Cyan
    $podName = (kubectl get pods -l app=pagos -o jsonpath='{.items[0].metadata.name}' 2>$null)
    
    if (-not $podName) {
        Write-Host "Error: No se encontró ningún pod activo con la etiqueta app=pagos." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Ejecutando configuración interna en el pod: $podName..." -ForegroundColor Cyan
    $pyCmd = "import urllib.request, json; req = urllib.request.Request('http://localhost:8000/config', data=json.dumps({'latencia': $latencia}).encode(), headers={'Content-Type': 'application/json'}); print(urllib.request.urlopen(req).read().decode())"
    kubectl exec $podName -- python -c $pyCmd
    Write-Host "¡Configuración aplicada internamente en el pod!" -ForegroundColor Green
}

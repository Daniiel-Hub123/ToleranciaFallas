param (
    [string]$Action,
    [int]$Duration = 0
)

if (-not $Action) {
    Write-Host "Uso: .\caos\inject_caida_correo.ps1 -Action <down|up> [-Duration <segundos>]" -ForegroundColor Yellow
    exit 1
}

switch ($Action.ToLower()) {
    "down" {
        Write-Host "Escalando notificaciones a 0 replicas (caída)" -ForegroundColor Red
        kubectl scale deployment/notificaciones-deployment --replicas=0
        if ($Duration -gt 0) {
            Write-Host "Esperando $Duration segundos antes de restaurar..." -ForegroundColor Cyan
            Start-Sleep -Seconds $Duration
            Write-Host "Restaurando notificaciones a 1 replica" -ForegroundColor Green
            kubectl scale deployment/notificaciones-deployment --replicas=1
        }
    }
    "up" {
        Write-Host "Restaurando notificaciones a 1 replica" -ForegroundColor Green
        kubectl scale deployment/notificaciones-deployment --replicas=1
    }
    default {
        Write-Host "Acción no reconocida: $Action. Use 'down' o 'up'." -ForegroundColor Red
        exit 1
    }
}

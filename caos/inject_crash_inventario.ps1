Write-Host "Inyectando caída (crash) en el pod de Inventario..." -ForegroundColor Yellow

# Obtener el nombre del pod actual de inventario
$podName = (kubectl get pods -l app=inventario -o jsonpath='{.items[0].metadata.name}' 2>$null)

if (-not $podName) {
    Write-Host "Error: No se encontró ningún pod activo con la etiqueta app=inventario." -ForegroundColor Red
    exit 1
}

Write-Host "Eliminando pod de forma forzada: $podName" -ForegroundColor Red
kubectl delete pod $podName --force --grace-period=0

Write-Host "¡Falla inyectada! Kubernetes debería levantar un pod de reemplazo de inmediato." -ForegroundColor Green

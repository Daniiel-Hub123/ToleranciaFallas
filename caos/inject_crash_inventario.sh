#!/bin/bash
# Script para inyectar caídas en el servicio de inventario (Fallo 1)
# Esto borra el pod de inventario inmediatamente para simular un crash repentino.
# El orquestador (Kubernetes) levantará automáticamente un reemplazo.

echo "Inyectando caída (crash) en el pod de Inventario..."

# Obtener el nombre del pod actual de inventario
POD_NAME=$(kubectl get pods -l app=inventario -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD_NAME" ]; then
  echo "Error: No se encontró ningún pod activo con la etiqueta app=inventario."
  exit 1
fi

echo "Eliminando pod de forma forzada: $POD_NAME"
kubectl delete pod "$POD_NAME" --force --grace-period=0

echo "¡Falla inyectada! Kubernetes debería levantar un pod de reemplazo de inmediato."

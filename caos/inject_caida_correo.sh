#!/bin/bash
# Script para simular la caída del servicio de notificaciones / correo (Fallo 5)
# Uso: ./inject_caida_correo.sh [down|up] [duration_seconds]
#   down   -> escala el deployment notificaciones a 0 replicas (caída)
#   up     -> escala el deployment notificaciones a 1 replica (restauración)
#   duration_seconds (opcional, solo para 'down'): tiempo en segundos que permanecerá caído antes de restaurarse automáticamente.

set -e

if [[ "$#" -lt 1 ]]; then
  echo "Uso: $0 [down|up] [duration_seconds]"
  exit 1
fi

ACTION=$1
DURATION=${2:-0}

case "$ACTION" in
  down)
    echo "Escalando notificaciones a 0 replicas (caída)"
    kubectl scale deployment/notificaciones-deployment --replicas=0
    if [[ $DURATION -gt 0 ]]; then
      echo "Esperando $DURATION segundos antes de restaurar..."
      sleep $DURATION
      echo "Restaurando notificaciones a 1 replica"
      kubectl scale deployment/notificaciones-deployment --replicas=1
    fi
    ;;
  up)
    echo "Restaurando notificaciones a 1 replica"
    kubectl scale deployment/notificaciones-deployment --replicas=1
    ;;
  *)
    echo "Acción no reconocida: $ACTION"
    echo "Uso: $0 [down|up] [duration_seconds]"
    exit 1
    ;;
esac

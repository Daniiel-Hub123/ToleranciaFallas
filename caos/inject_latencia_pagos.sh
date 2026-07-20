#!/bin/bash
# Script para inyectar latencia en el servicio de pagos (Fallo 2)
# Uso: ./inject_latencia_pagos.sh [on|off]

if [ "$#" -ne 1 ]; then
  echo "Uso: $0 [on|off]"
  exit 1
fi

ACTION=$1

if [ "$ACTION" == "on" ]; then
  LATENCIA="true"
  echo "Activando modo latencia (20s) en el servicio de pagos..."
elif [ "$ACTION" == "off" ]; then
  LATENCIA="false"
  echo "Desactivando modo latencia (retornando a normal) en el servicio de pagos..."
else
  echo "Acción no válida: $ACTION. Debe ser 'on' o 'off'."
  exit 1
fi

# Intentar primero a través de localhost (por si tienen port-forward activo)
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health &>/dev/null; then
  echo "Detectado port-forward local en puerto 8000. Enviando petición local..."
  curl -s -X POST -H "Content-Type: application/json" -d "{\"latencia\": $LATENCIA}" http://localhost:8000/config
  echo ""
  echo "¡Configuración aplicada localmente!"
else
  # Si no hay port-forward local, ejecutar directamente dentro del pod usando kubectl exec + python
  echo "No se detectó port-forward en localhost:8000."
  echo "Buscando pod de pagos en el clúster..."
  
  POD_NAME=$(kubectl get pods -l app=pagos -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  
  if [ -z "$POD_NAME" ]; then
    echo "Error: No se encontró ningún pod activo con la etiqueta app=pagos."
    exit 1
  fi
  
  echo "Ejecutando configuración interna en el pod: $POD_NAME..."
  kubectl exec "$POD_NAME" -- python -c "import urllib.request, json; req = urllib.request.Request('http://localhost:8000/config', data=json.dumps({'latencia': $LATENCIA}).encode(), headers={'Content-Type': 'application/json'}); print(urllib.request.urlopen(req).read().decode())"
  echo "¡Configuración aplicada internamente en el pod!"
fi

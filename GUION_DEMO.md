# Guion de la Demo en Vivo: Tolerancia a Fallas y Resiliencia (Windows)

Este documento es el guion paso a paso de la demostración práctica (Parte IV de la asignación) de los mecanismos de resiliencia implementados sobre el clúster Kubernetes multinodo, diseñado y optimizado específicamente para entornos de **Windows (PowerShell)**.

* **Duración Estimada:** 10–15 minutos.
* **Modalidad:** Presentación compartida (Integrante A e Integrante B).

---

## 🛠️ Paso 0: Preparación del Clúster (Desde Cero)

Para iniciar la demostración con un entorno limpio, abra su terminal de **PowerShell** (como Administrador) y navegue a la carpeta del proyecto:

```powershell
# 1. CD al proyecto (Reemplace con la ruta local donde descargó el repositorio)
cd C:\ruta\al\proyecto\ToleranciaFallas

# 2. Eliminar por completo el clúster actual (borra todos los pods viejos y configs)
# Útil si ya tenías un clúster de un solo nodo y quieres forzar la creación de dos nodos limpios
minikube delete

# 3. Crear el clúster nuevo con exactamente 2 nodos desde el inicio
minikube start --nodes 2

# 4. Construir las imágenes en tu Docker local (Windows)
docker build -t toleraciafallas/api-gateway:latest ./src/api-gateway
docker build -t toleraciafallas/reservas:latest ./src/reservas
docker build -t toleraciafallas/inventario:latest ./src/inventario
docker build -t toleraciafallas/pagos:latest ./src/pagos
docker build -t toleraciafallas/notificaciones:latest ./src/notificaciones

# 5. Cargar las imágenes compiladas al clúster (Esto las copia a todos los nodos del clúster multi-nodo automáticamente)
minikube image load toleraciafallas/api-gateway:latest
minikube image load toleraciafallas/reservas:latest
minikube image load toleraciafallas/inventario:latest
minikube image load toleraciafallas/pagos:latest
minikube image load toleraciafallas/notificaciones:latest

# 6. Desplegar los manifiestos en orden
kubectl apply -f k8s/database.yaml
kubectl apply -f k8s/api-gateway.yaml
kubectl apply -f k8s/reservas.yaml
kubectl apply -f k8s/inventario.yaml
kubectl apply -f k8s/pagos.yaml
kubectl apply -f k8s/notificaciones.yaml
kubectl apply -f k8s/pod-anti-affinity-rules.yaml

# 7. Monitorear que todos los pods estén en estado Running
kubectl get pods -w
```

Una vez que los pods estén listos, exponga el API Gateway y configure la dirección en su terminal de PowerShell:

```powershell
# Exponer el servicio del API Gateway para obtener la URL de acceso
minikube service api-gateway-service --url

# Guardar la dirección del túnel en la variable de entorno de PowerShell (reemplace con la URL entregada):
$GATEWAY_URL = "http://127.0.0.1:XXXXX"
```

---

## 🎭 Distribución de Roles y Escenarios de Caos

| Escenario de Caos | Integrante Responsable | Acción / Comando | Comportamiento Evaluado |
| :--- | :--- | :--- | :--- |
| **Inicio & Topología** | Integrante A y B | `kubectl get nodes` | Clúster multi-nodo y anti-afinidad de pods. |
| **1. Inventario Fantasma** | Integrante A | `kubectl delete pod` | Reintentos automáticos y auto-recuperación de pods. |
| **2. Pasarela Lenta** | Integrante A | `kubectl port-forward` | Timeout estricto de 3s y apertura de Circuit Breaker. |
| **3. Diluvio de Peticiones** | Integrante B | `k6 run` | Rate Limiting perimetral (HTTP 429) en el Gateway. |
| **4. Correo Perdido** | Integrante B | `kubectl scale` | Fallback / Degradación elegante de notificaciones. |

---

## 🧪 Pasos de la Presentación en Vivo

### 1. Presentación de Topología (Integrante A)
* **Comandos a ejecutar:**
  ```powershell
  kubectl get nodes -o wide
  kubectl get pods -o wide
  ```
* **Explicación:**
  - Mostrar que el clúster cuenta con **2 nodos activos** en Windows: **`minikube`** (que representa físicamente al **Nodo 1** / Control Plane) y **`minikube-m02`** (que representa al **Nodo 2** / Worker).
  - Enseñar la columna de `NODE` en los pods para demostrar que las réplicas del servicio de reservas se han distribuido automáticamente entre ambos nodos mediante políticas de anti-afinidad.

---

# en una segunda terminal para tener acceso al api-gateway
minikube service api-gateway-service --url
# guardar la direccion en una variable de entorno
$GATEWAY_URL = "http://[IP_ADDRESS]"


### 2. Caso 1: El Inventario Fantasma (Reintentos) (Integrante A)
* **Petición Normal (Antes del fallo):**
  ```powershell
  Invoke-RestMethod -Method Post -Uri "$GATEWAY_URL/reservar" -Body '{"asiento_id": "asiento_1"}' -ContentType "application/json"
  ```
  *Resultado esperado:* Retorna la reserva completada.

* **Inyección de la Falla:**
  En una segunda terminal, ejecute el script de caos para tumbar el pod de inventario:
  ```powershell
  # En Windows (PowerShell):
  .\caos\inject_crash_inventario.ps1

  # O en Git Bash / Linux:
  ./caos/inject_crash_inventario.sh
  ```
  Inmediatamente después, vuelva a mandar la petición de reserva en la primera terminal.

* **Comandos de Verificación en Vivo:**
  Ejecute los siguientes comandos en terminales secundarias para visualizar el impacto y la autorecuperación:
  
  1. **Monitoreo de Pods (Ver la caída y recreación automática):**
     ```powershell
     # Comprobar que Kubernetes está terminando el pod viejo y levantando uno nuevo
     kubectl get pods -l app=inventario -o wide
     ```
  2. **Monitoreo de Logs de Reservas (Ver reintentos automáticos):**
     ```powershell
     # Ver cómo Reservas detecta el fallo temporal, reintenta (1s, 2s...) y se recupera solo
     kubectl logs -l app=reservas --tail=40 -f
     ```

* **Resultado esperado:**
  El log de Reservas mostrará errores de red (`ConnectError`) e iniciará reintentos automáticos. Una vez levantado el pod de reemplazo en el Nodo 1 (`minikube`), la transacción finalizará con éxito (HTTP 200).

---

### 3. Caso 2: La Pasarela Lenta (Circuit Breaker) (Integrante A)
* **Activar Port-Forward a Pagos:**
  En una terminal secundaria, configure el reenvío de puertos para acceder al microservicio interno de pagos:
  ```powershell
  kubectl port-forward svc/pagos-service 8000:8000
  ```

* **Inyección del Caos:**
  En su terminal principal, ejecute el script de caos para activar la latencia de pagos (no requiere port-forward previo):
  ```powershell
  # En Windows (PowerShell):
  .\caos\inject_latencia_pagos.ps1 -Action on

  # O en Git Bash / Linux:
  ./caos/inject_latencia_pagos.sh on
  ```

* **Comandos de Verificación en Vivo:**
  1. **Verificar que la configuración de latencia se aplicó correctamente:**
     Consulte el estado del caos directamente en el pod:
     ```powershell
     kubectl exec $(kubectl get pod -l app=pagos -o jsonpath='{.items[0].metadata.name}') -- python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/config').read().decode())"
     # Debe retornar: {"modo_caos": "latencia"}
     ```
  2. **Monitorear transiciones del Circuit Breaker en Reservas:**
     Abra otra terminal y siga los logs en vivo:
     ```powershell
     kubectl logs -l app=reservas --tail=30 -f
     ```

* **Ejecución de la prueba:**
  Envíe 3 reservas consecutivas. Cada una demorará exactamente **3 segundos** y fallará con un HTTP 504 (Timeout) debido al límite estricto de timeout configurado.
  * Verás en los logs de Reservas: `[TIMEOUT WARNING] Intento de pago superó el límite de 3.0s.`
  
  A la 4ta petición, la respuesta será instantánea (0.002s) retornando un error **HTTP 503 (Circuit Breaker is OPEN)**.
  * Verás en los logs de Reservas: `[CIRCUIT BREAKER] Intento de llamada bloqueado. Estado actual: OPEN.`

* **Recuperación:**
  Desactive el modo latencia en el servicio de pagos usando el script de caos:
  ```powershell
  # En Windows (PowerShell):
  .\caos\inject_latencia_pagos.ps1 -Action off

  # O en Git Bash / Linux:
  ./caos/inject_latencia_pagos.sh off
  ```
  Espera 30 segundos (tiempo de enfriamiento). Envía una nueva petición; en los logs verás que el circuito pasa a *Half-Open*, se procesa exitosamente la llamada, regresa a `CLOSED` y las transacciones vuelven a responder con **HTTP 200 OK**.
  Cierre la terminal de `port-forward` si la abrió previamente.

---

### 4. Caso 3: El Diluvio de Peticiones (Rate Limiting) (Integrante B)
* **Inyección del Caos:**
  Dispare la prueba de sobrecarga usando la herramienta k6 dirigida al API Gateway:
  ```powershell
  k6 run -e TARGET_URL="$GATEWAY_URL/reservar" caos/inject_sobrecarga_k6.js
  ```

* **Comandos de Verificación en Vivo:**
  1. **Monitorear logs del API Gateway:**
     Abra una terminal secundaria para ver cómo el Gateway rechaza el tráfico excedente en tiempo real:
     ```powershell
     kubectl logs -l app=api-gateway --tail=50 -f
     ```
     *(Debería ver múltiples logs imprimiendo códigos `429` para solicitudes rechazadas)*.

* **Explicación:**
  - Mostrar la consola de k6 e indicar que el API Gateway bloqueó el exceso de solicitudes retornando **HTTP 429 (Too Many Requests)**.
  - Explicar que el Gateway protegió el backend de reservas y la base de datos de una denegación de servicio (DoS).

---

### 5. Caso 4: El Correo Perdido (Degradación Elegante) (Integrante B)
* **Inyección del Caos:**
  Simule la desconexión total del servicio de notificaciones usando el script de caos:
  ```powershell
  # En Windows (PowerShell):
  .\caos\inject_caida_correo.ps1 -Action down

  # O en Git Bash / Linux:
  ./caos/inject_caida_correo.sh down
  ```

* **Comandos de Verificación en Vivo:**
  1. **Verificar que el pod de notificaciones fue eliminado (0 réplicas):**
     ```powershell
     kubectl get pods -l app=notificaciones
     ```
     *(Debe responder: "No resources found en el namespace")*.
  2. **Ejecución de la reserva:**
     Realice una reserva normal:
     ```powershell
     Invoke-RestMethod -Method Post -Uri "$GATEWAY_URL/reservar" -Body '{"asiento_id": "asiento_2"}' -ContentType "application/json"
     ```
  3. **Verificar los logs de Reservas (Alerta de degradación / Fallback):**
     Muestre que la reserva se guardó a pesar de la caída del correo secundario:
     ```powershell
     kubectl logs -l app=reservas --tail=20
     ```
     *(Debe ver el log: `[FALLBACK WARNING] Error de conexion con servicio de notificaciones...`)*.

* **Recuperación:**
  Restaure el servicio de notificaciones usando el script de caos:
  ```powershell
  # En Windows (PowerShell):
  .\caos\inject_caida_correo.ps1 -Action up

  # O en Git Bash / Linux:
  ./caos/inject_caida_correo.sh up
  ```
  Verifique que el pod se levantó correctamente en el Nodo 2 (`minikube-m02`):
  ```powershell
  kubectl get pods -l app=notificaciones -o wide
  ```

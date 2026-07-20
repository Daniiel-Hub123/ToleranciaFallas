# Guion de la Demo en Vivo: Tolerancia a Fallas y Resiliencia (Windows)

Este documento describe el guion paso a paso de la demostración práctica (Parte IV de la asignación) de los mecanismos de resiliencia implementados sobre el clúster Kubernetes multinodo, diseñado para entornos de **Windows (PowerShell)**.

* **Duración Estimada:** 10–15 minutos.
* **Modalidad:** Presentación compartida (Integrante A e Integrante B).

> [!NOTE]
> Para la preparación del clúster, construcción de imágenes y despliegue de manifiestos, consúltese la sección de **Despliegue de la Infraestructura** en el [README.md](file:///c:/Users/sigua/Desktop/ToleranciaFallas/README.md).

---

## 🎭 Distribución de Roles y Escenarios de Caos

| Escenario de Caos | Integrante Responsable | Acción / Comando | Comportamiento Evaluado |
| :--- | :--- | :--- | :--- |
| **Inicio & Topología** | Integrante A y B | `kubectl get nodes` | Clúster multi-nodo y anti-afinidad de pods. |
| **1. Inventario Fantasma** | Integrante A | `.\caos\inject_crash_inventario.ps1` | Reintentos automáticos y auto-recuperación de pods. |
| **2. Pasarela Lenta** | Integrante A | `.\caos\inject_latencia_pagos.ps1` | Timeout estricto de 3s y apertura de Circuit Breaker. |
| **3. Diluvio de Peticiones** | Integrante B | `k6 run` | Rate Limiting perimetral (HTTP 429) en el Gateway. |
| **4. Correo Perdido** | Integrante B | `.\caos\inject_caida_correo.ps1` | Fallback / Degradación elegante de notificaciones. |

---

## 🧪 Pasos de la Presentación en Vivo

### 1. Presentación de Topología (Integrante A)
* **Requisito previo:** Configurar la variable `$GATEWAY_URL` en las terminales con la dirección obtenida al exponer el servicio API Gateway:
  ```powershell
  $GATEWAY_URL = "http://[IP_OBTENIDA_DE_MINIKUBE]"
  ```

* **Comandos de visualización:**
  ```powershell
  kubectl get nodes -o wide
  kubectl get pods -o wide
  ```
* **Explicación:**
  - Mostrar que el clúster cuenta con **2 nodos activos**: **`minikube`** (que representa físicamente al **Nodo 1** / Control Plane) y **`minikube-m02`** (que representa al **Nodo 2** / Worker).
  - Enseñar la columna de `NODE` en los pods para demostrar que las réplicas del servicio de reservas se han distribuido automáticamente entre ambos nodos mediante políticas de anti-afinidad.

---

### 2. Caso 1: El Inventario Fantasma (Reintentos) (Integrante A)
* **Petición Normal (Antes del fallo):**
  ```powershell
  Invoke-RestMethod -Method Post -Uri "$GATEWAY_URL/reservar" -Body '{"asiento_id": "asiento_1"}' -ContentType "application/json"
  ```
  *Resultado esperado:* Retorna la reserva completada.

* **Inyección de la Falla:**
  En una segunda terminal, ejecutar el script de caos para tumbar el pod de inventario:
  ```powershell
  # En Windows (PowerShell):
  .\caos\inject_crash_inventario.ps1

  # O en Git Bash / Linux:
  ./caos/inject_crash_inventario.sh
  ```
  Inmediatamente después, volver a enviar la petición de reserva en la primera terminal.

* **Comandos de Verificación en Vivo:**
  Ejecutar los siguientes comandos en terminales secundarias para visualizar el impacto y la autorecuperación:
  
  1. **Monitoreo de Pods (Ver la caída y recreación automática):**
     ```powershell
     # Comprobar que Kubernetes está terminando el pod viejo y levantando uno nuevo
     kubectl get pods -l app=inventario -o wide
     ```
  2. **Monitoreo de Logs de Reservas (Ver reintentos automáticos):**
     ```powershell
     # Ver cómo Reservas detecta el fallo temporal, reintenta (1s, 2s...) y se recupera
     kubectl logs -l app=reservas --tail=40 -f
     ```

* **Resultado esperado:**
  El log de Reservas muestra errores de red (`ConnectError`) e inicia reintentos automáticos. Una vez levantado el pod de reemplazo en el Nodo 1 (`minikube`), la transacción finaliza con éxito (HTTP 200).

---

### 3. Caso 2: La Pasarela Lenta (Circuit Breaker) (Integrante A)
* **Inyección del Caos:**
  En la terminal principal, ejecutar el script de caos para activar la latencia de pagos (no requiere port-forward previo):
  ```powershell
  # En Windows (PowerShell):
  .\caos\inject_latencia_pagos.ps1 -Action on

  # O en Git Bash / Linux:
  ./caos/inject_latencia_pagos.sh on
  ```

* **Comandos de Verificación en Vivo:**
  1. **Verificar que la configuración de latencia se aplicó correctamente:**
     Consultar el estado del caos directamente en el pod:
     ```powershell
     kubectl exec $(kubectl get pod -l app=pagos -o jsonpath='{.items[0].metadata.name}') -- python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/config').read().decode())"
     # Debe retornar: {"modo_caos": "latencia"}
     ```
  2. **Monitorear transiciones del Circuit Breaker en Reservas:**
     Abrir otra terminal y seguir los logs en vivo:
     ```powershell
     kubectl logs -l app=reservas --tail=30 -f
     ```

* **Ejecución de la prueba:**
  Enviar 3 reservas consecutivas. Cada una demorará exactamente **3 segundos** y fallará con un HTTP 504 (Timeout) debido al límite estricto de timeout configurado.
  * Se observa en los logs de Reservas: `[TIMEOUT WARNING] Intento de pago superó el límite de 3.0s.`
  
  A la 4ta petición, la respuesta es instantánea (0.002s) retornando un error **HTTP 503 (Circuit Breaker is OPEN)**.
  * Se observa en los logs de Reservas: `[CIRCUIT BREAKER] Intento de llamada bloqueado. Estado actual: OPEN.`

* **Recuperación:**
  Desactivar el modo latencia en el servicio de pagos usando el script de caos:
  ```powershell
  # En Windows (PowerShell):
  .\caos\inject_latencia_pagos.ps1 -Action off

  # O en Git Bash / Linux:
  ./caos/inject_latencia_pagos.sh off
  ```
  Esperar 30 segundos (tiempo de enfriamiento). Enviar una nueva petición; en los logs se observa que el circuito pasa a *Half-Open*, se procesa exitosamente la llamada, regresa a `CLOSED` y las transacciones vuelven a responder con **HTTP 200 OK**.

---

### 4. Caso 3: El Diluvio de Peticiones (Rate Limiting) (Integrante B)
* **Inyección del Caos:**
  Disparar la prueba de sobrecarga usando la herramienta k6 dirigida al API Gateway:
  ```powershell
  k6 run -e TARGET_URL="$GATEWAY_URL/reservar" caos/inject_sobrecarga_k6.js
  ```

* **Comandos de Verificación en Vivo:**
  1. **Monitorear logs del API Gateway:**
     Abrir una terminal secundaria para observar cómo el Gateway rechaza el tráfico excedente en tiempo real:
     ```powershell
     kubectl logs -l app=api-gateway --tail=50 -f
     ```
     *(Se deben observar múltiples logs imprimiendo códigos `429` para solicitudes rechazadas)*.

* **Explicación:**
  - Mostrar la consola de k6 e indicar que el API Gateway bloqueó el exceso de solicitudes retornando **HTTP 429 (Too Many Requests)**.
  - Explicar que el Gateway protegió el backend de reservas y la base de datos de una denegación de servicio (DoS).

---

### 5. Caso 4: El Correo Perdido (Degradación Elegante) (Integrante B)
* **Inyección del Caos:**
  Simular la desconexión total del servicio de notificaciones usando el script de caos:
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
     Realizar una reserva normal:
     ```powershell
     Invoke-RestMethod -Method Post -Uri "$GATEWAY_URL/reservar" -Body '{"asiento_id": "asiento_2"}' -ContentType "application/json"
     ```
  3. **Verificar los logs de Reservas (Alerta de degradación / Fallback):**
     Mostrar que la reserva se guardó a pesar de la caída del correo secundario:
     ```powershell
     kubectl logs -l app=reservas --tail=20
     ```
     *(Se debe observar el log: `[FALLBACK WARNING] Error de conexion con servicio de notificaciones...`)*.

* **Recuperación:**
  Restaurar el servicio de notificaciones usando el script de caos:
  ```powershell
  # En Windows (PowerShell):
  .\caos\inject_caida_correo.ps1 -Action up

  # O en Git Bash / Linux:
  ./caos/inject_caida_correo.sh up
  ```
  Verificar que el pod se levantó correctamente en el Nodo 2 (`minikube-m02`):
  ```powershell
  kubectl get pods -l app=notificaciones -o wide
  ```

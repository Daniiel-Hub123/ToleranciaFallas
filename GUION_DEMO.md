# Guion de la Demo en Vivo: Tolerancia a Fallas y Resiliencia

Este documento sirve como el guion oficial de la demostración práctica (Parte IV de la asignación) de los mecanismos de tolerancia a fallas implementados sobre el clúster Kubernetes multinodo.

* **Duración Estimada:** 10–15 minutos.
* **Modalidad:** Presentación compartida (Integrante A e Integrante B).

---

## 🛠️ Configuración Inicial de la Demo
Antes de comenzar la demostración, asegúrese de tener la terminal lista con acceso al clúster y los logs en tiempo real abiertos en pestañas divididas:

```bash
# Obtener la URL del API Gateway (NodePort)
minikube service api-gateway --url
# O directamente exportar el IP/Puerto del clúster:
export GATEWAY_URL="http://$(minikube ip):30080"
```

---

## 🎭 Distribución de Roles y Escenarios de Caos

| Escenario de Caos | Integrante Responsable | Acción / Comando | Comportamiento Evaluado |
| :--- | :--- | :--- | :--- |
| **Inicio & Topología** | Integrante A | Explicar el clúster multi-nodo. | `kubectl get nodes -o wide` |
| **1. Inventario Fantasma** | Integrante A | `bash caos/inject_crash_inventario.sh` | Reintentos asíncronos y auto-recuperación de Kubernetes. |
| **2. Pasarela Lenta** | Integrante B | `bash caos/inject_latencia_pagos.sh` | Timeout de 3s y apertura de Circuit Breaker. |
| **3. Diluvio de Peticiones** | Integrante A | `k6 run caos/inject_sobrecarga_k6.js` | Rate Limiting perimetral (HTTP 429) en API Gateway. |
| **4. Correo Perdido** | Integrante B | `bash caos/inject_caida_correo.sh` | Degradación elegante (Fallback) ante caída de servicio no crítico. |

---

## 🧪 Pasos Detallados de la Demostración

### 1. Demostración de la Distribución de Infraestructura
* **Comando a ejecutar:**
  ```bash
  kubectl get nodes -o wide
  kubectl get pods -o wide
  ```
* **Explicación (Integrante A):**
  - Mostrar que el clúster está corriendo sobre **2 nodos activos** (`minikube` y `minikube-n2`).
  - Mostrar que los pods del Servicio de Reservas e Inventario están repartidos entre ambos nodos utilizando las reglas de anti-afinidad (evitando que la caída de un nodo arrastre a todas las réplicas).

---

### 2. Caso 1: El Inventario Fantasma (Reintentos y Recuperación)
* **Comportamiento ANTES del fallo:**
  Hacer una petición normal:
  ```bash
  curl -X POST -H "Content-Type: application/json" -d '{"asiento_id": "asiento_1"}' $GATEWAY_URL/reservar
  ```
  *Resultado:* Compra exitosa (`"status": "Reserva Completada"`).

* **Inyección de la Falla (Durante):**
  En una terminal secundaria, correr el script que elimina el pod de Inventario en bucle:
  ```bash
  bash caos/inject_crash_inventario.sh
  ```
  Hacer la petición de compra inmediatamente después de matar el pod.
  *Logs en pantalla:* En otra pestaña, mostrar los logs de Reservas:
  ```bash
  kubectl logs -l app=reservas-service -f --tail=30
  ```
  *Resultado:* El log de Reservas mostrará errores de red (`httpx.RequestError`) y el inicio de los **reintentos automáticos con retraso de 1 segundo**.

* **Comportamiento DESPUÉS del fallo (Recuperación):**
  Kubernetes levanta un pod de reemplazo de Inventario automáticamente. La petición del cliente **no falla**; el reintento número 2 o 3 tiene éxito una vez el pod está listo y retorna la reserva procesada.

---

### 3. Caso 2: La Pasarela Lenta (Timeout y Circuit Breaker)
* **Comportamiento ANTES del fallo:**
  El servicio de pagos responde en milisegundos. La compra se procesa al instante.

* **Inyección de la Falla (Durante):**
  Activar la latencia artificial en pagos:
  ```bash
  bash caos/inject_latencia_pagos.sh
  ```
  Hacer 3 peticiones consecutivas de reserva.
  *Resultado:*
  - Las primeras 3 peticiones tardan exactamente **3 segundos** cada una antes de fallar con un HTTP 504 (Timeout en backend de Reservas), incrementando el contador de fallos.
  - La 4ta petición falla **inmediatamente** con un HTTP 503 (`Circuit Breaker is OPEN. Payment gateway temporarily disabled`), demostrando que el circuito se ha abierto y el tráfico de red hacia pagos ha sido cortado para evitar saturación.

* **Comportamiento DESPUÉS del fallo (Recuperación):**
  Desactivar la latencia:
  ```bash
  curl -X POST -H "Content-Type: application/json" -d '{"latencia": false}' http://localhost:8000/config # o vía CLI de caos
  ```
  Esperar los 30 segundos de tiempo de enfriamiento y hacer una nueva petición. El circuito transiciona a *Half-Open*, detecta que la respuesta es exitosa, cierra el circuito (*Closed*) y el sistema vuelve a la normalidad.

---

### 4. Caso 3: El Diluvio de Peticiones (Rate Limiting)
* **Comportamiento ANTES del fallo:**
  Un usuario haciendo compras esporádicas no tiene problemas.

* **Inyección de la Falla (Durante):**
  Lanzar la prueba de estrés con k6 para simular cientos de peticiones simultáneas:
  ```bash
  k6 run caos/inject_sobrecarga_k6.js
  ```
  *Resultado:* k6 mostrará en su consola que una parte de las peticiones fueron rechazadas con código de estado HTTP **429 (Too Many Requests)**.
  *Logs en pantalla:* Mostrar que el API Gateway intercepta la sobrecarga y bloquea las peticiones desde el middleware antes de saturar los microservicios internos.

* **Comportamiento DESPUÉS del fallo (Recuperación):**
  Detener k6. Al reanudar las llamadas individuales, el sistema responde de inmediato con HTTP 200 de forma exitosa.

---

### 5. Caso 4: El Correo Perdido (Degradación Elegante)
* **Comportamiento ANTES del fallo:**
  El servicio de notificaciones está activo y responde con `"notificacion_estado": "Enviada"`.

* **Inyección de la Falla (Durante):**
  Simular caída total del servicio de notificaciones reduciendo sus réplicas a cero:
  ```bash
  bash caos/inject_caida_correo.sh
  ```
  Ejecutar una compra.
  *Resultado:* La compra de la entrada tiene éxito y devuelve `"status": "Reserva Completada"`, pero con la propiedad `"notificacion_estado": "Pendiente de reenvío en background"`. El flujo crítico de reservas no se detiene a pesar de que el servicio secundario de correos está offline.
  *Logs en pantalla:*
  ```bash
  kubectl logs -l app=reservas-service --tail=20
  ```
  Mostrar el log: `[FALLBACK LOG] No se pudo enviar el correo de confirmación. Detalle: ...`

* **Comportamiento DESPUÉS del fallo (Recuperación):**
  Restaurar el servicio de notificaciones (`kubectl scale deployment/notificaciones-service --replicas=1`). La comunicación se restablece de inmediato.

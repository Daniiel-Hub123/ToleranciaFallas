# Guion de la Demo en Vivo: Tolerancia a Fallas y Resiliencia

Este documento es el guion paso a paso de la demostración práctica (Parte IV de la asignación) de los mecanismos de resiliencia implementados sobre el clúster Kubernetes multinodo, aplicable de manera general para cualquier entorno (Linux, macOS, Windows).

* **Duración Estimada:** 10–15 minutos.
* **Modalidad:** Presentación compartida (Integrante A e Integrante B).

---

## 🛠️ Paso 0: Preparación del Clúster (Desde Cero)

Para iniciar la demostración con un entorno limpio, navegue a la carpeta raíz del proyecto y ejecute los comandos correspondientes a su sistema operativo:

```bash
# 1. CD al proyecto
cd /ruta/al/proyecto/ToleranciaFallas

# 2. Iniciar el clúster multi-nodo (Minikube o Kind)
minikube start --nodes 2

# 3. Vincular el entorno de Docker al demonio del clúster
# Para Linux / macOS (Bash/Zsh):
eval $(minikube docker-env)
# Para Windows (PowerShell):
minikube docker-env | Invoke-Expression

# 4. Construir imágenes de los microservicios
docker build -t toleraciafallas/api-gateway:latest ./src/api-gateway
docker build -t toleraciafallas/reservas:latest ./src/reservas
docker build -t toleraciafallas/inventario:latest ./src/inventario
docker build -t toleraciafallas/pagos:latest ./src/pagos
docker build -t toleraciafallas/notificaciones:latest ./src/notificaciones

# 5. Desplegar los manifiestos en orden
kubectl apply -f k8s/database.yaml
kubectl apply -f k8s/api-gateway.yaml
kubectl apply -f k8s/reservas.yaml
kubectl apply -f k8s/inventario.yaml
kubectl apply -f k8s/pagos.yaml
kubectl apply -f k8s/notificaciones.yaml
kubectl apply -f k8s/pod-anti-affinity-rules.yaml

# 6. Monitorear que todos los pods estén en estado Running
kubectl get pods -w
```

Una vez que los pods estén listos, exponga el API Gateway y configure la dirección en su terminal:

```bash
# Exponer el servicio del API Gateway para obtener la URL de acceso
minikube service api-gateway-service --url

# Guardar la dirección obtenida en una variable de entorno de su terminal:
# En Linux / macOS (Bash):
export GATEWAY_URL="http://<IP_Y_PUERTO_OBTENIDO>"
# En Windows (PowerShell):
$GATEWAY_URL = "http://<IP_Y_PUERTO_OBTENIDO>"
```

---

## 🎭 Distribución de Roles y Escenarios de Caos

| Escenario de Caos | Integrante Responsable | Acción / Comando | Comportamiento Evaluado |
| :--- | :--- | :--- | :--- |
| **Inicio & Topología** | Integrante A | `kubectl get nodes` | Clúster multi-nodo y anti-afinidad de pods. |
| **1. Inventario Fantasma** | Integrante A | `kubectl delete pod` | Reintentos automáticos y auto-recuperación de pods. |
| **2. Pasarela Lenta** | Integrante B | `kubectl port-forward` | Timeout estricto de 3s y apertura de Circuit Breaker. |
| **3. Diluvio de Peticiones** | Integrante A | `k6 run` | Rate Limiting perimetral (HTTP 429) en el Gateway. |
| **4. Correo Perdido** | Integrante B | `kubectl scale` | Fallback / Degradación elegante de notificaciones. |

---

## 🧪 Pasos de la Presentación en Vivo

### 1. Presentación de Topología (Integrante A)
* **Comando a ejecutar:**
  ```bash
  kubectl get nodes -o wide
  kubectl get pods -o wide
  ```
* **Explicación:**
  - Mostrar que el clúster cuenta con al menos **2 nodos activos**.
  - Enseñar la columna de `NODE` en los pods para demostrar que las réplicas del servicio crítico de reservas se han distribuido en nodos físicos separados mediante políticas de anti-afinidad.

---

### 2. Caso 1: El Inventario Fantasma (Reintentos) (Integrante A)
* **Petición Normal (Antes del fallo):**
  ```bash
  curl -X POST -H "Content-Type: application/json" -d '{"asiento_id": "asiento_1"}' $GATEWAY_URL/reservar
  ```
  *Resultado esperado:* Retorna HTTP 200 con la reserva completada.

* **Inyección de la Falla:**
  En una segunda terminal, elimine abruptamente el pod de inventario en medio de la transacción:
  ```bash
  kubectl delete pod -l app=inventario --force --grace-period=0
  ```
  Inmediatamente después, vuelva a mandar la petición de reserva en la primera terminal.
  En otra ventana, monitoree los logs de Reservas para evidenciar el fallo:
  ```bash
  kubectl logs -l app=reservas --tail=30 -f
  ```
  *Resultado esperado:* El log de Reservas mostrará errores de red (`ConnectError`) e iniciará reintentos automáticos separados por 1s. Una vez levantado el pod de reemplazo por Kubernetes, la transacción finalizará con éxito (HTTP 200).

---

### 3. Caso 2: La Pasarela Lenta (Circuit Breaker) (Integrante B)
* **Activar Port-Forward a Pagos:**
  En una terminal secundaria, configure el reenvío de puertos para acceder al microservicio interno de pagos:
  ```bash
  kubectl port-forward svc/pagos-service 8000:8000
  ```
* **Inyección del Caos:**
  En su terminal principal, active la latencia simulada en pagos:
  ```bash
  curl -X POST -H "Content-Type: application/json" -d '{"latencia": true}' http://localhost:8000/config
  ```
* **Ejecución de la prueba:**
  Envíe 3 reservas consecutivas. Cada una demorará exactamente **3 segundos** y fallará con un HTTP 504 (Timeout).
  A la 4ta petición, la respuesta será instantánea (0.002s) retornando un error **HTTP 503 (Circuit Breaker is OPEN)**.
* **Recuperación:**
  Apague la latencia de pagos:
  ```bash
  curl -X POST -H "Content-Type: application/json" -d '{"latencia": false}' http://localhost:8000/config
  ```
  Espera 30 segundos (tiempo de enfriamiento). Envía una nueva petición; el circuito pasará a *Half-Open*, se cerrará (`CLOSED`) y las transacciones volverán a funcionar con éxito. Cierre la terminal de `port-forward`.

---

### 4. Caso 3: El Diluvio de Peticiones (Rate Limiting) (Integrante A)
* **Inyección del Caos:**
  Dispare la prueba de sobrecarga usando la herramienta k6 dirigida al API Gateway:
  ```bash
  k6 run -e TARGET_URL="$GATEWAY_URL/reservar" caos/inject_sobrecarga_k6.js
  ```
* **Explicación:**
  - Mostrar la consola de k6 e indicar que el API Gateway bloqueó el exceso de solicitudes retornando **HTTP 429 (Too Many Requests)**.
  - Explicar que el Gateway protegió el backend de reservas y la base de datos de una denegación de servicio (DoS).

---

### 5. Caso 4: El Correo Perdido (Degradación Elegante) (Integrante B)
* **Inyección del Caos:**
  Simula la desconexión total del servicio de notificaciones escalando sus réplicas a cero:
  ```bash
  kubectl scale deployment/notificaciones-deployment --replicas=0
  ```
* **Ejecución de la prueba:**
  Realice una reserva normal:
  ```bash
  curl -X POST -H "Content-Type: application/json" -d '{"asiento_id": "asiento_2"}' $GATEWAY_URL/reservar
  ```
* **Explicación:**
  - El cliente recibe respuesta exitosa **HTTP 200 OK** con `"status": "Reserva Completada"`, pero con la propiedad `"notificacion_estado": "Pendiente de reenvío en background"`.
  - Muestre los logs de reservas (`kubectl logs -l app=reservas --tail=20`) para enseñar la alerta de fallback: `[FALLBACK WARNING] Error de conexion con servicio de notificaciones...`. El negocio no se detuvo por la caída de un servicio secundario.
* **Recuperación:**
  Restaure las réplicas del servicio de notificaciones:
  ```bash
  kubectl scale deployment/notificaciones-deployment --replicas=1
  ```

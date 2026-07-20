# Guion de la Demo en Vivo: Tolerancia a Fallas y Resiliencia

Este documento es el guion paso a paso de la demostración práctica (Parte IV de la asignación) de los mecanismos de resiliencia sobre tu clúster Kubernetes multinodo, actualizado con todos los puertos y comandos que nos han funcionado con éxito en PowerShell (Windows).

* **Duración Estimada:** 10–15 minutos.
* **Modalidad:** Presentación compartida (Integrante A e Integrante B).

---

## 🛠️ Paso 0: Preparación del Clúster (Desde Cero)

Para iniciar tu demo limpia con el clúster totalmente restablecido, ejecuta en PowerShell:

```powershell
# 1. CD al proyecto
cd c:\Users\sigua\Desktop\ToleranciaFallas

# 2. Iniciar el clúster multi-nodo
minikube start --nodes 2

# 3. Vincular Docker al daemon de minikube
& minikube -p minikube docker-env | Invoke-Expression

# 4. Construir imágenes actualizadas de los microservicios
docker build -t toleraciafallas/api-gateway:latest ./src/api-gateway
docker build -t toleraciafallas/reservas:latest ./src/reservas
docker build -t toleraciafallas/inventario:latest ./src/inventario
docker build -t toleraciafallas/pagos:latest ./src/pagos
docker build -t toleraciafallas/notificaciones:latest ./src/notificaciones

# 5. Desplegar manifiestos en orden
kubectl apply -f k8s/database.yaml
kubectl apply -f k8s/api-gateway.yaml
kubectl apply -f k8s/reservas.yaml
kubectl apply -f k8s/inventario.yaml
kubectl apply -f k8s/pagos.yaml
kubectl apply -f k8s/notificaciones.yaml
kubectl apply -f k8s/pod-anti-affinity-rules.yaml

# 6. Monitorear que todos los pods estén en Running y 1/1 (o 2/2)
kubectl get pods -w
```

Una vez que todos los pods estén `Running`, expón el API Gateway y guarda la URL en una variable de PowerShell:

```powershell
# Obtener la URL del Gateway (puerto 30088 en minikube)
minikube service api-gateway-service --url

# Copia la URL del túnel que te de Minikube y asígnala (ejemplo):
$GATEWAY_URL = "http://127.0.0.1:54321"  # <-- Reemplaza con tu puerto real de salida
```

---

## 🎭 Distribución de Roles y Escenarios de Caos

| Escenario de Caos | Integrante | Comando Principal | Comportamiento Evaluado |
| :--- | :--- | :--- | :--- |
| **Inicio & Topología** | Integrante A | `kubectl get nodes -o wide` | Clúster multi-nodo y anti-afinidad. |
| **1. Inventario Fantasma** | Integrante A | `kubectl delete pod` | Reintentos asíncronos y auto-recuperación. |
| **2. Pasarela Lenta** | Integrante B | `kubectl port-forward` | Timeout de 3s y apertura de Circuit Breaker. |
| **3. Diluvio de Peticiones** | Integrante A | `k6 run` | Rate Limiting perimetral (HTTP 429). |
| **4. Correo Perdido** | Integrante B | `kubectl scale` | Fallback / Degradación elegante de notificaciones. |

---

## 🧪 Pasos de la Presentación en Vivo

### 1. Presentación de Topología (Integrante A)
* **Comando a ejecutar:**
  ```powershell
  kubectl get nodes -o wide
  kubectl get pods -o wide
  ```
* **Explicación:**
  - Mostrar al profesor que el clúster tiene **2 nodos activos** (`minikube` y `minikube-n2`).
  - Mostrar que las réplicas del servicio crítico de reservas (`reservas-deployment`) se han programado cruzadas (una en el Nodo 1 y la otra en el Nodo 2) gracias a las reglas de anti-afinidad en los YAML.

---

### 2. Caso 1: El Inventario Fantasma (Reintentos) (Integrante A)
* **Petición Normal (Antes del fallo):**
  ```powershell
  Invoke-RestMethod -Method Post -Uri "$GATEWAY_URL/reservar" -Body '{"asiento_id": "asiento_1"}' -ContentType "application/json"
  ```
  *Resultado:* Retorna exitoso `{"status": "Reserva Completada", ...}`.

* **Inyección de la Falla:**
  En una segunda terminal, destruye el pod de inventario en medio del proceso:
  ```powershell
  kubectl delete pod -l app=inventario --force --grace-period=0
  ```
  Inmediatamente después, vuelve a mandar la petición de reserva en la primera terminal.
  En otra pestaña, puedes monitorizar los logs del servicio de Reservas:
  ```powershell
  kubectl logs -l app=reservas --tail=30 -f
  ```
  *Resultado:* El log de Reservas mostrará intentos fallidos de conexión (`ConnectError`) e iniciará reintentos automáticos separados por 1s. Al levantarse el nuevo pod por Kubernetes, la transacción finaliza exitosamente (HTTP 200).

---

### 3. Caso 2: La Pasarela Lenta (Circuit Breaker) (Integrante B)
* **Activar Port-Forward a Pagos:**
  Dado que el servicio de pagos está dentro del clúster, abre una terminal separada y reenvía su puerto para poder configurar el caos desde Windows:
  ```powershell
  kubectl port-forward svc/pagos-service 8000:8000
  ```
* **Inyección del Caos:**
  En tu terminal principal, activa la latencia de pagos enviando la configuración de caos:
  ```powershell
  Invoke-RestMethod -Method Post -Uri "http://localhost:8000/config" -Body '{"latencia": true}' -ContentType "application/json"
  ```
* **Ejecución de la prueba:**
  Envía 3 reservas consecutivas. Cada una demorará exactamente **3 segundos** y fallará con un HTTP 504 debido al Timeout.
  A la 4ta petición, la respuesta será instantánea (0.002s) con un error **HTTP 503 (Circuit Breaker is OPEN)**.
* **Recuperación:**
  Apaga la latencia en pagos:
  ```powershell
  Invoke-RestMethod -Method Post -Uri "http://localhost:8000/config" -Body '{"latencia": false}' -ContentType "application/json"
  ```
  Espera 30 segundos de enfriamiento. Envía una nueva petición; el circuito pasará a *Half-Open*, se cerrará (`CLOSED`) y las transacciones volverán a funcionar con éxito. Cierra la terminal de `port-forward` con `Ctrl+C`.

---

### 4. Caso 3: El Diluvio de Peticiones (Rate Limiting) (Integrante A)
* **Inyección del Caos:**
  Dispara la prueba de sobrecarga usando k6 dirigida a tu puerto del API Gateway expuesto por Minikube:
  ```powershell
  k6 run -e TARGET_URL="$GATEWAY_URL/reservar" caos/inject_sobrecarga_k6.js
  ```
* **Explicación:**
  - Muestra la consola de k6. Explicar al profesor que las peticiones excedieron la tasa de 10 peticiones/10s.
  - El API Gateway interceptó la sobrecarga en su middleware y bloqueó el exceso retornando un código **HTTP 429 (Too Many Requests)**, evitando que las llamadas llegaran a saturar el Servicio de Reservas y PostgreSQL.

---

### 5. Caso 4: El Correo Perdido (Degradación Elegante) (Integrante B)
* **Inyección del Caos:**
  Simula la desconexión total del servicio de notificaciones reduciendo sus réplicas a cero:
  ```powershell
  kubectl scale deployment/notificaciones-deployment --replicas=0
  ```
* **Ejecución de la prueba:**
  Realiza una compra normal:
  ```powershell
  Invoke-RestMethod -Method Post -Uri "$GATEWAY_URL/reservar" -Body '{"asiento_id": "asiento_2"}' -ContentType "application/json"
  ```
* **Explicación:**
  - El cliente recibe respuesta exitosa **HTTP 200 OK** con `"status": "Reserva Completada"`.
  - La compra se registró y persistió en la base de datos de PostgreSQL con éxito, pero la respuesta informa `"notificacion_estado": "Pendiente de reenvío en background"`.
  - Muestra los logs de reservas (`kubectl logs -l app=reservas --tail=20`) para enseñar al profesor la alerta del fallback: `[FALLBACK WARNING] Error de conexion con servicio de notificaciones...`. El negocio no se detuvo por un fallo secundario.
* **Recuperación:**
  Restaura las réplicas del servicio de notificaciones:
  ```powershell
  kubectl scale deployment/notificaciones-deployment --replicas=1
  ```

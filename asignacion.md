# Práctica - Tolerancia a Fallas

## Información General

- **Apertura:** Miércoles, 8 de julio de 2026, 00:00
- **Cierre:** Miércoles, 15 de julio de 2026, 00:00
- **Modalidad:** En parejas (las mismas duplas de la tarea de investigación MLR)

---

# Contexto General

La tarea anterior abordó la tolerancia a fallos desde la investigación: qué dice la literatura académica y qué evidencia documenta la industria sobre los distintos mecanismos.

Esta práctica cierra el ciclo llevando esos mecanismos a la experimentación directa. Ya no se trata de leer sobre fallos, sino de provocarlos deliberadamente sobre una infraestructura real y verificar, con evidencia propia, que el sistema sobrevive.

**Duración total:** dos semanas.

**Esfuerzo estimado por integrante:** entre **6 y 8 horas** de trabajo efectivo, distribuidas entre:

- Despliegue de infraestructura
- Implementación de mecanismos de resiliencia
- Demo en vivo
- Análisis teórico

---

# Parte I — El Escenario: Sistema de Reservas de Entradas

## Objetivo

Desplegar la arquitectura simplificada de venta de entradas para eventos sobre una infraestructura Kubernetes de al menos dos nodos, de modo que los experimentos de fallo posteriores ocurran sobre infraestructura real y distribuida, no sobre un único contenedor local.

## Instrucciones

### Paso 1

Construyan la siguiente arquitectura simplificada de venta de entradas para eventos, cuyos componentes deben comunicarse mediante **REST** o **gRPC**.

Los componentes que no sean el foco de esta práctica (por ejemplo, **Pagos** o **Notificaciones**) pueden implementarse como **stubs básicos**, desarrollados por la propia pareja, que simulen latencia y fallos realistas sin necesidad de lógica de negocio completa.

### Componentes

- API Gateway (punto de entrada para los clientes)
- Servicio de Reservas (Core)
- Servicio de Inventario
- Servicio de Pagos (externo/simulado)
- Servicio de Notificaciones
- Base de Datos

---

### Paso 2

Desplieguen la arquitectura en un clúster Kubernetes con un mínimo de **dos nodos**, o en **dos clústeres/workspaces independientes** que simulen dos sitios de infraestructura.

Ejemplos:

- Dos node pools
- Dos instancias de kind/minikube conectadas
- Dos namespaces con afinidad de nodo forzada

Distribuyan al menos un componente crítico (**Servicio de Reservas** o **Servicio de Inventario**) con réplicas repartidas entre ambos equipos de cómputo.

---

### Paso 3

Documenten:

- Los manifiestos YAML
- Un diagrama de arquitectura que muestre explícitamente la distribución de los seis componentes entre ambos nodos o sitios.

---

## Restricciones

- Infraestructura mínima de **dos nodos** o **dos clústeres/workspaces independientes**.
- Deben existir los seis componentes.
- Los stubs de Pagos o Notificaciones deben simular:
  - Latencia variable
  - Fallos aleatorios

No se aceptan respuestas siempre exitosas.

---

## Entregables

- Manifiestos Kubernetes (YAML)
- Diagrama de arquitectura
- README con instrucciones de despliegue

---

# Parte II — Los 6 Puntos de Fallo (Chaos Scenarios)

## Objetivo

Comprender el catálogo de anomalías que el sistema debe soportar para decidir cuáles implementar posteriormente.

## Instrucciones

### Paso 1

Estudien los seis escenarios de fallo.

Para cada uno, identifiquen qué mecanismo de Kubernetes o infraestructura permitiría provocarlo de forma controlada.

Ejemplos:

- Eliminación de Pods
- Network Policies
- Inyección de latencia
- Límites de recursos
- Generación de carga
- Condiciones de concurrencia

---

## Escenarios de fallo

### 1. El Inventario Fantasma (Disponibilidad)

El Servicio de Inventario se cae completamente mientras se procesa una reserva.

---

### 2. La Pasarela Lenta (Latencia)

El Servicio de Pagos tarda **20 segundos** en responder debido a sobrecarga.

---

### 3. El Diluvio de Peticiones (Sobrecarga)

El sistema recibe un pico repentino de tráfico utilizando:

- k6
- JMeter
- Scripts personalizados

---

### 4. Base de Datos Intermitente (Conectividad)

La conexión a la base de datos se pierde intermitentemente durante operaciones de escritura.

---

### 5. El Correo Perdido (Fallo no crítico)

El servicio de Notificaciones deja de funcionar.

El usuario paga correctamente, pero nunca recibe el correo de confirmación.

---

### 6. Condición de Carrera (Consistencia)

Dos usuarios intentan comprar el último asiento exactamente al mismo tiempo.

---

## Restricciones

Antes de avanzar a la Parte III debe existir un mapeo explícito entre:

- Cada fallo
- El mecanismo técnico que lo provocará

---

## Entregables

Una tabla que relacione:

| Fallo | Mecanismo de inyección |
|--------|------------------------|
| ... | ... |

---

# Parte III — Implementación de Mecanismos de Resiliencia

**Elegir 4 de los 6 fallos**

## Objetivo

Implementar mecanismos que permitan al sistema sobrevivir a cuatro fallos aplicando patrones de resiliencia.

Ejemplos:

- Circuit Breaker
- Retries con Backoff
- Fallbacks
- Bulkheads
- Otros patrones adecuados

---

## Instrucciones

### Paso 1

Elegir cuatro fallos.

Para cada uno:

- Seleccionar el patrón adecuado.
- Justificar por qué ese patrón y no otro.

---

### Paso 2

Implementar el mecanismo en el servicio correspondiente.

---

### Paso 3

Preparar el mecanismo de inyección del fallo.

Ejemplos:

- `kubectl delete pod`
- NetworkPolicy
- Toxiproxy
- k6
- JMeter
- Escenarios de concurrencia

---

### Paso 4

Registrar evidencia de recuperación mediante:

- Logs
- Métricas
- Capturas

El sistema debe demostrar que:

- No colapsa.
- Maneja el error.
- Se recupera automáticamente.
- Usa un valor por defecto cuando corresponde.

---

## Restricciones

- Los cuatro fallos deben ejecutarse realmente sobre un clúster de al menos dos nodos.
- No se aceptan simulaciones únicamente en Docker local.
- Todos los patrones deben estar justificados.
- El código debe mantenerse en un repositorio Git con historial de commits por integrante.

---

## Entregables

- Repositorio del proyecto
- Código fuente
- Scripts/manifiestos de inyección
- Evidencias de recuperación

---

# Parte IV — Demo en Vivo

## Objetivo

Demostrar que el sistema soporta los cuatro fallos implementados sobre Kubernetes.

## Instrucciones

### Paso 1

Preparar un guion indicando:

- Comando ejecutado
- Comportamiento esperado antes
- Durante la falla
- Después de la recuperación

---

### Paso 2

Ejecutar los cuatro fallos en vivo.

---

### Paso 3

Mostrar:

- Logs
- Dashboards
- Métricas

---

## Restricciones

- Debe ejecutarse sobre el clúster real.
- Duración:
  - **10–15 minutos**
- Ambos integrantes deben participar.

---

## Entregables

- Guion de la demo
- Demo en vivo

---

# Parte V — Análisis y Diseño (2 fallos restantes)

## Objetivo

Analizar teóricamente los dos fallos que no fueron implementados y proponer una solución de nivel producción.

---

## Instrucciones

### Paso 1

Explicar por qué ocurre el fallo utilizando fundamentos como:

- Teorema CAP
- Condiciones de red
- Modelos de concurrencia

Relacionarlo con:

- Lo visto en clase
- La investigación MLR (si aplica)

---

### Paso 2

Explicar cómo se resolvería en producción.

### Ejemplo

> Para la condición de carrera utilizaríamos bloqueo pesimista en la base de datos o un patrón de reserva temporal con expiración (holds), en lugar de verificar y descontar inventario en pasos separados.

---

### Paso 3

Agregar:

- Pseudocódigo
- Diagrama de solución

---

## Restricciones

- La explicación debe ser específica del fallo elegido.
- Si existe relación con la investigación MLR, debe citarse.

---

## Entregables

Un informe técnico en PDF que incluya para cada fallo:

- Explicación teórica
- Solución propuesta
- Pseudocódigo o diagrama

---

# Rúbrica de Calificación

La nota se divide en dos bloques:

- **Bloque A:** Infraestructura y Experimentación (**70 puntos**)
- **Bloque B:** Análisis Técnico y Documentación (**30 puntos**)

---

# Bloque A — Infraestructura y Experimentación (70 pts)

| Dimensión | Criterio | Puntaje |
|-----------|----------|---------|
| Despliegue Multi-Nodo y Arquitectura | El sistema está desplegado correctamente sobre un clúster de al menos dos nodos o sitios, con componentes críticos replicados y documentación adecuada. | **20 pts** |
| Implementación de Mecanismos de Resiliencia | Los cuatro patrones están correctamente implementados, justificados y versionados. | **20 pts** |
| Demo en Vivo y Evidencia | Los cuatro fallos se ejecutan realmente y el sistema demuestra recuperación o manejo controlado mediante evidencia. | **30 pts** |

---

# Bloque B — Análisis Técnico y Documentación (30 pts)

| Dimensión | Criterio | Puntaje |
|-----------|----------|---------|
| Rigor Teórico | Explicación técnicamente correcta de los dos fallos basada en fundamentos de sistemas distribuidos. | **10 pts** |
| Calidad de la Solución | La propuesta de producción es coherente y el pseudocódigo/diagrama representa correctamente la solución. | **10 pts** |
| Documentación y Claridad | El informe, README y guion permiten reproducir el trabajo y mantienen coherencia con la Parte II y la investigación MLR. | **10 pts** |
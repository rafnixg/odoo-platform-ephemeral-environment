# Roadmap de Mini-Runbot

El roadmap mantiene el PoC enfocado en validar el ciclo de vida Odoo antes de incorporar
infraestructura distribuida.

## Fase 0: fundamentos del lifecycle — completa

- Máquina de estados, auditoría SQLite, CLI y API.
- Workspaces seguros, cleanup, logs y clasificación de recuperación.

## Fase 1: ejecución aislada real — completa

- Orígenes Git configurados, locales o HTTPS/SSH, resueltos a SHAs inmutables.
- Docker Compose por build, PostgreSQL, instalación/pruebas Odoo y healthcheck HTTP.
- Dashboard, ejecutor local acotado, cleanup por TTL y fixture E2E controlado.

## Fase 2: builds compuestos — completa

- Hasta diez repositorios configurados con refs independientes.
- Persistencia de alias, ref, SHA, checkout y prioridad de addons.
- `addons_path` determinista y contrato común para CLI, API y dashboard.
- Rechazo de alias duplicados y destinos repetidos antes de crear recursos.

## Fase 3: fiabilidad del host — en progreso

- [x] Leases de puertos transaccionales en SQLite entre procesos.
- [x] Reconciliación de leases huérfanos o ausentes durante recuperación.
- [x] Cleanup programado y configurable en el proceso API.
- [x] Política opt-in de retención y eliminación de auditoría y logs.
- [x] Reconciliación de builds registrados con servicios Docker reales.
- [x] Documentación bilingüe y validaciones automáticas de calidad y seguridad.
- [x] Aplicación PyPI autocontenida con recursos runtime, `mini-runbot init` y validación de wheel.
- [x] Workflow de publicación por tags con PyPI Trusted Publishing.
- [ ] Elegir una licencia, configurar el publisher en PyPI y realizar la primera publicación.

### Control de ejecución y logs — siguiente incremento

- [ ] Introducir migraciones versionadas para SQLite antes de añadir estados y eventos.
- [ ] Extraer un `CommandRunner` portable que gestione procesos y grupos de procesos en Windows y
  Linux.
- [ ] Añadir los estados `CANCEL_REQUESTED`, `CANCELLING` y `CANCELLED` con cleanup idempotente y
  conservación del motivo original.
- [ ] Exponer la cancelación en API, CLI y dashboard, tanto para builds en cola como en ejecución.
- [ ] Capturar `stdout` y `stderr` incrementalmente como eventos estructurados por build y etapa.
- [ ] Publicar los eventos mediante Server-Sent Events con cursor de reconexión y conservar la
  consulta de logs históricos.
- [ ] Cubrir cancelación, timeouts y condiciones de carrera en checkout, instalación, pruebas,
  healthcheck y cola.

### Endurecimiento adicional del host

- [ ] Ejecutar las pruebas sin Docker en una matriz CI con Windows y Linux.
- [ ] Ejecutar el E2E real de Docker/Odoo mediante workflow manual y programación periódica en
  Linux.
- [ ] Añadir paginación, ordenamiento y filtros por estado, repositorio y fecha a la API de builds.
- [ ] Añadir endpoints de liveness y readiness para configuración, SQLite, Docker y ejecutor.
- [ ] Aplicar límites configurables de CPU, memoria, procesos y espacio disponible por build.
- [ ] Permitir reintentar un build con sus mismos SHAs o crear otro desde las refs actuales sin
  confundir ambos comportamientos.
- [ ] Exportar un paquete de diagnóstico con logs, etapas, revisiones y Compose renderizado.
- [ ] Exponer métricas opcionales de cola, builds, duración de etapas, fallos y cleanup.
- [ ] Documentar ejecución como servicio en Windows y Linux, backup/restauración, troubleshooting y
  la matriz de compatibilidad probada.
- [x] Fijar la versión de Mermaid y añadir diagramas de secuencia para los flujos operativos.

La fase 3 se considera completa cuando un operador puede observar y cancelar de forma segura un
build real, recuperar el servicio y diagnosticar fallos en ambos sistemas soportados.

## Fase 4: integración externa — opcional

- Webhooks de GitHub y publicación de estados mediante Checks.
- Cola durable y workers separados.
- Autenticación, autorización, TLS e integración de secretos.
- Proxy inverso y rutas estables de preview.

Kubernetes y el scheduling multi-host permanecen fuera de alcance hasta que el flujo de un solo
host demuestre suficiente valor operativo.

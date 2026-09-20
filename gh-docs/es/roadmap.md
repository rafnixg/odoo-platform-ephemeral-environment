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
- [ ] Streaming estructurado de logs y cancelación de builds.

## Fase 4: integración externa — opcional

- Webhooks de GitHub y publicación de estados mediante Checks.
- Cola durable y workers separados.
- Autenticación, autorización, TLS e integración de secretos.
- Proxy inverso y rutas estables de preview.

Kubernetes y el scheduling multi-host permanecen fuera de alcance hasta que el flujo de un solo
host demuestre suficiente valor operativo.

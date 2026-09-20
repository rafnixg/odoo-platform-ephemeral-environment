# Glosario

| Término | Definición |
| --- | --- |
| Addons path | Lista ordenada donde Odoo busca módulos. La prioridad menor se evalúa primero. |
| Alias permitido | Nombre configurado por el operador que representa un origen Git confiable. |
| Build | Ejecución aislada de revisiones y módulos con lifecycle, workspace y recursos propios. |
| Build compuesto | Build formado por varios repositorios con refs independientes. |
| Checkout detached | Working tree fijado a un commit sin permanecer unido a una rama mutable. |
| Cleanup | Destrucción de recursos de builds vencidos; no implica necesariamente purgar auditoría. |
| Compose project | Nombre aislado usado por Docker Compose para servicios, red y volúmenes del build. |
| Estado terminal | Estado sin progresión normal posterior; `DESTROYED` permite repetición idempotente. |
| Etapa | Operación auditable del pipeline con estado, tiempo, salida, log y resumen. |
| Filestore | Almacenamiento de adjuntos de Odoo, aislado en un volumen por proyecto Compose. |
| Healthcheck | Verificación final de que el preview Odoo responde por HTTP. |
| Lease de puerto | Reserva persistente que asigna exclusivamente un puerto loopback a un build. |
| Optimistic locking | Control de concurrencia que rechaza una escritura si cambió `Build.version`. |
| Origen Git | URL HTTPS/SSH o ruta local definida en configuración para un alias. |
| Preview | Instancia Odoo temporal publicada en `127.0.0.1:<puerto>`. |
| Purga | Eliminación posterior del registro y workspace de un build ya destruido. |
| Recuperación | Reconciliación explícita entre SQLite, Docker y leases después de un reinicio. |
| Ref solicitada | Rama, tag o SHA que pidió el usuario; se resuelve antes de ejecutar. |
| Revisión | Combinación persistida de alias, origen, ref, SHA, checkout y prioridad. |
| SHA inmutable | Commit exacto que identifica el código realmente probado. |
| TTL | Tiempo de vida desde la creación hasta que el build puede expirar. |
| Workspace | `<builds_root>/<build_id>` con fuentes, configuración runtime y logs. |

## Nombres de etapas

`checkout` → `render` → `compose_validate` → `database` → `install` → `test` → `start` →
`healthcheck`.

Consulte [modelo de dominio](domain-model.md) para estados y validaciones y
[pipeline](build-pipeline.md) para el comportamiento de cada etapa.

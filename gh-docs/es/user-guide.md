# Guía funcional

## Crear un build

Un build necesita repositorios, referencias Git, módulos Odoo y opcionalmente un TTL. Las entradas
de repositorio son alias definidos por el operador; la API y la CLI nunca aceptan URLs o rutas
arbitrarias.

Desde el dashboard seleccione uno o más repositorios, indique sus refs, añada los módulos y envíe el
formulario. Desde la CLI:

```console
mini-runbot build create --repo custom --ref feature/catalog --extra-repo oca=16.0 --modules custom_sale,website_sale --ttl-seconds 14400 --run
```

La prioridad `addons_priority` de cada alias determina el orden del `addons_path`; no depende del
orden del payload.

## Interpretar estados y etapas

| Estado | Significado |
| --- | --- |
| `new` | Solicitud persistida y todavía no ejecutada. |
| `checking_out` | Resolución y checkout de revisiones Git. |
| `preparing` | Renderizado y validación de Docker Compose. |
| `installing` | Creación de la base de datos e instalación de módulos. |
| `testing` | Ejecución de pruebas Odoo. |
| `starting` | Inicio del servidor y healthcheck. |
| `running` | Preview disponible. |
| `failed` | Una etapa falló; se conserva evidencia. |
| `expired` | El TTL terminó y el build espera limpieza. |
| `destroying` / `destroyed` | Eliminación en curso / finalizada del runtime. |

Cada etapa registra inicio, fin, duración, código de salida, resumen y ruta de log cuando aplica.

## Consultar y diagnosticar

- Use los filtros del dashboard o `mini-runbot build list --status failed`.
- Abra un build para revisar su timeline y el mensaje de fallo.
- Consulte una etapa concreta con `mini-runbot build logs BUILD_ID --stage test`.
- Los timestamps se almacenan en UTC; el dashboard los muestra en la zona horaria del navegador.

## Destruir y limpiar

`build destroy` elimina contenedores, red y volúmenes del proyecto Compose, pero conserva el registro
de auditoría y sus logs. La operación es idempotente. La limpieza programada puede destruir builds
expirados y, si se configura una retención positiva, purgar auditorías antiguas.

No se permite destruir un build mientras su worker local continúa ejecutándolo.

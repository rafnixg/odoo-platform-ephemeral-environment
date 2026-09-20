# Configuración

Mini-Runbot carga YAML únicamente cuando `MINI_RUNBOT_CONFIG` apunta a un archivo existente. Los
valores de entorno admitidos tienen precedencia sobre el YAML.

## Ejemplo

```yaml
database_url: sqlite:///./mini_runbot.db
builds_root: ./builds
odoo_image: odoo:16.0
postgres_image: postgres:15
port_start: 18000
port_end: 19999
command_timeout_seconds: 900
health_timeout_seconds: 120
max_concurrent_builds: 2
cleanup_interval_seconds: 60
destroyed_retention_seconds: 0
load_demo_data: true
retain_failed_runtime: false
repositories:
  custom:
    url: https://github.com/OCA/e-commerce.git
    default_ref: "16.0"
    target: custom-addons
    addons_subpath: .
    allow_request_ref: true
    addons_priority: 100
```

## Opciones generales

| Opción | Predeterminado | Uso |
| --- | --- | --- |
| `database_url` | `sqlite:///./mini_runbot.db` | Base de auditoría y leases. |
| `builds_root` | `./builds` | Workspaces y logs por build. |
| `odoo_image` | `odoo:16.0` | Imagen de Odoo. |
| `postgres_image` | `postgres:15` | Imagen interna de PostgreSQL. |
| `port_start`, `port_end` | `18000`, `19999` | Rango loopback para previews. |
| `command_timeout_seconds` | `900` | Límite para comandos externos. |
| `health_timeout_seconds` | `120` | Límite del healthcheck HTTP. |
| `max_concurrent_builds` | `2` | Workers del ejecutor API. |
| `cleanup_interval_seconds` | `0` | Frecuencia del scheduler; cero lo desactiva. |
| `destroyed_retention_seconds` | `0` | Retención antes de purgar; cero conserva indefinidamente. |
| `load_demo_data` | `true` | Carga datos demo requeridos por muchas pruebas Odoo/OCA. |
| `retain_failed_runtime` | `false` | Conserva contenedores fallidos para diagnóstico. |

## Repositorios

Cada clave bajo `repositories` es un alias confiable. `target` debe ser único, `addons_subpath` debe
ser relativo y no puede escapar del checkout, y `allow_request_ref: false` limita solicitudes a
`default_ref`. Un número menor en `addons_priority` tiene mayor precedencia.

Las credenciales de remotos HTTPS/SSH deben proceder de Git Credential Manager o SSH del host;
nunca las incluya en la URL o en el repositorio.

## Variables de entorno

| Variable | Reemplaza |
| --- | --- |
| `MINI_RUNBOT_CONFIG` | Ruta del archivo YAML. |
| `MINI_RUNBOT_DATABASE_URL` | `database_url`. |
| `MINI_RUNBOT_BUILDS_ROOT` | `builds_root`. |
| `MINI_RUNBOT_ODOO_IMAGE` | `odoo_image`. |
| `MINI_RUNBOT_CLEANUP_INTERVAL_SECONDS` | `cleanup_interval_seconds`. |

`config.local.yaml`, bases SQLite y `builds/` son estado local del operador y no deben versionarse.

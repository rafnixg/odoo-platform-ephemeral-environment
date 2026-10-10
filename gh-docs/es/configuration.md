# Configuración

Mini-Runbot carga YAML únicamente cuando `MINI_RUNBOT_CONFIG` apunta a un archivo existente. Los
valores de entorno admitidos tienen precedencia sobre el YAML.

Use `mini-runbot init` para generar este archivo de forma interactiva o `mini-runbot init
--defaults` para copiar los valores del ejemplo empaquetado. Ninguna variante sobrescribe un
destino existente.

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
| `odoo_image` | `odoo:16.0` | Imagen de Odoo cuando no aplica ningún perfil. |
| `postgres_image` | `postgres:15` | Imagen interna de PostgreSQL cuando no aplica ningún perfil. |
| `odoo_versions` | vacío | Perfiles de imagen por build; vea [Versiones de Odoo](#versiones-de-odoo). |
| `port_start`, `port_end` | `18000`, `19999` | Rango loopback para previews. |
| `command_timeout_seconds` | `900` | Límite para comandos externos. |
| `health_timeout_seconds` | `120` | Límite del healthcheck HTTP. |
| `max_concurrent_builds` | `2` | Workers del ejecutor API. |
| `cleanup_interval_seconds` | `0` | Frecuencia del scheduler; cero lo desactiva. |
| `destroyed_retention_seconds` | `0` | Retención antes de purgar; cero conserva indefinidamente. |
| `load_demo_data` | `true` | Carga datos demo requeridos por muchas pruebas Odoo/OCA. |
| `retain_failed_runtime` | `false` | Conserva contenedores fallidos para diagnóstico. |

## Versiones de Odoo

`odoo_versions` asocia un nombre de perfil con las imágenes sobre las que corre un build.
`postgres_image` es opcional y hereda el valor global.

```yaml
odoo_versions:
  "16.0": {odoo_image: odoo:16.0, postgres_image: postgres:15}
  "17.0": {odoo_image: odoo:17.0, postgres_image: postgres:15}
  "18.0": {odoo_image: odoo:18.0, postgres_image: postgres:16}
  "19.0": {odoo_image: odoo:19.0, postgres_image: postgres:16}
  "20.0": {odoo_image: odoo:20.0, postgres_image: postgres:16}
```

Un build resuelve su perfil en este orden:

1. El perfil solicitado: `--odoo-version`, el selector del dashboard u `odoo_version` en la API.
   Un nombre desconocido se rechaza.
2. La referencia Git del primer repositorio, cuando es igual al nombre de un perfil o empieza por
   él seguido de `-`, `_` o `/` (`17.0`, `17.0-fix-payment`). Gana el nombre más largo.
3. Los valores globales `odoo_image` y `postgres_image`, informados como `default`.

Las imágenes resueltas se guardan con el build, de modo que un cambio posterior de configuración
no altera los builds existentes. Los nombres de perfil admiten letras, dígitos, `.`, `_` y `-`;
`default` está reservado.

El runtime se adapta a la serie de la imagen: los datos demo se solicitan de forma explícita
desde 19.0, donde ya no se cargan por defecto, y el servidor del preview escucha siempre en todas
las interfaces del contenedor, algo que 20.0 ya no hace por sí solo. La etapa `install` falla
cuando Odoo deja sin instalar un módulo solicitado, por ejemplo porque la versión de su manifest
apunta a otra serie.

La plantilla de Compose monta el volumen de la base en `/var/lib/postgresql/data`; use imágenes
de PostgreSQL que conserven sus datos ahí (hasta `postgres:17`).

## Repositorios

Cada clave bajo `repositories` es un alias confiable. `target` debe ser único, `addons_subpath` debe
ser relativo y no puede escapar del checkout, y `allow_request_ref: false` limita solicitudes a
`default_ref`. Un número menor en `addons_priority` tiene mayor precedencia.

Las credenciales de remotos HTTPS/SSH deben proceder del helper de credenciales de Git disponible
en el host (por ejemplo, Git Credential Manager en Windows) o de SSH. Nunca las incluya en la URL o
en el repositorio.

Use `/` como separador en el YAML cuando sea posible: funciona en Windows y Linux. Las rutas locales
de repositorios siguen perteneciendo al host, por lo que un `config.local.yaml` puede usar, por
ejemplo, `C:/repos/addons` en Windows o `/srv/repos/addons` en Linux. No comparta una configuración
con rutas absolutas entre sistemas.

## Variables de entorno

| Variable | Reemplaza |
| --- | --- |
| `MINI_RUNBOT_CONFIG` | Ruta del archivo YAML. |
| `MINI_RUNBOT_DATABASE_URL` | `database_url`. |
| `MINI_RUNBOT_BUILDS_ROOT` | `builds_root`. |
| `MINI_RUNBOT_ODOO_IMAGE` | `odoo_image`. |
| `MINI_RUNBOT_CLEANUP_INTERVAL_SECONDS` | `cleanup_interval_seconds`. |

`config.local.yaml`, bases SQLite y `builds/` son estado local del operador y no deben versionarse.
En ambos sistemas, el usuario del proceso necesita permisos de lectura sobre los repositorios y de
escritura sobre la base SQLite y `builds_root`.

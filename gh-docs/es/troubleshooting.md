# Troubleshooting y runbook

Empiece siempre por el diagnóstico integrado desde el mismo entorno virtual y configuración que
usará el servicio:

```console
mini-runbot doctor
```

`doctor` comprueba Python, Git, Docker CLI, Compose v2, daemon, `builds_root` y repositorios. Es un
comando CLI; actualmente no existe un endpoint HTTP equivalente.

## Matriz de diagnóstico

| Síntoma | Comprobación | Acción |
| --- | --- | --- |
| No se carga configuración | Revise `MINI_RUNBOT_CONFIG` y que sea una ruta absoluta existente. | Vuelva a exportar la variable en el proceso que inicia Mini-Runbot. |
| Falla `docker-daemon` | Ejecute `docker version` y `docker info`. | Inicie Docker Desktop o Docker Engine y confirme contenedores Linux. |
| Falla `compose` | Ejecute `docker compose version`. | Instale/active Compose v2; `docker-compose` v1 no es suficiente. |
| Repositorio remoto inaccesible | Ejecute `git ls-remote ORIGEN REF` con las credenciales del mismo usuario. | Corrija el helper Git/SSH; no incruste secretos en la URL. |
| `No preview ports are available` | Revise el rango y procesos que escuchan en loopback. | Amplíe el rango o destruya únicamente builds conocidos que ya no necesite. |
| Falla `checkout` | Consulte `checkout.log` y la ref persistida. | Confirme alias, permiso a la ref y existencia de `addons_subpath`. |
| Falla `compose_validate` | Consulte el log y `runtime/compose.yaml`. | Corrija imágenes, montajes o valores configurados; no edite un workspace activo. |
| Falla `install` | Consulte la última salida de Odoo. | Revise dependencias, manifest, orden de addons y datos demo. |
| Falla `test` | Consulte el log de la etapa, no solo el estado del contenedor. | Corrija las pruebas Odoo/OCA reportadas antes de considerar válido el build. |
| Falla `healthcheck` | Revise `start` y `healthcheck.log`. | Compruebe puerto, proceso Odoo, tiempo configurado y logs del servicio. |
| Estado inconsistente tras reinicio | Detenga la API anterior y ejecute `mini-runbot recover`. | Inspeccione los IDs recuperados/fallidos y sus logs antes de limpiar. |

## Consultar evidencia

```console
mini-runbot build get BUILD_ID
mini-runbot build logs BUILD_ID
mini-runbot build logs BUILD_ID --stage test
```

La API limita la respuesta de logs a los últimos 100 000 bytes y valida que cada ruta registrada
sea hija directa de `workspace/logs`. Para investigar contenedores fallidos, active previamente
`retain_failed_runtime: true`; después destruya el build explícitamente cuando termine.

## Cleanup y recuperación

```console
mini-runbot cleanup --expired
mini-runbot cleanup --retained
mini-runbot recover
```

- `--expired` destruye runtimes vencidos.
- `--retained` solo purga cuando la retención configurada es positiva.
- `recover` clasifica ejecuciones interrumpidas y reconcilia Docker y puertos.

No ejecute recuperación mientras otra instancia pueda seguir trabajando. La destrucción elimina
contenedores y volúmenes del build; confirme siempre el ID.

## Particularidades por sistema

=== "Windows · PowerShell"

    - Docker Desktop debe usar contenedores Linux.
    - Verifique que la unidad que contiene `builds_root` esté compartida con Docker Desktop.
    - Exporte la configuración en la misma consola que ejecutará `serve`.

    ```powershell
    $env:MINI_RUNBOT_CONFIG = (Resolve-Path config.local.yaml).Path
    mini-runbot doctor
    ```

=== "Linux · Bash"

    - El usuario necesita acceso al socket Docker y permisos de escritura sobre `builds_root`.
    - Pertenecer al grupo `docker` equivale a privilegios administrativos sobre el host.
    - No resuelva errores de permisos ejecutando indiscriminadamente todo el servicio como root.

    ```bash
    export MINI_RUNBOT_CONFIG="$(realpath config.local.yaml)"
    mini-runbot doctor
    ```

## Backup y restauración

Detenga API, scheduler y builds antes de copiar estado. Respalde juntos:

- el archivo SQLite señalado por `database_url`;
- `builds_root`, incluidos logs y Compose renderizados;
- la configuración privada por un canal seguro, separada del repositorio.

Restaure en las mismas rutas o actualice la configuración antes de ejecutar `mini-runbot recover`.
Un backup de SQLite sin sus workspaces conserva auditoría, pero no permite inspeccionar logs ni
reconciliar todos los runtimes.

## Escalación

Al reportar un problema incluya versión de Mini-Runbot, sistema operativo, salida de `doctor`, ID,
estado, etapa fallida y resumen del log. Elimine tokens, URLs con credenciales y datos privados.

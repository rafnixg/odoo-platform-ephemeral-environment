# Referencia de CLI

La CLI y la API usan el mismo `BuildManager`, las mismas validaciones y las mismas transiciones.

## Inicializar configuración

```console
mini-runbot init
mini-runbot init --defaults
mini-runbot init --output otra-configuracion.yaml
```

Sin `--defaults`, el asistente pregunta por base SQLite, workspaces, imágenes, puertos, timeouts,
concurrencia, cleanup, retención y hasta diez repositorios permitidos. La escritura es exclusiva:
si el destino existe, el comando termina sin modificarlo. Al finalizar muestra cómo exportar
`MINI_RUNBOT_CONFIG` en PowerShell y Bash.

## Builds

Los comandos de una línea funcionan igual en PowerShell y Bash:

```console
# Crear y ejecutar
mini-runbot build create --repo custom --ref 16.0 --modules module_a,module_b --run

# Añadir repositorios
mini-runbot build create --repo custom --ref feature/x --extra-repo oca=16.0 --modules module_a --run

# Consultar
mini-runbot build list
mini-runbot build list --status running
mini-runbot build get BUILD_ID
mini-runbot build logs BUILD_ID --stage test

# Ejecutar un registro nuevo y destruir el runtime
mini-runbot build run BUILD_ID
mini-runbot build destroy BUILD_ID
```

`create`, `get`, `list`, `run` y `destroy` aceptan `--json` para integraciones. `--extra-repo
ALIAS=REF` se puede repetir hasta el límite de repositorios del dominio.

## Servicio y diagnóstico

```console
mini-runbot serve --host 127.0.0.1 --port 8000 --reload
mini-runbot doctor
mini-runbot recover
```

`recover` se ejecuta después de confirmar un reinicio del orquestador. Clasifica ejecuciones
interrumpidas, reconcilia leases y reintenta destrucciones pendientes.

## Limpieza

```console
mini-runbot cleanup --expired
mini-runbot cleanup --retained
mini-runbot cleanup --expired --retained --json
```

`--expired` destruye runtimes cuyo TTL terminó. `--retained` elimina definitivamente auditorías y
logs destruidos más antiguos que `destroyed_retention_seconds`; no hace nada cuando la retención es
cero.

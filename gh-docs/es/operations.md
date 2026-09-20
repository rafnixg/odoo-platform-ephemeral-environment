# Operación y seguridad

## Estado local

Trate como propiedad del operador:

- `config.local.yaml` y otros archivos de configuración privada.
- `mini_runbot.db` y demás bases SQLite.
- workspaces y logs bajo `builds/`.
- contenedores, redes y volúmenes de builds existentes.

No elimine ni reconstruya un build existente durante verificaciones. Cree uno identificable y
limpie únicamente sus recursos al terminar.

## Fallos y evidencia

Una etapa fallida conserva nombre, código de salida, mensaje y log. Si la limpieza posterior
también falla, el error original sigue siendo la causa principal. Con
`retain_failed_runtime: true`, los recursos fallidos se mantienen para inspección manual.

La destrucción usa el proyecto Compose y workspace validados del build, ejecuta `down --volumes
--remove-orphans` y es segura al repetirse. Por defecto conserva auditoría y logs.

## Expiración y retención

- `cleanup_interval_seconds > 0` activa el scheduler dentro del proceso API.
- `cleanup --expired` destruye runtimes vencidos.
- `destroyed_retention_seconds: 0` conserva evidencia indefinidamente.
- Una retención positiva más `cleanup --retained` purga registros y workspaces destruidos antiguos.

## Modelo de seguridad

- Solo se aceptan alias configurados; nunca URLs o rutas enviadas por clientes.
- Refs, módulos, destinos, IDs y rutas de log se validan en sus fronteras de confianza.
- Los comandos externos reciben arrays de argumentos y no se ejecutan mediante shell.
- PostgreSQL no publica puertos en el host; el preview se enlaza a loopback.
- Credenciales y secretos deben permanecer en mecanismos del host, fuera de configuración y logs.

!!! danger
    Un repositorio permitido puede ejecutar Python y procesos dentro del runtime Odoo. Docker no
    convierte este PoC en un servicio multiusuario seguro. Use un host dedicado y código confiable.

## Límites operativos

No hay autenticación, TLS, proxy inverso, cola durable, workers distribuidos, Kubernetes ni gestor
externo de secretos. SQLite y el ejecutor local están pensados para un solo host.

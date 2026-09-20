# ADR 0001: arquitectura de la fase 0 y estrategia de ejecución

- Estado: aceptada para la fase 0
- Fecha: 2026-09-19

## Contexto

El repositorio comenzó vacío. El objetivo era validar el lifecycle antes de disponer de todos los
repositorios Odoo, imágenes, módulos y dependencias necesarios para una ejecución real.

## Decisión

El primer incremento usa un dominio independiente de frameworks, puertos estrechos de repositorio y
runtime, SQLite mediante SQLAlchemy y servicios de aplicación compartidos por Typer y FastAPI.

La máquina de estados es explícita:

```text
NEW -> CHECKING_OUT -> PREPARING -> INSTALLING -> TESTING -> STARTING -> RUNNING
```

Cualquier estado activo puede fallar. Cualquier estado no destruido puede pasar por `DESTROYING` a
`DESTROYED`; repetir la destrucción es exitoso. `RUNNING` puede expirar antes de destruirse.

## Estrategia Git

Solo se aceptan alias configurados. Cada ref se resuelve a un SHA antes de crear un checkout
detached bajo `<builds_root>/<build_id>/sources/<target>`. Nunca se modifica el working tree del
usuario. Origen, ref, SHA, destino y prioridad quedan persistidos.

## Estrategia Docker Compose

Una plantilla Jinja se renderiza únicamente con valores validados o generados. Cada build recibe
proyecto Compose, red, volumen PostgreSQL, base de datos, workspace, filestore y puerto propios. El
archivo se valida con `docker compose config` antes de crear recursos.

Instalación, pruebas y arranque son invocaciones separadas. El estado `RUNNING` exige comandos
exitosos y healthcheck HTTP válido. La destrucción usa `down --volumes --remove-orphans` sobre el
proyecto validado y se puede repetir.

## Consecuencias

El dominio y la aplicación se prueban sin Docker y pueden cambiar de adaptadores sin modificar las
reglas de CLI/API. El aislamiento reduce colisiones, pero no permite ejecutar repositorios hostiles.

# Primeros pasos

## Requisitos

Mini-Runbot usa el mismo código y ciclo de vida en ambos sistemas:

- Python 3.12 y Git.
- Docker Compose v2, disponible como `docker compose`.
- Permiso de escritura sobre `builds_root` y acceso al daemon Docker.

=== "Windows"

    - Windows 10/11 con PowerShell.
    - Docker Desktop configurado para contenedores Linux.
    - Virtualización y WSL 2 habilitados cuando Docker Desktop los requiera.

=== "Linux"

    - Una distribución Linux con Bash.
    - Docker Engine y el plugin Docker Compose v2.
    - El usuario debe poder acceder al socket Docker. Pertenecer al grupo `docker` equivale a
      conceder privilegios elevados sobre el host; aplique la política de seguridad de su equipo.

## Instalación

### Aplicación aislada con pipx

Después de la primera publicación en PyPI, la instalación recomendada en ambos sistemas será:

=== "Windows · PowerShell"

    ```powershell
    py -3.12 -m pip install --user pipx
    py -3.12 -m pipx ensurepath
    pipx install mini-runbot
    mini-runbot init
    ```

=== "Linux · Bash"

    ```bash
    python3.12 -m pip install --user pipx
    python3.12 -m pipx ensurepath
    pipx install mini-runbot
    mini-runbot init
    ```

Mientras se prepara esa publicación, clone el repositorio y ejecute `pipx install .` desde su raíz.
`pipx` mantiene la aplicación y sus dependencias separadas del Python del sistema.

### Entorno de desarrollo

Desde la raíz del repositorio:

=== "Windows · PowerShell"

    ```powershell
    py -3.12 -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -e ".[dev]"
    ```

=== "Linux · Bash"

    ```bash
    python3.12 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e ".[dev]"
    ```

## Crear la configuración

El asistente toma como base el ejemplo incluido en la aplicación, pregunta por runtime,
concurrencia, retención y repositorios permitidos, y crea `config.local.yaml` únicamente si no
existe:

```console
mini-runbot init
```

Para aceptar todos los valores de `config.example.yaml` sin preguntas:

```console
mini-runbot init --defaults
```

Después exporte su ruta absoluta:

=== "Windows · PowerShell"

    ```powershell
    $env:MINI_RUNBOT_CONFIG = (Resolve-Path config.local.yaml).Path
    mini-runbot doctor
    ```

=== "Linux · Bash"

    ```bash
    export MINI_RUNBOT_CONFIG="$(realpath config.local.yaml)"
    mini-runbot doctor
    ```

`doctor` comprueba Python, Git, Docker, Compose, el daemon, el directorio de builds y los orígenes
Git configurados. Resuelva cualquier fallo antes de crear un build real.

## Iniciar el dashboard

El comando es idéntico en PowerShell y Bash:

```console
mini-runbot serve --reload
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000). El dashboard permite crear, filtrar y
consultar builds, seguir sus etapas, leer logs, abrir previews y destruir runtimes.

## Primer build

El alias `custom` debe existir en la [configuración](configuration.md):

```console
mini-runbot build create --repo custom --ref 16.0 --modules sale,website --run
```

Guarde el ID mostrado. Puede consultar el resultado con `mini-runbot build get BUILD_ID` y destruir
el runtime con `mini-runbot build destroy BUILD_ID`.

!!! note
    Sin `--run`, la CLI solo crea el registro. La API, en cambio, devuelve `202 Accepted` y entrega
    automáticamente el build al ejecutor local.

## Demo controlada

La demo usa `config.demo.yaml`, resuelve el `HEAD` de este repositorio e instala el módulo
`mini_runbot_demo`.

=== "Windows · PowerShell"

    ```powershell
    powershell -ExecutionPolicy Bypass -File .\scripts\demo.ps1
    ```

=== "Linux · Bash"

    ```bash
    export MINI_RUNBOT_CONFIG="$(realpath config.demo.yaml)"
    python -m mini_runbot.cli.main doctor
    python -m mini_runbot.cli.main build create \
      --repo demo --ref HEAD --modules mini_runbot_demo --run
    ```

La demo deja el preview activo intencionalmente. Destruya el ID reportado cuando termine.

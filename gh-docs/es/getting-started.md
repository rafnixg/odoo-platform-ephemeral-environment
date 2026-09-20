# Primeros pasos

## Requisitos

- Windows con PowerShell.
- Python 3.12.
- Git.
- Docker Desktop usando contenedores Linux para builds reales.

## Instalación

Desde la raíz del repositorio:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Copie `config.example.yaml` a un archivo local ignorado por Git, ajuste los repositorios permitidos
y exporte su ruta absoluta:

```powershell
Copy-Item config.example.yaml config.local.yaml
$env:MINI_RUNBOT_CONFIG = (Resolve-Path config.local.yaml)
mini-runbot doctor
```

`doctor` comprueba Python, Git, Docker, Compose, el daemon, el directorio de builds y los orígenes
Git configurados.

## Iniciar el dashboard

```powershell
mini-runbot serve --reload
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000). El dashboard permite crear, filtrar y
consultar builds, seguir sus etapas, leer logs, abrir previews y destruir runtimes.

## Primer build

El alias `custom` debe existir en la [configuración](configuration.md):

```powershell
mini-runbot build create `
  --repo custom `
  --ref 16.0 `
  --modules sale,website `
  --run
```

Guarde el ID mostrado. Puede consultar el resultado con `mini-runbot build get BUILD_ID` y destruir
el runtime con `mini-runbot build destroy BUILD_ID`.

!!! note
    Sin `--run`, la CLI solo crea el registro. La API, en cambio, devuelve `202 Accepted` y entrega
    automáticamente el build al ejecutor local.

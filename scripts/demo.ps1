$ErrorActionPreference = "Stop"
$env:MINI_RUNBOT_CONFIG = (Resolve-Path ".\config.demo.yaml").Path

python -m mini_runbot.cli.main doctor
python -m mini_runbot.cli.main build create `
  --repo demo `
  --ref HEAD `
  --modules mini_runbot_demo `
  --run

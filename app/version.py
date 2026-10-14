VERSION = "1.2.0"
REPO = "mozg9637-creator/NovaOffice-source"
WORKFLOW_NAME = "build-installer"
ARTIFACT = "NovaOffice-Setup"

try:  # файл создаётся на сборке в GitHub Actions
    from build_info import BUILD, SHA
except Exception:
    BUILD, SHA = 0, ""

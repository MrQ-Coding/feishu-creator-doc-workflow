# feishu-creator-doc-workflow

Codex skill for operating `feishu-creator` safely with heading- and section-level document workflows.

## Install

### macOS / Linux

One-command install:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/MrQ-Coding/feishu-creator-doc-workflow/main/scripts/install.sh)
```

From a local clone:

```bash
bash scripts/install.sh
```

### Windows PowerShell

One-command install:

```powershell
irm https://raw.githubusercontent.com/MrQ-Coding/feishu-creator-doc-workflow/main/scripts/install.ps1 | iex
```

From a local clone:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

### Windows Git Bash

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/MrQ-Coding/feishu-creator-doc-workflow/main/scripts/install.sh)
```

## Notes

- Default install path: `~/.codex/skills/feishu-creator-doc-workflow`
- Set `CODEX_HOME` first if you use a non-default Codex home directory.
- Restart Codex after installing or updating the skill.

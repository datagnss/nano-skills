---
name: datagnss-skill-installer
description: Install DATAGNSS Codex skills from this repository when the user asks to install, sync, or update a skill such as the DATAGNSS NANO RTK Receiver skill `nano-rtk-config` from a local path or GitHub repo. Use this to select the right skill folder, copy it into the local Codex skills directory, and verify the installation.
---

# DATAGNSS Skill Installer

Install skills from this repository into the local Codex skills directory.

This repository currently ships one product-specific skill for the **DATAGNSS NANO RTK Receiver**.

Company website: [www.datagnss.com](https://www.datagnss.com)

## Default target

- Install into `${CODEX_HOME:-$HOME/.codex}/skills`.
- If the user names a specific destination, use that destination instead.

## Available skill

- `skills/nano-rtk-config`
  - Configure and inspect **DATAGNSS NANO RTK Receiver** devices over the HTTP API.
  - Use when the user wants firmware, status, GNSS, Wi-Fi, RTCM, NTRIP, TCP server, external port, reboot, or similar device operations by IP or hostname.

## Installation workflow

1. Confirm which skill the user wants from this repository.
2. Create the target directory if it does not exist.
3. Replace any existing installed copy of the same skill only when the user asked to install or update it.
4. Copy the selected skill folder into the target directory.
5. Verify the copied files exist:
   - `SKILL.md`
   - `agents/openai.yaml` when present
   - `references/` and `scripts/` when present
6. If the repository also contains a usage `README.md`, point the user to it for examples.

## Complete installation steps

Install `nano-rtk-config` from a local checkout of this repository:

1. Change into the repository root.
2. Create the destination directory:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
```

3. Copy the skill folder:

```bash
cp -R skills/nano-rtk-config "${CODEX_HOME:-$HOME/.codex}/skills/"
```

4. Verify the installed files:

```bash
find "${CODEX_HOME:-$HOME/.codex}/skills/nano-rtk-config" -maxdepth 2 -type f | sort
```

5. Validate the installed skill metadata:

```bash
python /home/rinex20/.codex/skills/.system/skill-creator/scripts/quick_validate.py "${CODEX_HOME:-$HOME/.codex}/skills/nano-rtk-config"
```

6. Start using the installed skill with prompts such as:
   - `The device is 10.10.168.148. Check the firmware version.`
   - `Inspect the current status on 10.10.168.148.`
   - `Switch 10.10.168.159 to rover mode and configure the NTRIP client.`

## Install commands

Install `nano-rtk-config`:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/nano-rtk-config "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Replace an existing installed copy:

```bash
rm -rf "${CODEX_HOME:-$HOME/.codex}/skills/nano-rtk-config"
cp -R skills/nano-rtk-config "${CODEX_HOME:-$HOME/.codex}/skills/"
```

## Validation

- Check that `${CODEX_HOME:-$HOME/.codex}/skills/nano-rtk-config/SKILL.md` exists after copying.
- Optionally run:

```bash
python /home/rinex20/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/nano-rtk-config
```

- If local device access is available, a safe smoke test is:

```bash
python skills/nano-rtk-config/scripts/nano_rtk_api.py 10.10.168.148 GET /system/info
```

## Response style

- Tell the user which skill folder was installed and where it was copied.
- If replacing an existing installed copy, say that explicitly.
- If installation cannot proceed, report the exact missing path or command failure.

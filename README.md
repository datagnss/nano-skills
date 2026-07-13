# nano-skills

This repository contains reusable Codex skills for DATAGNSS devices and workflows.

The current published skill is specifically for the **DATAGNSS NANO RTK Receiver** product line.

Company website: [www.datagnss.com](https://www.datagnss.com)

## Included skill

- `skills/nano-rtk-config`: configure and inspect **DATAGNSS NANO RTK Receiver** devices over the HTTP API

## What `nano-rtk-config` covers

Use this skill when a **DATAGNSS NANO RTK Receiver** is reachable by IP or hostname and Codex needs to:

- query firmware, model, GNSS version, or device ID
- inspect runtime status, features, or full config
- configure Wi-Fi, GNSS mode, RTCM source, NTRIP client/server, TCP server, or external port
- reboot the device when explicitly requested

The skill is read-first by default and avoids reset, reboot, or firmware update unless the user clearly asks for them.

## Repository layout

```text
skills/
  nano-rtk-config/
    SKILL.md
    agents/openai.yaml
    references/
    scripts/
sessions.md
```

## Install

Install the skill into Codex's local skills directory.

1. Clone or download this repository to a local working directory.
2. Go to the repository root.
3. Copy `skills/nano-rtk-config` into `${CODEX_HOME:-$HOME/.codex}/skills`.
4. Verify that the installed folder contains `SKILL.md`, `agents/openai.yaml`, `references/`, and `scripts/`.

Install the skill:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/nano-rtk-config "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Verify the installation:

```bash
find "${CODEX_HOME:-$HOME/.codex}/skills/nano-rtk-config" -maxdepth 2 -type f | sort
```

If you are updating an existing local installation, replacing the existing directory is usually enough:

```bash
rm -rf "${CODEX_HOME:-$HOME/.codex}/skills/nano-rtk-config"
cp -R skills/nano-rtk-config "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Validate the installed skill metadata:

```bash
python /home/rinex20/.codex/skills/.system/skill-creator/scripts/quick_validate.py "${CODEX_HOME:-$HOME/.codex}/skills/nano-rtk-config"
```

The repository also includes a root-level [SKILL.md](/data/rinex20/work/nano-skills/SKILL.md) that acts as an installer entrypoint for future Codex-driven installation flows.

## Trigger examples

Typical prompts that should trigger this skill:

- `The device is 10.10.168.148. Check the firmware version.`
- `Inspect the current status on 10.10.168.148.`
- `Switch 10.10.168.159 to rover mode and configure the NTRIP client.`
- `Check whether 10.10.168.148 supports NTRIP server mode.`

The bundled UI metadata lives in `skills/nano-rtk-config/agents/openai.yaml`.

## Local validation

Validate the skill metadata:

```bash
python /home/rinex20/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/nano-rtk-config
```

Validate the repository installer entrypoint:

```bash
python /home/rinex20/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

Query a device with the bundled helper:

```bash
python skills/nano-rtk-config/scripts/nano_rtk_api.py 10.10.168.148 GET /system/info
```

Check runtime status:

```bash
python skills/nano-rtk-config/scripts/nano_rtk_api.py 10.10.168.148 GET /system/status
```

Patch one config field:

```bash
python skills/nano-rtk-config/scripts/nano_rtk_api.py 10.10.168.148 PATCH /config --body '{"data":{"wifi.ssid":"NANO_RTK_AP"}}'
```

The helper script accepts:

- IP, hostname, or full base URL
- short paths like `/system/info`, auto-expanded to `/api/v1/system/info`
- full API paths like `/api/v1/system/info`, sent unchanged

## Publish checklist

1. Validate `skills/nano-rtk-config`.
2. Verify at least one read-only request against a live device.
3. Review `sessions.md`.
4. Commit on a dedicated branch before publishing.

## Development flow

Recommended branch flow for this repo:

1. Create a feature branch from `main`, for example `codex/nano-rtk-config-publish`.
2. Update the skill and append the change summary to `sessions.md`.
3. Run metadata validation and at least one live read-only device check.
4. Commit on the branch.
5. Push the branch and open a PR back to `main`.

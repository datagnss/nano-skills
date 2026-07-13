# nano-skills

This repository contains reusable Codex skills for DATAGNSS workflows.

## Included skill

- `skills/nano-rtk-config`: configure and inspect NANO RTK devices over the HTTP API

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

## Local validation

Validate the skill metadata:

```bash
python /home/rinex20/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/nano-rtk-config
```

Query a device with the bundled helper:

```bash
python skills/nano-rtk-config/scripts/nano_rtk_api.py 10.10.168.148 GET /system/info
```

## Publish checklist

1. Validate `skills/nano-rtk-config`.
2. Verify at least one read-only request against a live device.
3. Review `sessions.md`.
4. Commit on a dedicated branch before publishing.

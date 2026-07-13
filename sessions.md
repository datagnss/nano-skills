# Sessions

## 2026-06-26

- Created the `nano-rtk-config` skill to configure NANO RTK devices from only the device IP.
- Read and captured the API reference from `http://10.10.168.159/api`.
- Added `references/api.md` for the endpoint summary and `agents/openai.yaml` for UI metadata.
- Initialized git for this repo and reorganized the skill under `skills/nano-rtk-config` so it can be installed directly from a GitHub repo/path.
- Installed `nano-rtk-config` into `/home/rinex20/.codex/skills/nano-rtk-config` for Codex use and verified the source directory contents.
- Reconfigured `10.10.168.159` from base mode to rover mode, enabled NTRIP client `gps1:123456@clas.datagnss.com:2101/SHIGINO1`, and switched RTCM source to NTRIP; verification showed the client connected successfully.

## 2026-07-13

- Hardened `skills/nano-rtk-config/SKILL.md` with a clearer discovery workflow, failure triage, helper script usage, and safer request mapping for publish-ready use.
- Added `skills/nano-rtk-config/scripts/nano_rtk_api.py` so the skill can issue repeatable HTTP API requests without ad hoc `curl` commands.
- Expanded `skills/nano-rtk-config/references/api.md` with usage guidance for read vs write endpoints and practical request patterns.
- Added repository-level `README.md` and `.gitignore` to make the repo easier to validate and publish.

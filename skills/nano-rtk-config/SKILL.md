---
name: nano-rtk-config
description: Configure DATAGNSS NANO RTK Receiver devices over the HTTP API when the user provides the device IP or asks for firmware, status, Wi-Fi, GNSS, NTRIP, RTCM, TCP server, reboot, or related device operations.
---

# NANO RTK Config

Use this skill when the user wants to inspect or configure a NANO RTK device and can provide the device IP or hostname.

If the user asks how to start using a NANO RTK Receiver or does not yet know the device IP, first guide them through initial access:

1. Search for the device Wi-Fi SSID in the form `NANO_RTK_xxxx`.
2. Connect to that Wi-Fi using password `datagnss`.
3. Open `http://192.168.4.1` in a browser to access the web settings page.
4. Enter the target STA-mode Wi-Fi SSID and password so the receiver can join the local network.
5. After the device joins the LAN and obtains an IP address, continue with API-based configuration by IP.

## Standard onboarding reply

When the user asks a broad question such as "How do I use it?" and does not yet provide the device IP, reply in the user's language with a short guided setup like this:

1. Search for the device Wi-Fi SSID in the form `NANO_RTK_xxxx`.
2. Connect to that Wi-Fi using password `datagnss`.
3. Open `http://192.168.4.1` in a browser.
4. In the web settings page, enter the STA-mode Wi-Fi SSID and password for the target local network.
5. Wait for the receiver to join that LAN and obtain an IP address.
6. Use that IP address for follow-up configuration such as status checks, Wi-Fi updates, GNSS settings, NTRIP, RTCM, or TCP server setup.

## Core rules

- If the user gives only the IP, use that as the device base URL and continue with API discovery.
- Ask follow-up questions only for missing intent or credentials.
- Do not reset configuration, reboot, or upload firmware unless the user explicitly asks.
- Start with read-only discovery before proposing changes.
- Prefer the bundled helper script at `scripts/nano_rtk_api.py` for repeatable requests. Read `references/api.md` when endpoint names or payload fields matter.

## Default workflow

1. Build the base URL as `http://<device-ip>/api/v1`.
2. Read current state first with:
   - `GET /api/v1/system/info`
   - `GET /api/v1/system/features`
   - `GET /api/v1/config` when changing configuration
   - `GET /api/v1/system/status` when runtime state matters
3. Summarize the current values that are relevant to the request.
4. Map the user request to the smallest safe API call.
5. Apply the change only after the intended delta is clear.
6. Verify with `GET /api/v1/config` or `GET /api/v1/system/status`.
7. Reboot only if the endpoint requires it or the user explicitly asks.

## Helper script

Use the bundled helper for deterministic requests:

```bash
python skills/nano-rtk-config/scripts/nano_rtk_api.py 10.10.168.148 GET /system/info
python skills/nano-rtk-config/scripts/nano_rtk_api.py 10.10.168.148 PATCH /config --body '{"data":{"wifi.ssid":"NANO_RTK_AP"}}'
```

Notes:

- The script accepts an IP, hostname, or full base URL.
- A path like `/system/info` is automatically expanded to `/api/v1/system/info`.
- A path that already starts with `/api/` is sent unchanged.

## Endpoint selection

- Wi-Fi join: `POST /api/v1/wifi/connect`
- Partial config update: `PATCH /api/v1/config`
- Full config replace: `PUT /api/v1/config`
- GNSS mode or output rate: `POST /api/v1/gnss/apply`
- RTCM source: `POST /api/v1/rtcm/apply_source`
- NTRIP client: `POST /api/v1/ntrip/client/apply`
- NTRIP server: `POST /api/v1/ntrip/server/apply`
- TCP server: `POST /api/v1/tcp_server/apply`
- External serial port: `POST /api/v1/external_port/apply`
- Reboot: `POST /api/v1/system/reboot`
- Factory reset: `POST /api/v1/system/reset_config` only when explicitly requested
- Firmware update: `POST /update` or `POST /api/v1/update`

## Common request mapping

- Query version, device ID, or model: `GET /api/v1/system/info`
- Check whether NTRIP client/server is supported: `GET /api/v1/system/features`
- Inspect live GNSS, network, or service state: `GET /api/v1/system/status`
- Update one or two config keys with known dotted names: `PATCH /api/v1/config`
- Apply a service-specific workflow with validation rules: use the dedicated `POST .../apply` endpoint

## Practical behavior

- Prefer `PATCH /api/v1/config` for small edits when the target field is clear.
- Prefer the dedicated endpoint for services that have their own API, such as Wi-Fi, GNSS, RTCM, NTRIP, TCP server, or external port.
- Treat `GET /api/v1/system/features` as capability detection before proposing NTRIP client/server operations.
- For connect/setup tasks, summarize the current config before changing it so the user knows what will be modified.
- For failure cases, separate network reachability, API error, and device-side validation errors.
- When the user asks for a simple check such as firmware version or status, do not read the full config unless it is needed.

## Failure triage

Check failures in this order:

1. Reachability: confirm the exact URL and whether the HTTP request connected at all.
2. Endpoint selection: confirm whether the path should be `/api/v1/...` or a legacy top-level path such as `/update`.
3. Request shape: validate JSON keys, value types, and enum values against `references/api.md`.
4. Device validation: report the exact API error body instead of paraphrasing it away.
5. Post-change verification: if the write call succeeded, confirm the changed fields with a fresh read.

## Safety notes

- Never assume a reset is acceptable.
- Never upload firmware without the user supplying a file and explicitly requesting the update.
- If the device is unreachable, report the exact URL that failed and the stage that failed.
- Avoid full-config replacement unless the user explicitly wants to replace the entire config.

## Minimal interaction style

- If the user only provides an IP and a goal, continue with discovery and then ask only the minimum remaining questions.
- If the goal is a common preset, state the discovered current values and then make the smallest API change that satisfies the request.
- Keep responses action-oriented: current state, intended change, verification result, and any remaining risk.

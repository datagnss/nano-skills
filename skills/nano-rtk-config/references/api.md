# NANO RTK API Reference

Use this file when you need the concrete endpoint or payload shape. Keep `SKILL.md` for workflow and safety rules.

Base URL:

```text
http://<device-ip>/api/v1
```

Default AP mode:

```text
http://192.168.4.1/api/v1
```

## Response model

- `200`: success
- `400`: bad request, usually `{"error":"..."}`
- `500`: internal error

## Discovery

### `GET /system/info`

Lightweight device info such as firmware, GNSS versions, device ID, and model.

### `GET /system/features`

Capability flags, for example:

```json
{
  "ntrip_server": true,
  "ntrip_client": true
}
```

### `GET /config`

Returns the full configuration tree.

Use this only when the task requires configuration inspection or post-change verification.

### `GET /system/status`

Returns real-time GNSS, network, service, and hardware state.

Use this for runtime diagnostics such as GNSS fix, network status, NTRIP state, or Bluetooth connections.

## Configuration

### `PUT /config`

Replace the full configuration. The device reboots after success.

### `PATCH /config`

Partial update using dotted keys.

Example:

```json
{
  "data": {
    "wifi.ssid": "NANO_RTK_AP",
    "wifi.password": "datagnss",
    "ntrip.client.enabled": "1"
  }
}
```

Good fit for small edits where the dotted key is already known.

## Network

### `POST /wifi/connect`

Body:

```json
{
  "ssid": "MyNetwork",
  "password": "mypassword"
}
```

Use when the user wants the device to join an existing AP.

### `POST /tcp_server/apply`

Body:

```json
{
  "enabled": true
}
```

Use the dedicated endpoint instead of patching raw config keys when possible.

### `POST /external_port/apply`

Body:

```json
{
  "baud_rate": 230400,
  "swap_rx_tx": false
}
```

Allowed baud rates:

- `9600`
- `57600`
- `115200`
- `230400`
- `460800`

## GNSS and corrections

### `POST /gnss/apply`

Key fields:

- `mode`: `0` Rover, `1` Base, `2` Unset, `3` Raw
- `output_rate`: `1`, `5`, `10`
- `fixed_base.mode`: `0` LLA, `1` ECEF, `2` Survey

Read current config first before changing GNSS mode, especially when switching between rover and base behavior.

### `POST /rtcm/apply_source`

Body:

```json
{
  "rtcm_source": 2
}
```

Values:

- `0`: Bluetooth
- `1`: External UART
- `2`: NTRIP Client

### `POST /ntrip/client/apply`

Body:

```json
{
  "enabled": true,
  "server": "ntrip.example.com",
  "port": 2101,
  "mountpoint": "MOUNT1",
  "user": "username",
  "password": "password",
  "version": 2,
  "send_gga": true
}
```

Check `GET /system/features` first to confirm that the device advertises NTRIP client support.

### `POST /ntrip/server/apply`

Body:

```json
{
  "enabled": true,
  "server": "0.0.0.0",
  "port": 2101,
  "mountpoint": "BASE1",
  "auth": "password",
  "source": 0
}
```

Check `GET /system/features` first to confirm that the device advertises NTRIP server support.

## System actions

### `POST /system/reboot`

Reboots after a short delay.

### `POST /system/reset_config`

Factory reset. Only use when the user explicitly requests it.

## Firmware update

### `POST /update`

Multipart upload. Also available as `POST /api/v1/update`.

Supported formats:

- `DGFW`
- `DGFM APP`
- `DGFM SPIFFS`
- native ESP32 firmware

## Practical request patterns

- Version query: `GET /system/info`
- Capability query: `GET /system/features`
- Runtime diagnostics: `GET /system/status`
- Read-before-write config workflow: `GET /config` then `PATCH /config`
- Service workflow: call the dedicated `.../apply` endpoint and then verify with `GET /config` or `GET /system/status`

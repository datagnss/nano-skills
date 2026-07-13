import contextlib
import io
import json
import pathlib
import sys
import unittest
from email.message import Message
from unittest import mock


SCRIPT_DIR = pathlib.Path(__file__).resolve().parents[1] / "skills" / "nano-rtk-config" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import nano_rtk_api


class FakeResponse:
    def __init__(self, payload: bytes, content_type: str = "application/json") -> None:
        self._payload = payload
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class NanoRtkApiTests(unittest.TestCase):
    def test_normalize_base_adds_scheme_and_trims_slash(self) -> None:
        self.assertEqual(nano_rtk_api.normalize_base("10.10.168.148/"), "http://10.10.168.148")
        self.assertEqual(nano_rtk_api.normalize_base("https://device.local/"), "https://device.local")

    def test_normalize_path_adds_prefix_for_short_paths(self) -> None:
        self.assertEqual(nano_rtk_api.normalize_path("system/info"), "/api/v1/system/info")
        self.assertEqual(nano_rtk_api.normalize_path("/system/info"), "/api/v1/system/info")
        self.assertEqual(nano_rtk_api.normalize_path("/api/v1/system/info"), "/api/v1/system/info")

    def test_build_url_joins_base_and_path(self) -> None:
        self.assertEqual(
            nano_rtk_api.build_url("10.10.168.148", "/system/status"),
            "http://10.10.168.148/api/v1/system/status",
        )

    def test_parse_body_returns_encoded_json(self) -> None:
        payload = nano_rtk_api.parse_body('{"data":{"wifi.ssid":"NANO_RTK_AP"}}')
        self.assertEqual(json.loads(payload.decode("utf-8")), {"data": {"wifi.ssid": "NANO_RTK_AP"}})

    def test_parse_body_none_returns_none(self) -> None:
        self.assertIsNone(nano_rtk_api.parse_body(None))
        self.assertIsNone(nano_rtk_api.parse_body(""))

    def test_parse_body_invalid_json_exits(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            nano_rtk_api.parse_body("{invalid")
        self.assertIn("Invalid JSON body", str(ctx.exception))

    def test_emit_response_pretty_prints_json(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            nano_rtk_api.emit_response(b'{"b":1,"a":2}', "application/json", compact=False)
        self.assertEqual(stdout.getvalue(), '{\n  "a": 2,\n  "b": 1\n}\n')

    def test_emit_response_compact_json(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            nano_rtk_api.emit_response(b'{"b":1,"a":2}', "application/json", compact=True)
        self.assertEqual(stdout.getvalue(), '{"b":1,"a":2}\n')

    def test_emit_response_plain_text(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            nano_rtk_api.emit_response(b"ok", "text/plain", compact=False)
        self.assertEqual(stdout.getvalue(), "ok\n")

    @mock.patch("nano_rtk_api.urllib.request.urlopen")
    def test_run_request_success_uses_json_headers(self, mock_urlopen: mock.Mock) -> None:
        mock_urlopen.return_value = FakeResponse(b'{"ok":true}')
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = nano_rtk_api.run_request(
                "patch",
                "10.10.168.148",
                "/config",
                '{"data":{"wifi.ssid":"NANO_RTK_AP"}}',
                5.0,
                False,
            )

        self.assertEqual(exit_code, 0)
        self.assertIn('"ok": true', stdout.getvalue())
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://10.10.168.148/api/v1/config")
        self.assertEqual(request.get_method(), "PATCH")
        self.assertEqual(request.headers["Accept"], "application/json")
        self.assertEqual(request.headers["Content-type"], "application/json")
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"data": {"wifi.ssid": "NANO_RTK_AP"}})

    @mock.patch("nano_rtk_api.urllib.request.urlopen")
    def test_run_request_http_error_returns_2(self, mock_urlopen: mock.Mock) -> None:
        headers = Message()
        headers["Content-Type"] = "application/json"
        request = nano_rtk_api.urllib.request.Request("http://10.10.168.148/api/v1/system/info")
        error = nano_rtk_api.urllib.error.HTTPError(
            request.full_url,
            404,
            "Not Found",
            headers,
            io.BytesIO(b'{"error":"missing"}'),
        )
        mock_urlopen.side_effect = error

        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = nano_rtk_api.run_request("GET", "10.10.168.148", "/system/info", None, 5.0, True)

        self.assertEqual(exit_code, 2)
        self.assertIn("HTTP 404 for http://10.10.168.148/api/v1/system/info", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), '{"error":"missing"}\n')

    @mock.patch("nano_rtk_api.urllib.request.urlopen")
    def test_run_request_url_error_returns_3(self, mock_urlopen: mock.Mock) -> None:
        mock_urlopen.side_effect = nano_rtk_api.urllib.error.URLError("timed out")

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = nano_rtk_api.run_request("GET", "10.10.168.148", "/system/info", None, 5.0, False)

        self.assertEqual(exit_code, 3)
        self.assertIn("Request failed for http://10.10.168.148/api/v1/system/info: timed out", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

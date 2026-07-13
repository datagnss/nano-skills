import contextlib
import io
import json
import pathlib
import socket
import sys
import unittest
from email.message import Message
from unittest import mock
import urllib.error


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


class FakeSocketConnection:
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

    def test_candidate_hosts_expands_subnet(self) -> None:
        self.assertEqual(nano_rtk_api.candidate_hosts("192.168.4.0/30"), ["192.168.4.1", "192.168.4.2"])

    def test_is_candidate_local_ip_filters_invalid_addresses(self) -> None:
        self.assertTrue(nano_rtk_api.is_candidate_local_ip("192.168.4.12"))
        self.assertFalse(nano_rtk_api.is_candidate_local_ip("127.0.0.1"))
        self.assertFalse(nano_rtk_api.is_candidate_local_ip("0.0.0.0"))

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

    def test_parse_json_payload_non_json_returns_none(self) -> None:
        self.assertIsNone(nano_rtk_api.parse_json_payload(b"ok", "text/plain"))

    def test_summarize_discovered_device_prefers_known_fields(self) -> None:
        summary = nano_rtk_api.summarize_discovered_device(
            "192.168.4.12",
            {"data": {"model": "NANO RTK", "fw_version": "1.0.0", "device_id": "abc"}},
        )
        self.assertEqual(
            summary,
            {"ip": "192.168.4.12", "model": "NANO RTK", "fw_version": "1.0.0", "device_id": "abc"},
        )

    def test_subnet_prefix_for_ip_defaults_private_networks_to_24(self) -> None:
        self.assertEqual(nano_rtk_api.subnet_prefix_for_ip("192.168.4.12"), 24)
        self.assertEqual(nano_rtk_api.subnet_prefix_for_ip("10.10.20.30"), 24)

    def test_subnet_prefix_for_ip_uses_16_for_link_local(self) -> None:
        self.assertEqual(nano_rtk_api.subnet_prefix_for_ip("169.254.10.20"), 16)

    @mock.patch("nano_rtk_api.socket.gethostbyname_ex")
    @mock.patch("nano_rtk_api.socket.getaddrinfo")
    @mock.patch("nano_rtk_api.socket.socket")
    def test_discover_local_ips_collects_and_deduplicates_candidates(
        self,
        mock_socket_cls: mock.Mock,
        mock_getaddrinfo: mock.Mock,
        mock_gethostbyname_ex: mock.Mock,
    ) -> None:
        fake_socket = mock.MagicMock()
        fake_socket.__enter__.return_value = fake_socket
        fake_socket.getsockname.return_value = ("192.168.4.20", 12345)
        mock_socket_cls.return_value = fake_socket
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_DGRAM, 0, "", ("192.168.4.21", 0)),
            (socket.AF_INET, socket.SOCK_DGRAM, 0, "", ("127.0.0.1", 0)),
        ]
        mock_gethostbyname_ex.return_value = ("host", [], ["192.168.4.20", "10.0.0.5"])

        self.assertEqual(nano_rtk_api.discover_local_ips(), ["10.0.0.5", "192.168.4.20", "192.168.4.21"])

    @mock.patch("nano_rtk_api.discover_local_ips")
    def test_infer_local_subnets_builds_cidrs(self, mock_local_ips: mock.Mock) -> None:
        mock_local_ips.return_value = ["192.168.4.20", "10.10.20.30", "169.254.5.6", "192.168.4.20"]
        self.assertEqual(
            nano_rtk_api.infer_local_subnets(),
            ["192.168.4.0/24", "10.10.20.0/24", "169.254.0.0/16"],
        )

    @mock.patch("nano_rtk_api.socket.create_connection")
    def test_is_http_service_reachable_true(self, mock_connect: mock.Mock) -> None:
        mock_connect.return_value = FakeSocketConnection()
        self.assertTrue(nano_rtk_api.is_http_service_reachable("192.168.4.12", 0.2))

    @mock.patch("nano_rtk_api.socket.create_connection")
    def test_is_http_service_reachable_false(self, mock_connect: mock.Mock) -> None:
        mock_connect.side_effect = OSError("refused")
        self.assertFalse(nano_rtk_api.is_http_service_reachable("192.168.4.12", 0.2))

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
        error.close()

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

    @mock.patch("nano_rtk_api.make_request")
    def test_probe_host_returns_summary_for_reachable_device(self, mock_make_request: mock.Mock) -> None:
        mock_make_request.return_value = (
            b'{"data":{"model":"NANO RTK","fw_version":"1.2.3","device_id":"dev-1"}}',
            "application/json",
        )

        result = nano_rtk_api.probe_host("192.168.4.12", "/system/info", 0.2)

        self.assertEqual(
            result,
            {"ip": "192.168.4.12", "model": "NANO RTK", "fw_version": "1.2.3", "device_id": "dev-1"},
        )

    @mock.patch("nano_rtk_api.make_request")
    def test_probe_host_returns_none_on_url_error(self, mock_make_request: mock.Mock) -> None:
        mock_make_request.side_effect = urllib.error.URLError("timed out")
        self.assertIsNone(nano_rtk_api.probe_host("192.168.4.12", "/system/info", 0.2))

    @mock.patch("nano_rtk_api.probe_host")
    @mock.patch("nano_rtk_api.is_http_service_reachable")
    def test_discover_devices_prints_sorted_results(
        self,
        mock_reachable: mock.Mock,
        mock_probe_host: mock.Mock,
    ) -> None:
        def fake_reachable(host: str, timeout: float):
            return host in {"192.168.4.1", "192.168.4.3"}

        def fake_probe(host: str, path: str, timeout: float):
            if host == "192.168.4.1":
                return {"ip": host, "model": "NANO RTK"}
            if host == "192.168.4.3":
                return {"ip": host, "fw_version": "1.0.0"}
            return None

        mock_reachable.side_effect = fake_reachable
        mock_probe_host.side_effect = fake_probe
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = nano_rtk_api.discover_devices("192.168.4.0/29", "/system/info", 0.2, 4, False)

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            [{"ip": "192.168.4.1", "model": "NANO RTK"}, {"fw_version": "1.0.0", "ip": "192.168.4.3"}],
        )
        self.assertEqual(mock_probe_host.call_count, 2)

    @mock.patch("nano_rtk_api.discover_devices_in_subnet")
    @mock.patch("nano_rtk_api.infer_local_subnets")
    def test_discover_local_devices_merges_multiple_subnets(
        self,
        mock_infer_local_subnets: mock.Mock,
        mock_discover_devices_in_subnet: mock.Mock,
    ) -> None:
        mock_infer_local_subnets.return_value = ["192.168.4.0/24", "10.10.20.0/24"]

        def fake_discover(subnet: str, path: str, timeout: float, workers: int):
            if subnet == "192.168.4.0/24":
                return [{"ip": "192.168.4.10", "model": "NANO RTK"}]
            return [{"ip": "10.10.20.15", "fw_version": "1.0.0"}]

        mock_discover_devices_in_subnet.side_effect = fake_discover
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = nano_rtk_api.discover_local_devices("/system/info", 0.2, 4, False)

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            [{"fw_version": "1.0.0", "ip": "10.10.20.15"}, {"ip": "192.168.4.10", "model": "NANO RTK"}],
        )

    @mock.patch("nano_rtk_api.infer_local_subnets")
    def test_discover_local_devices_errors_when_no_subnet_inferred(self, mock_infer_local_subnets: mock.Mock) -> None:
        mock_infer_local_subnets.return_value = []
        with self.assertRaises(SystemExit) as ctx:
            nano_rtk_api.discover_local_devices("/system/info", 0.2, 4, False)
        self.assertIn("Could not infer a local IPv4 subnet", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

import stat
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.requests import Request

from backend import fleet_auth
from backend.main import FLEET_TOKEN, app


def fake_request(host: str, headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/generate",
        "raw_path": b"/api/generate",
        "query_string": b"",
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
        "client": (host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


def test_job_origin_uses_valid_fleet_token_before_loopback(monkeypatch):
    monkeypatch.setattr(fleet_auth, "load_token", lambda: "fleet-secret")
    request = fake_request("127.0.0.1", {"x-studio-token": "fleet-secret"})
    assert fleet_auth.classify_job_origin(request) == ("api", None)


def test_job_origin_marks_uncredentialed_loopback_as_local_ui(monkeypatch):
    monkeypatch.setattr(fleet_auth, "load_token", lambda: "fleet-secret")
    request = fake_request("127.0.0.1", {"x-kh-origin-device": "spoofed"})
    assert fleet_auth.classify_job_origin(request) == ("local_ui", None)


def test_job_origin_never_trusts_caller_device_headers(monkeypatch):
    monkeypatch.setattr(fleet_auth, "load_token", lambda: "fleet-secret")
    request = fake_request("100.64.0.8", {
        "x-studio-token": "fleet-secret", "x-kh-origin-device": "spoofed",
    })
    assert fleet_auth.classify_job_origin(request) == ("api", None)


class FleetAuthTests(unittest.TestCase):
    def test_public_and_protected_routes(self):
        client = TestClient(app)
        self.assertEqual(client.get("/api/health").status_code, 200)
        self.assertEqual(client.get("/api/capabilities").status_code, 200)
        self.assertEqual(client.get("/api/catalog").status_code, 401)
        authed = TestClient(app, headers={"X-Studio-Token": FLEET_TOKEN})
        self.assertEqual(authed.get("/api/catalog").status_code, 200)

    def test_cross_origin_write_rejected_even_with_token(self):
        client = TestClient(app, headers={"X-Studio-Token": FLEET_TOKEN})
        response = client.delete("/api/downloads", headers={"Origin": "https://evil.example"})
        self.assertEqual(response.status_code, 403)

    def test_loopback_and_private_shared_token(self):
        request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
        self.assertTrue(fleet_auth.is_loopback(request))
        source = fleet_auth.HUB_TOKEN_FILE if fleet_auth.HUB_TOKEN_FILE.exists() else fleet_auth.SHARED_TOKEN_FILE
        self.assertEqual(stat.S_IMODE(source.stat().st_mode), 0o600)

    def test_saved_fleet_token_takes_effect_without_restart(self):
        with patch.object(fleet_auth, "load_token", return_value="rotated-token"):
            accepted = TestClient(app, headers={"X-Studio-Token": "rotated-token"})
            stale = TestClient(app, headers={"X-Studio-Token": FLEET_TOKEN})
            self.assertEqual(accepted.get("/api/catalog").status_code, 200)
            self.assertEqual(stale.get("/api/catalog").status_code, 401)


if __name__ == "__main__":
    unittest.main()

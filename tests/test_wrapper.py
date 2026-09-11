"""Fast contract checks with stub models. No upstream source, model download or network."""
import importlib
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import httpx
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
scratch = tempfile.TemporaryDirectory(prefix="miyohub-captcha-unit-")
models = SimpleNamespace(**{name: object() for name in ("session", "session_dfine", "session_yolo11n", "session_dino3", "session_dino_cf")})
with patch.dict(sys.modules, {
    "crack": SimpleNamespace(Crack=Mock()),
    "crop_image": SimpleNamespace(crop_image_v3=Mock(), validate_path=scratch.name),
    "predict": models,
}):
    service = importlib.import_module("service")


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(service.app)
        self.params = {"gt": "a" * 32, "challenge": "b" * 32}
        self.network = patch.object(httpx.HTTPTransport, "handle_request", side_effect=AssertionError("real network is forbidden"))
        # ASGI TestClient uses an in-process transport; socket transports stay blocked.
        self.network.start()
        self.token = patch.object(service, "api_token", "")
        self.token.start()

    def tearDown(self):
        self.token.stop()
        self.network.stop()
        self.client.close()

    def test_health_requires_all_models_and_reports_version(self):
        result = self.client.get("/healthz")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["version"], service.version)
        with patch.object(models, "session", None):
            self.assertEqual(self.client.get("/healthz").status_code, 503)

    def test_invalid_requests_and_unauthorized_calls_do_not_solve(self):
        with patch.object(service, "solve_challenge") as solve:
            self.assertEqual(self.client.get("/pass_nine", params={"gt": "invalid", "challenge": "invalid"}).status_code, 422)
            with patch.object(service, "api_token", "unit-test-secret"):
                self.assertEqual(self.client.get("/pass_nine", params=self.params).status_code, 401)
            solve.assert_not_called()

    def test_alias_authorization_and_protocol(self):
        expected = {"data": {"result": "success", "validate": "unit-test-validation"}}
        with patch.object(service, "api_token", "unit-test-secret"), patch.object(service, "solve_challenge", return_value=expected) as solve:
            result = self.client.get("/pass_uni", params={**self.params, "use_v3_model": "false"}, headers={"Authorization": "Bearer unit-test-secret"})
            self.assertEqual(result.json(), expected)
            solve.assert_called_once_with(self.params["gt"], self.params["challenge"], False)

    def test_failure_is_redacted_and_scratch_is_removed(self):
        image = Path(scratch.name) / "synthetic.png"
        image.write_bytes(b"synthetic")
        with patch.object(service, "solve_challenge", side_effect=ValueError("do-not-expose-challenge")):
            result = self.client.get("/pass_nine", params=self.params)
        self.assertEqual(result.status_code, 502)
        self.assertNotIn("do-not-expose", result.text)
        self.assertFalse(image.exists())
        self.assertFalse(service.lock.locked())

    def test_busy_worker_does_not_start_more_work(self):
        busy = Mock(spec=threading.Lock())
        busy.acquire.return_value = False
        with patch.object(service, "lock", busy), patch.object(service, "solve_challenge") as solve:
            result = self.client.get("/pass_nine", params=self.params)
        self.assertEqual(result.status_code, 429)
        solve.assert_not_called()
        busy.release.assert_not_called()

    def test_deadline_and_host_allowlist_precede_network(self):
        with service.DeadlineClient(time.monotonic() - 1) as client:
            with self.assertRaises(TimeoutError):
                client.get("https://api.geevisit.com/get.php")
        with service.DeadlineClient(time.monotonic() + 50) as client:
            for target in ["http://api.geetest.com", "https://api.geetest.com.evil.invalid", "http://127.0.0.1", "https://example.invalid"]:
                with self.assertRaises(ValueError):
                    client.get(target)


if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        scratch.cleanup()

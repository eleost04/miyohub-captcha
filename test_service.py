"""Offline API and real CPU inference tests. Run with Docker --network none."""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

import service

GT = "a" * 32
CHALLENGE = "b" * 32


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(service.app)

    def tearDown(self):
        self.client.close()

    def test_health_and_all_cpu_models(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], service.version)
        self.assertEqual(len(response.json()["models"]), 5)
        for name in service.model_names:
            self.assertEqual(getattr(service.predict, name).get_providers(), ["CPUExecutionProvider"])

    def test_partial_models_are_not_healthy(self):
        with patch.object(service.predict, "session_dino_cf", None):
            self.assertEqual(self.client.get("/healthz").status_code, 503)

    def test_invalid_inputs_never_call_upstream(self):
        with patch.object(service, "solve_challenge") as solve:
            response = self.client.get("/pass_nine", params={"gt": "example_gt", "challenge": "example_challenge"})
            self.assertEqual(response.status_code, 422)
            solve.assert_not_called()

    def test_contract_model_flag_and_authorization(self):
        expected = {"data": {"result": "success", "validate": "offline-test", "challenge": CHALLENGE}}
        with patch.object(service, "api_token", "private"), patch.object(service, "solve_challenge", return_value=expected) as solve:
            params = {"gt": GT, "challenge": CHALLENGE, "use_v3_model": "false"}
            self.assertEqual(self.client.get("/pass_nine", params=params).status_code, 401)
            solve.assert_not_called()
            response = self.client.get("/pass_uni", params=params, headers={"Authorization": "Bearer private"})
            self.assertEqual(response.json(), expected)
            solve.assert_called_once_with(GT, CHALLENGE, False)

    def test_errors_are_redacted_and_scratch_is_cleaned(self):
        scratch = Path(service.validate_path) / "synthetic-test.jpg"
        scratch.write_bytes(b"temporary")
        with patch.object(service, "solve_challenge", side_effect=ValueError("secret-challenge")):
            response = self.client.get("/pass_nine", params={"gt": GT, "challenge": CHALLENGE})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret-challenge", response.text)
        self.assertFalse(scratch.exists())
        self.assertFalse(service.lock.locked())

    def test_requests_cannot_mix_images(self):
        active = 0
        def solve(*args):
            nonlocal active
            active += 1
            self.assertEqual(active, 1)
            time.sleep(0.025)
            active -= 1
            return {"data": {"result": "fail"}}
        with patch.object(service, "solve_challenge", side_effect=solve), ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.client.get, "/pass_nine", params={"gt": GT, "challenge": CHALLENGE}) for _ in range(2)]
            self.assertTrue(all(future.result().status_code == 200 for future in futures))

    def test_real_offline_model_inference(self):
        picture = Image.new("RGB", (344, 384), (120, 140, 100))
        raw = BytesIO()
        picture.save(raw, format="PNG")
        service.crop_image_v3(raw.getvalue())
        points = service.predict.predict_onnx_pdl(service.validate_path)
        self.assertTrue(points)
        self.assertTrue(all(1 <= row <= 3 and 1 <= col <= 3 for row, col in points))
        self.assertIsInstance(service.predict.predict_onnx_dfine(picture), list)
        crops = service.predict.predict_onnx_yolo(picture)
        self.assertIn("top", crops)
        self.assertIn("bottom", crops)
        features = service.predict.predict_onnx_dino(picture)
        similarity = service.predict.predict_dino_classify(features, features)
        self.assertAlmostEqual(similarity, 1.0, places=4)


if __name__ == "__main__":
    unittest.main()

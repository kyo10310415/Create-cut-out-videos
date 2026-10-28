"""Offline dependency smoke/regression tests; no credentials or API calls required.

Run: python -m unittest discover -s tests -v
Install requirements-render.txt and Pillow==13.0.0 for this focused suite.
"""
import io
import unittest
from dotenv import dotenv_values
from flask import Flask, session
import orjson
from PIL import Image
import requests
from tqdm import tqdm


class SecurityDependencyTests(unittest.TestCase):
    def test_session_membership_varies_on_cookie(self):
        app = Flask(__name__)
        app.secret_key = "offline-test-only"

        @app.get("/")
        def index():
            return {"authenticated": "user" in session}

        response = app.test_client().get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Cookie", response.vary)

    def test_orjson_rejects_deeply_nested_serialization(self):
        value = []
        for _ in range(1000):
            value = [value]
        with self.assertRaises(TypeError):
            orjson.dumps(value)

    def test_image_round_trip(self):
        output = io.BytesIO()
        Image.new("RGB", (8, 8), "red").save(output, format="PNG")
        output.seek(0)
        with Image.open(output) as image:
            image.load()
            self.assertEqual(image.getpixel((0, 0)), (255, 0, 0))

    def test_dotenv_parsing(self):
        self.assertEqual(dotenv_values(stream=io.StringIO("TEST_VALUE=ok\n")), {"TEST_VALUE": "ok"})

    def test_requests_preparation(self):
        request = requests.Request("GET", "https://example.invalid/", params={"q": "日本語"}).prepare()
        self.assertIn("q=", request.url)

    def test_progress_iterator(self):
        self.assertEqual(list(tqdm(range(3), disable=True)), [0, 1, 2])


if __name__ == "__main__":
    unittest.main()

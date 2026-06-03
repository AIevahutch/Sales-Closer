import json
import os
import unittest
from unittest.mock import patch

from closer_app.llm import chat_completion


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")


class LlmTests(unittest.TestCase):
    def test_chat_completion_uses_gpt55_and_standard_service_tier(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return _FakeResponse()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
            os.environ.pop("OPENAI_MODEL", None)
            os.environ.pop("OPENAI_SERVICE_TIER", None)
            with patch("urllib.request.urlopen", fake_urlopen):
                result = chat_completion("system", "user")

        self.assertEqual(result, "ok")
        self.assertEqual(captured["payload"]["model"], "gpt-5.5")
        self.assertEqual(captured["payload"]["service_tier"], "default")
        self.assertEqual(captured["timeout"], 30)

    def test_invalid_service_tier_falls_back_to_default(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return _FakeResponse()

        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "test-key", "OPENAI_SERVICE_TIER": "mystery"},
            clear=False,
        ):
            with patch("urllib.request.urlopen", fake_urlopen):
                chat_completion("system", "user")

        self.assertEqual(captured["payload"]["service_tier"], "default")


if __name__ == "__main__":
    unittest.main()

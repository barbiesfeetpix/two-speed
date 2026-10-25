import json
import unittest

from two_speed.agent import NANO, SUPER, review
from two_speed.client import ModelError, chat


def fake_complete(replies):
    calls = []

    def complete(model, messages):
        calls.append(model)
        text = replies[model]
        return {"text": text, "model": model, "usage": {"prompt_tokens": 10, "completion_tokens": 20}}

    complete.calls = calls
    return complete


class AgentTests(unittest.TestCase):
    def test_style_nit_stays_on_nano(self):
        complete = fake_complete({
            NANO: json.dumps({"issues": [{"severity": "low", "why": "name is vague"}], "needs_super": False, "revision": "def price_after(price, percent):\n    return price - percent"}),
        })
        result = review("def discount(price, percent):\n    return price - percent", complete)
        self.assertFalse(result["routed_to_super"])
        self.assertIsNone(result["super"])
        self.assertEqual(complete.calls, [NANO])

    def test_high_issue_calls_super_once(self):
        complete = fake_complete({
            NANO: "```json\n" + json.dumps({"issues": [{"severity": "high", "why": "percent is subtracted as a raw number"}], "needs_super": True, "revision": "still wrong"}) + "\n```",
            SUPER: json.dumps({"issues": [{"severity": "high", "why": "percent must scale the price"}], "revision": "def discount(price, percent):\n    return price * (1 - percent)"}),
        })
        result = review("def discount(price, percent):\n    return price - percent", complete)
        self.assertEqual(complete.calls, [NANO, SUPER])
        self.assertIn("price *", result["final_revision"])
        self.assertNotIn("Bearer", json.dumps(result))

    def test_bad_json_still_escalates(self):
        complete = fake_complete({NANO: "not json", SUPER: json.dumps({"issues": [], "revision": "def ok():\n    return 1"})})
        result = review("def ok():\n    return 1", complete)
        self.assertTrue(result["routed_to_super"])
        self.assertIn("JSON", result["nano"]["error"])

    def test_empty_snippet(self):
        with self.assertRaises(ValueError):
            review("  ", fake_complete({}))


class ClientTests(unittest.TestCase):
    def test_reads_openai_shape_and_hides_key(self):
        seen = {}

        def transport(url, headers, raw):
            seen["url"] = url
            seen["auth"] = headers["Authorization"]
            seen["body"] = json.loads(raw)
            return 200, {"model": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", "choices": [{"message": {"content": "hi"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}}

        reply = chat("secret-key", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", [{"role": "user", "content": "hi"}], transport=transport)
        self.assertEqual(reply["text"], "hi")
        self.assertTrue(seen["url"].endswith("/chat/completions"))
        self.assertEqual(seen["auth"], "Bearer secret-key")
        self.assertNotIn("secret-key", json.dumps(reply))

    def test_missing_key(self):
        with self.assertRaises(ModelError) as caught:
            chat("  ", "m", [])
        self.assertEqual(caught.exception.kind, "config")


if __name__ == "__main__":
    unittest.main()

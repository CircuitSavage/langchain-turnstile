"""Unit tests for langchain-turnstile.

These mock Peak's HTTP response, so they need neither a live Peak key nor
a real browser or LLM. Run with::

    python -m pytest tests/ -v
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_turnstile import PeakError, PeakTurnstileTool  # noqa: E402
from langchain_turnstile.inject import build_injection_script  # noqa: E402
from langchain_turnstile.peak import PeakClient  # noqa: E402

SAMPLE_SITEKEY = "1x00000000000000000000AA"
SAMPLE_URL = "https://protected.example/login"
TEST_TOKEN = "XXXX.TEST"


def _peak_success(*_args, **_kwargs):
    return {"success": True, "data": {"token": TEST_TOKEN}, "cost": 0.0009}


class PeakTurnstileToolTests(unittest.TestCase):
    def test_run_returns_token(self):
        tool = PeakTurnstileTool(api_key="pk_test_key")
        with mock.patch.object(PeakClient, "_post", side_effect=_peak_success) as post:
            result = tool.run({"url": SAMPLE_URL, "sitekey": SAMPLE_SITEKEY})
        self.assertEqual(result, TEST_TOKEN)
        payload = post.call_args.args[0]
        # No proxy given -> defaults to the proxyless task, per the live
        # API contract (proxied task 400s without a proxy field).
        self.assertEqual(payload["task_type"], "turnstiletaskproxyless")
        self.assertNotIn("proxy", payload)

    def test_run_with_proxy_uses_proxied_task(self):
        tool = PeakTurnstileTool(api_key="pk_test_key")
        proxy = "http://user:pass@1.2.3.4:8080"
        with mock.patch.object(PeakClient, "_post", side_effect=_peak_success) as post:
            tool.run({"url": SAMPLE_URL, "sitekey": SAMPLE_SITEKEY, "proxy": proxy})
        payload = post.call_args.args[0]
        self.assertEqual(payload["task_type"], "turnstiletask")
        self.assertEqual(payload["proxy"], proxy)

    def test_api_key_from_env(self):
        tool = PeakTurnstileTool()
        with mock.patch.dict(os.environ, {"PEAK_API_KEY": "pk_env_key"}):
            with mock.patch.object(PeakClient, "_post", side_effect=_peak_success):
                result = tool.run({"url": SAMPLE_URL, "sitekey": SAMPLE_SITEKEY})
        self.assertEqual(result, TEST_TOKEN)

    def test_failure_returned_not_raised(self):
        # A tool-level error comes back as a string the agent can read and
        # react to, rather than crashing the agent's run loop.
        tool = PeakTurnstileTool(api_key="pk_test_key")
        fail = {"success": False, "error": "insufficient balance"}
        with mock.patch.object(PeakClient, "_post", return_value=fail):
            result = tool.run({"url": SAMPLE_URL, "sitekey": SAMPLE_SITEKEY})
        self.assertIn("insufficient balance", result)

    def test_async_fallback_threads_sync_run(self):
        import asyncio

        tool = PeakTurnstileTool(api_key="pk_test_key")
        with mock.patch.object(PeakClient, "_post", side_effect=_peak_success):
            result = asyncio.run(
                tool.arun({"url": SAMPLE_URL, "sitekey": SAMPLE_SITEKEY})
            )
        self.assertEqual(result, TEST_TOKEN)


class InjectionScriptTests(unittest.TestCase):
    def test_token_is_json_escaped_not_python_repr(self):
        # A token containing a character that Python repr and JSON string
        # syntax would escape differently should still produce valid JS.
        script = build_injection_script('weird"token')
        self.assertIn('"weird\\"token"', script)

    def test_script_references_callback_and_field(self):
        script = build_injection_script(TEST_TOKEN)
        self.assertIn("cf-turnstile-response", script)
        self.assertIn("data-callback", script)
        self.assertIn(TEST_TOKEN, script)


class PeakErrorTests(unittest.TestCase):
    def test_no_api_key_returns_error_string(self):
        # _run catches PeakError (including "no key configured") and hands
        # the agent a readable string instead of raising, same as any
        # other solve failure.
        tool = PeakTurnstileTool()
        with mock.patch.dict(os.environ, {}, clear=True):
            result = tool.run({"url": SAMPLE_URL, "sitekey": SAMPLE_SITEKEY})
        self.assertIn("ERROR", result)
        self.assertIn("No Peak API key", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)

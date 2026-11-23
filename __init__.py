"""0G Private Computer provider profile: every chat model 0G's router serves, sent as OpenAI chat
completions to https://router-api.0g.ai/v1 with an OG_API_KEY from https://pc.0g.ai."""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from typing import Any

from hermes_cli.version_info import hermes_user_agent
from providers import register_provider
from providers.base import LazyHeaders, ProviderProfile

BASE_URL = "https://router-api.0g.ai/v1"
# The catalog is public (no key). One fetch per process, on the first request that needs it; a
# failed fetch is retried after this long, so an unreachable router costs one short wait per window.
_CATALOG_TIMEOUT = 3.0
_RETRY_AFTER = 600.0
# Levels sent as reasoning_effort while the catalog has not measured a model's own levels; Hermes's
# weaker and stronger ends clamp onto them, as pi-0g does.
_EFFORTS = {"minimal": "low", "low": "low", "medium": "medium", "high": "high", "xhigh": "high", "max": "high"}

# Hermes's canonical attribution set: 0G's router files these requests under client "hermes".
_HEADERS = LazyHeaders({
    "HTTP-Referer": "https://hermes-agent.nousresearch.com",
    "X-Title": "Hermes Agent",
    "User-Agent": lambda: hermes_user_agent("HermesAgent"),
})


class _Catalog:
    """The parts of GET {base_url}/models this profile reads, keyed by model id."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._base_url = ""
        self._models: dict[str, dict[str, Any]] = {}
        self._failed_at = 0.0

    def load(self, base_url: str) -> dict[str, dict[str, Any]]:
        base_url = (base_url or BASE_URL).rstrip("/")
        with self._lock:
            if self._models and self._base_url == base_url:
                return self._models
            if self._base_url == base_url and time.monotonic() - self._failed_at < _RETRY_AFTER:
                return {}
            self._base_url = base_url
            try:
                self._models = _fetch(base_url)
                self._failed_at = 0.0
            except Exception:
                self._models = {}
                self._failed_at = time.monotonic()
            return self._models

    def cached(self) -> dict[str, dict[str, Any]]:
        return self._models


def _fetch(base_url: str) -> dict[str, dict[str, Any]]:
    req = urllib.request.Request(f"{base_url}/models", headers={"Accept": "application/json", **dict(_HEADERS.items())})
    with urllib.request.urlopen(req, timeout=_CATALOG_TIMEOUT) as resp:
        items = json.loads(resp.read().decode()).get("data") or []
    out = {}
    for m in items:
        if not isinstance(m, dict) or not isinstance(m.get("id"), str) or m.get("type") != "chatbot":
            continue
        if "openai" not in (m.get("supported_formats") or ["openai"]):
            continue
        out[m["id"]] = m
    return out


_catalog = _Catalog()


class ZeroGProfile(ProviderProfile):
    """Model list, context lengths and reasoning controls from 0G's public catalog."""

    def fetch_models(self, *, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0):
        models = _catalog.load(base_url or self.base_url)
        return sorted(models) or None

    def get_model_context_length(self, model: str) -> int | None:
        length = _catalog.cached().get(model, {}).get("context_length")
        return length if isinstance(length, int) and length > 0 else None

    def build_api_kwargs_extras(
        self, *, reasoning_config: dict | None = None, model: str | None = None, base_url: str | None = None,
        **context: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        # Only models that list reasoning_effort get it: some upstreams (gpt-4.1) reject it with a 400.
        # Turning thinking off sends nothing, so the model thinks as it does by default: the catalog
        # does not yet say which models reasoning_effort "none" really turns off.
        if not isinstance(reasoning_config, dict) or reasoning_config.get("enabled") is False:
            return {}, {}
        effort = _EFFORTS.get(str(reasoning_config.get("effort") or "").lower())
        entry = _catalog.load(base_url or self.base_url).get(model or "")
        if not effort or not entry or "reasoning_effort" not in (entry.get("supported_parameters") or []):
            return {}, {}
        return {}, {"reasoning_effort": effort}


zerog = ZeroGProfile(
    name="0g",
    aliases=("0g-pc", "zerog"),
    display_name="0G Private Computer",
    description="0G Private Computer — one API key for open and frontier models, with TEE-verified options",
    signup_url="https://pc.0g.ai",
    env_vars=("OG_API_KEY", "OG_BASE_URL"),
    base_url=BASE_URL,
    auth_type="api_key",
    default_headers=_HEADERS,
    default_aux_model="glm-5.3-flash",
    # Picker safety net when the live catalog cannot be fetched: tool-calling chat models.
    fallback_models=("glm-5.3", "glm-5.3-flash", "deepseek-v4-pro", "kimi-k2.6", "0gm-1.0-35b-a3b"),
)

register_provider(zerog)

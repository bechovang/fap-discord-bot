"""
Runtime configuration overrides stored in data/.
"""
import json
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

CONFIG_FILE = Path("data/runtime_config.json")


def _load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_config(config: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_proxy_url() -> Optional[str]:
    config = _load_config()
    proxy_url = config.get("proxy_url")
    return proxy_url or None


def set_proxy_url(proxy_url: str):
    config = _load_config()
    config["proxy_url"] = proxy_url
    _save_config(config)


def clear_proxy_url():
    config = _load_config()
    config.pop("proxy_url", None)
    _save_config(config)


def format_proxy_summary(proxy_url: Optional[str]) -> str:
    if not proxy_url:
        return "Not configured"

    parsed = urlparse(proxy_url)
    host = parsed.hostname or "unknown"
    port = parsed.port or "?"
    username = parsed.username or ""
    masked_user = username[:4] + "***" if username else "none"
    return f"{host}:{port} | user: {masked_user} | scheme: {parsed.scheme}"

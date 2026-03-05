from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

try:
    import streamlit as st

    _HAS_STREAMLIT = True
except Exception:
    # Streamlit is only available when running the web app.
    _HAS_STREAMLIT = False


@lru_cache(maxsize=None)
def _from_streamlit(name: str) -> Optional[str]:
    """
    Read a value from Streamlit secrets if available.

    This works both on Streamlit Cloud (via the Secrets UI) and locally
    when a .streamlit/secrets.toml file is present and the app is run
    with `streamlit run`.
    """
    if not _HAS_STREAMLIT:
        return None

    try:
        value = st.secrets[name]  # type: ignore[index]
    except Exception:
        return None

    if value is None:
        return None

    return str(value)


def _from_env(name: str) -> Optional[str]:
    """Read a value from standard environment variables."""
    return os.getenv(name)


def get_required_secret(name: str) -> str:
    """
    Retrieve a required configuration value.

    Order of precedence:
    1. Streamlit secrets (secrets.toml / Secrets UI)
    2. OS environment variables (including values loaded from .env)
    """
    value = _from_streamlit(name) or _from_env(name)
    if value is None or value == "":
        raise RuntimeError(f"{name} is not set in Streamlit secrets or environment variables.")
    return value


def get_setting(name: str, default: Optional[str] = None) -> str:
    """
    Retrieve an optional configuration value with a default.

    If the setting is not present in Streamlit secrets or the environment,
    the provided default is returned.
    """
    value = _from_streamlit(name) or _from_env(name)
    if value is None or value == "":
        return default
    return value


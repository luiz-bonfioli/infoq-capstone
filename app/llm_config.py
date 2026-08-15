"""Shared helper for detecting whether real LangChain LLM/embeddings
credentials are configured.

Node implementations use this to decide between calling the real model and
falling back to a deterministic stub - keeping the graph runnable in
environments without API keys (e.g. CI, local skeleton testing) while
showing the production integration pattern.
"""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

# Load variables from a local .env file (if present) into the process
# environment on first import, without overriding any variables already
# set externally (e.g. by the shell or a deployment platform).
load_dotenv(override=False)


def llm_configured() -> bool:
    """Whether an OpenAI API key is available for real LLM/embeddings calls."""
    return bool(os.environ.get("OPENAI_API_KEY"))


def ssl_verification_disabled() -> bool:
    """Whether outbound HTTPS calls to the LLM/embeddings API should skip TLS
    certificate verification.

    Opt-in via `OPENAI_SKIP_SSL_VERIFY=true` in `.env`. Intended as a
    workaround for corporate networks with SSL-inspecting proxies whose
    intermediate CA isn't trusted by Python's certificate store (e.g.
    `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`).
    Do NOT enable this in production - it disables protection against
    man-in-the-middle attacks.
    """
    return os.environ.get("OPENAI_SKIP_SSL_VERIFY", "").strip().lower() in {"1", "true", "yes"}


def build_http_client() -> httpx.Client | None:
    """Build a shared `httpx.Client` for LangChain OpenAI clients, honoring
    `ssl_verification_disabled()`. Returns None when verification should
    stay enabled, so callers can rely on the library's own default client.
    """
    if ssl_verification_disabled():
        return httpx.Client(verify=False)
    return None


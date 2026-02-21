"""
Sync and async AI query functions.

Usage (minimal):
    response = query_ai("What is 2+2?")

Usage (explicit provider/model):
    response = query_ai(
        "What is 2+2?",
        provider=AIProvider.ANTHROPIC,
        model="claude-sonnet-4-20250514",
        system="You are a math tutor.",
        temperature=0.3,
    )

Async variant:
    response = await query_ai_async("What is 2+2?")
"""

from __future__ import annotations

from typing import Optional

from .config import AIProvider, DEFAULT_PROVIDER, get_api_key, get_default_model


# ---------------------------------------------------------------------------
# Provider-specific dispatch (sync)
# ---------------------------------------------------------------------------


def _query_openai(
    prompt: str,
    model: str,
    api_key: str,
    system: Optional[str],
    temperature: float,
    max_tokens: int,
) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content


def _query_anthropic(
    prompt: str,
    model: str,
    api_key: str,
    system: Optional[str],
    temperature: float,
    max_tokens: int,
) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    kwargs: dict = dict(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    if system:
        kwargs["system"] = system

    resp = client.messages.create(**kwargs)
    return resp.content[0].text


def _query_google(
    prompt: str,
    model: str,
    api_key: str,
    system: Optional[str],
    temperature: float,
    max_tokens: int,
) -> str:
    import requests

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body: dict = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    resp = requests.post(url, params={"key": api_key}, json=body, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ---------------------------------------------------------------------------
# Provider-specific dispatch (async)
# ---------------------------------------------------------------------------


async def _query_openai_async(
    prompt: str,
    model: str,
    api_key: str,
    system: Optional[str],
    temperature: float,
    max_tokens: int,
) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content


async def _query_anthropic_async(
    prompt: str,
    model: str,
    api_key: str,
    system: Optional[str],
    temperature: float,
    max_tokens: int,
) -> str:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key)
    kwargs: dict = dict(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    if system:
        kwargs["system"] = system

    resp = await client.messages.create(**kwargs)
    return resp.content[0].text


async def _query_google_async(
    prompt: str,
    model: str,
    api_key: str,
    system: Optional[str],
    temperature: float,
    max_tokens: int,
) -> str:
    import httpx

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body: dict = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, params={"key": api_key}, json=body, timeout=120)
        resp.raise_for_status()
        data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ---------------------------------------------------------------------------
# Dispatch tables — extend these when adding a new provider
# ---------------------------------------------------------------------------

_PROVIDER_DISPATCH = {
    AIProvider.OPENAI: _query_openai,
    AIProvider.ANTHROPIC: _query_anthropic,
    AIProvider.GOOGLE: _query_google,
}

_PROVIDER_DISPATCH_ASYNC = {
    AIProvider.OPENAI: _query_openai_async,
    AIProvider.ANTHROPIC: _query_anthropic_async,
    AIProvider.GOOGLE: _query_google_async,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def query_ai(
    prompt: str,
    *,
    provider: AIProvider = DEFAULT_PROVIDER,
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    debug: bool = False,
) -> str:
    """Send *prompt* to an AI provider and return the text response (sync).

    Args:
        prompt:      The user message / question.
        provider:    Which AI backend to use (default: ``DEFAULT_PROVIDER``).
        model:       Model identifier; falls back to the provider's default.
        system:      Optional system prompt / instruction.
        temperature: Sampling temperature (0 = deterministic).
        max_tokens:  Response length cap.
        debug:       If True, print the prompt and response to terminal.

    Returns:
        The model's text reply.
    """
    if debug:
        print("\n" + "=" * 80)
        print("AI QUERY DEBUG - PROMPT")
        print("=" * 80)
        if system:
            print(f"SYSTEM: {system}\n")
        print(f"USER: {prompt}")
        print("=" * 80 + "\n")

    model = model or get_default_model(provider)
    api_key = get_api_key(provider)
    dispatch_fn = _PROVIDER_DISPATCH.get(provider)
    if dispatch_fn is None:
        raise ValueError(f"No sync dispatch registered for provider: {provider}")

    response = dispatch_fn(prompt, model, api_key, system, temperature, max_tokens)

    if debug:
        print("\n" + "=" * 80)
        print("AI QUERY DEBUG - RESPONSE")
        print("=" * 80)
        print(response)
        print("=" * 80 + "\n")

    return response


async def query_ai_async(
    prompt: str,
    *,
    provider: AIProvider = DEFAULT_PROVIDER,
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    debug: bool = False,
) -> str:
    """Send *prompt* to an AI provider and return the text response (async).

    Same interface as :func:`query_ai` but ``await``-able.
    """
    if debug:
        print("\n" + "=" * 80)
        print("AI QUERY DEBUG - PROMPT (ASYNC)")
        print("=" * 80)
        if system:
            print(f"SYSTEM: {system}\n")
        print(f"USER: {prompt}")
        print("=" * 80 + "\n")

    model = model or get_default_model(provider)
    api_key = get_api_key(provider)
    dispatch_fn = _PROVIDER_DISPATCH_ASYNC.get(provider)
    if dispatch_fn is None:
        raise ValueError(f"No async dispatch registered for provider: {provider}")

    response = await dispatch_fn(
        prompt, model, api_key, system, temperature, max_tokens
    )

    if debug:
        print("\n" + "=" * 80)
        print("AI QUERY DEBUG - RESPONSE (ASYNC)")
        print("=" * 80)
        print(response)
        print("=" * 80 + "\n")

    return response

#!/usr/bin/env python3
"""Example usage of the AI query module - sync and async."""

import sys
import os
import asyncio
import time

# Add src to path (parent directory of tests)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai import query_ai, query_ai_async, AIProvider


# Sync usage
print("=== Sync Call ===")
t0 = time.time()
response = query_ai(
    "In the game of standard catan, give me a list of facts you know about the game in terms of rules and strategies",
    provider=AIProvider.OPENAI,
    model="gpt-5-mini",
    temperature=1,
    service_tier="priority",
)
elapsed = time.time() - t0
print(response)
print(f"  ⏱ {elapsed:.2f}s")


# Async usage
async def test_async():
    print("\n=== Async Call ===")
    t0 = time.time()
    response = await query_ai_async(
        "What should I build first in Catan?",
        provider=AIProvider.OPENAI,
        model="gpt-5-mini",
        system="You are a Catan strategy expert. Be concise.",
        temperature=1,
        service_tier="priority",
    )
    elapsed = time.time() - t0
    print(response)
    print(f"  ⏱ {elapsed:.2f}s")


asyncio.run(test_async())

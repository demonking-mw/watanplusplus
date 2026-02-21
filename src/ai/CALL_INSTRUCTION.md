# AI Query Module

This module provides a unified interface for querying LLM providers (OpenAI, Anthropic, Google).

## Features

- **`query_ai`**: Synchronous call to the AI provider.
- **`query_ai_async`**: Asynchronous call to the AI provider.
- **`AIProvider`**: Enum for selecting the provider.

## Usage

### Synchronous Call

```python
from ai import query_ai, AIProvider

response = query_ai(
    "What is 17 + 25? Reply with just the number.",
    provider=AIProvider.OPENAI,
)
print(response)
```

### Asynchronous Call

```python
import asyncio
from ai import query_ai_async, AIProvider

async def main():
    response = await query_ai_async(
        "What should I build first in Catan?",
        provider=AIProvider.OPENAI,
        system="You are a Catan strategy expert. Be concise.",
    )
    print(response)

asyncio.run(main())
```

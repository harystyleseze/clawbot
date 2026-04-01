from __future__ import annotations

import httpx
from loguru import logger


class OpenAICompatibleClient:
    """Client for any OpenAI-compatible API (Groq, xAI Grok, Together, etc.)."""

    def __init__(self, api_key: str, base_url: str, model: str, name: str = "OpenAI") -> None:
        self.model = model
        self.name = name
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
        )

    async def chat(self, system: str, user_message: str, max_tokens: int = 300) -> str:
        response = await self._client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.2,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def close(self) -> None:
        await self._client.aclose()


class AnthropicClient:
    """Anthropic Claude API — different format from OpenAI."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url="https://api.anthropic.com", timeout=15.0,
        )

    async def chat(self, system: str, user_message: str, max_tokens: int = 300) -> str:
        response = await self._client.post(
            "/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]

    async def close(self) -> None:
        await self._client.aclose()


class ChainGPTClient:
    """ChainGPT — blockchain-specific queries only (sponsor integration)."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=15.0)

    async def chat(self, system: str, user_message: str, max_tokens: int = 300) -> str:
        response = await self._client.post(
            "https://api.chaingpt.org/chat/stream",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "general_assistant",
                "question": f"{system}\n\nUser: {user_message}",
                "chatHistory": "off",
            },
        )
        if response.status_code not in (200, 201):
            response.raise_for_status()
        return response.text.strip()

    async def close(self) -> None:
        await self._client.aclose()


class AIClient:
    """Multi-provider AI client with automatic fallback.

    Priority: Groq (fast, free) → xAI Grok → Anthropic Claude → Ollama (local)
    ChainGPT is separate — blockchain-only for sponsor integration.
    """

    def __init__(
        self,
        groq_api_key: str = "",
        grok_api_key: str = "",
        anthropic_api_key: str = "",
        libertai_api_key: str = "",
        ollama_url: str = "",
        ollama_model: str = "qwen2.5:1.5b",
        chaingpt_api_key: str = "",
    ) -> None:
        self._providers: list[tuple[str, object]] = []

        if groq_api_key:
            self._providers.append(("Groq", OpenAICompatibleClient(
                api_key=groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                model="llama-3.3-70b-versatile",
                name="Groq",
            )))

        if grok_api_key:
            self._providers.append(("Grok", OpenAICompatibleClient(
                api_key=grok_api_key,
                base_url="https://api.x.ai/v1",
                model="grok-4-1-fast-non-reasoning",
                name="Grok",
            )))

        if libertai_api_key:
            self._providers.append(("LibertAI", OpenAICompatibleClient(
                api_key=libertai_api_key,
                base_url="https://api.libertai.io/v1",
                model="hermes-3-8b-tee",
                name="LibertAI",
            )))

        if anthropic_api_key:
            self._providers.append(("Anthropic", AnthropicClient(anthropic_api_key)))

        if ollama_url:
            self._providers.append(("Ollama", OpenAICompatibleClient(
                api_key="ollama",
                base_url=f"{ollama_url}/v1",
                model=ollama_model,
                name="Ollama",
            )))

        if not self._providers:
            raise ValueError("No AI provider configured. Set GROQ_API_KEY in .env")

        self._active_provider: str = self._providers[0][0]

        self._chaingpt: ChainGPTClient | None = None
        if chaingpt_api_key:
            self._chaingpt = ChainGPTClient(chaingpt_api_key)

    async def chat(self, system: str, user_message: str, max_tokens: int = 300) -> str:
        last_error = None
        for name, client in self._providers:
            try:
                result = await client.chat(system, user_message, max_tokens)
                if self._active_provider != name:
                    logger.info(f"AI provider switched to {name}")
                    self._active_provider = name
                return result
            except Exception as e:
                logger.warning(f"AI provider {name} failed: {e}")
                last_error = e
                continue

        raise RuntimeError(f"All AI providers failed: {last_error}")

    async def blockchain_query(self, question: str) -> str | None:
        if not self._chaingpt:
            return None
        try:
            return await self._chaingpt.chat("You are a helpful blockchain assistant.", question)
        except Exception as e:
            logger.warning(f"ChainGPT query failed: {e}")
            return None

    @property
    def active_provider(self) -> str:
        return self._active_provider

    @property
    def has_chaingpt(self) -> bool:
        return self._chaingpt is not None

    async def close(self) -> None:
        for _, client in self._providers:
            await client.close()
        if self._chaingpt:
            await self._chaingpt.close()

import time
from dataclasses import dataclass
from openai import AsyncOpenAI
from openai import RateLimitError, APITimeoutError, APIConnectionError
from app.llm.prompt_builder import BuiltPrompt
from app.config import settings
from app.utils.logger import logger


@dataclass
class GPTResponse:
    content: str              # raw answer text from GPT
    prompt_tokens: int        # tokens used in prompt
    completion_tokens: int    # tokens used in completion
    total_tokens: int         # total tokens used
    model: str                # which model was used
    response_time_ms: int     # how long the API call took


class GPTClient:
    """
    Clean wrapper around OpenAI async client.

    Handles:
    - Async API calls
    - Automatic retry on rate limit and timeout (up to 3 attempts)
    - Token usage tracking for audit logs
    - Response time tracking
    - Clean error messages
    """

    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 2

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
        )
        logger.info(f"GPT client initialized — model: {settings.OPENAI_MODEL}")

    async def complete(self, prompt: BuiltPrompt) -> GPTResponse:
        """
        Main entry point.
        Sends prompt to GPT and returns structured response.
        Retries up to MAX_RETRIES times on transient errors.
        """
        attempt = 0
        last_error = None

        while attempt < self.MAX_RETRIES:
            try:
                return await self._call_api(prompt)

            except RateLimitError as e:
                last_error = e
                attempt += 1
                wait = self.RETRY_DELAY_SECONDS * (2 ** attempt)  # exponential backoff
                logger.warning(
                    f"OpenAI rate limit hit — "
                    f"attempt {attempt}/{self.MAX_RETRIES}, "
                    f"retrying in {wait}s"
                )
                time.sleep(wait)

            except APITimeoutError as e:
                last_error = e
                attempt += 1
                logger.warning(
                    f"OpenAI timeout — "
                    f"attempt {attempt}/{self.MAX_RETRIES}"
                )

            except APIConnectionError as e:
                last_error = e
                attempt += 1
                logger.error(f"OpenAI connection error: {e}")

            except Exception as e:
                logger.error(f"Unexpected GPT error: {e}")
                raise

        logger.error(f"GPT failed after {self.MAX_RETRIES} attempts: {last_error}")
        raise RuntimeError(
            f"GPT API unavailable after {self.MAX_RETRIES} attempts. "
            f"Please try again later."
        )

    async def _call_api(self, prompt: BuiltPrompt) -> GPTResponse:
        """Single API call — called by complete() with retry logic."""
        start_time = time.time()

        logger.info(
            f"Calling GPT — model: {settings.OPENAI_MODEL}, "
            f"max_tokens: {settings.OPENAI_MAX_TOKENS}"
        )

        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": prompt.system_message,
                },
                {
                    "role": "user",
                    "content": prompt.user_message,
                },
            ],
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=settings.OPENAI_TEMPERATURE,
        )

        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)

        content = response.choices[0].message.content or ""
        usage = response.usage

        logger.info(
            f"GPT response received — "
            f"{usage.total_tokens} tokens, "
            f"{response_time_ms}ms"
        )

        return GPTResponse(
            content=content,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            model=response.model,
            response_time_ms=response_time_ms,
        )

    async def complete_streaming(self, prompt: BuiltPrompt):
        """
        Streaming version — yields text chunks as they arrive.
        Use this for the chat UI so users see the answer being typed.

        Usage:
            async for chunk in gpt_client.complete_streaming(prompt):
                yield chunk
        """
        logger.info("GPT streaming call started")

        stream = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": prompt.system_message,
                },
                {
                    "role": "user",
                    "content": prompt.user_message,
                },
            ],
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=settings.OPENAI_TEMPERATURE,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
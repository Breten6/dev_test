import asyncio
import json
import os

from fastapi import HTTPException
from openai import APIError, APITimeoutError, AsyncOpenAI
from pydantic import BaseModel, ValidationError
from typing import TypeVar

T = TypeVar("T", bound=BaseModel)


async def parse_model(schema: type[T], data: object, instructions: str) -> T:
    model = os.getenv("OPENAI_MODEL")
    if not model or not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(503, "OpenAI is not configured. Check the backend environment.")

    try:
        async with asyncio.timeout(45):
            async with AsyncOpenAI(timeout=20, max_retries=1) as client:
                response = await client.responses.parse(
                    model=model,
                    instructions=instructions,
                    input=json.dumps(data),
                    text_format=schema,
                    store=False,
                )
    except (TimeoutError, APITimeoutError):
        raise HTTPException(504, "The OpenAI request timed out. Try again.") from None
    except (APIError, ValidationError, ValueError):
        raise HTTPException(503, "The OpenAI request failed. Check configuration or retry.") from None

    if response.status != "completed" or response.output_parsed is None:
        raise HTTPException(503, "OpenAI returned no usable response. Try again.")
    return response.output_parsed

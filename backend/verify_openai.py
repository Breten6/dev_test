"""Verify the configured Responses API connection from a local shell."""

import os

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI


def main() -> int:
    names = ("OPENAI_API_KEY", "OPENAI_MODEL")
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        print(f"Missing environment configuration: {', '.join(missing)}")
        return 1

    print("OpenAI environment variables are available.")
    try:
        with OpenAI(timeout=12.0, max_retries=0) as client:
            response = client.responses.create(
                model=os.environ["OPENAI_MODEL"],
                input="Reply with the single word OK.",
                max_output_tokens=128,
                store=False,
            )
    except APITimeoutError:
        print("OpenAI request timed out.")
        return 1
    except APIConnectionError:
        print("Unable to connect to OpenAI.")
        return 1
    except APIStatusError as error:
        print(f"OpenAI rejected the request (HTTP {error.status_code}).")
        return 1

    if response.status != "completed" or not response.output_text.strip():
        print("OpenAI did not return a completed text response.")
        return 1
    print("OpenAI Responses API check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

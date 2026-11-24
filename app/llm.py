"""LLM client factory.

The rest of the code talks to the LLM only through `get_chat_model()`. Because
`ChatOpenAI` speaks the OpenAI API format, switching between Ollama, vLLM and a
commercial API is a matter of changing environment variables, not code.

Usage:
    uv run python -m app.llm "Merhaba, kendini tanıt."
"""

import sys

from langchain_openai import ChatOpenAI

from app.config import Settings, get_settings


def get_chat_model(settings: Settings | None = None) -> ChatOpenAI:
    s = settings or get_settings()
    return ChatOpenAI(
        base_url=s.llm_base_url,
        model=s.llm_model,
        api_key=s.llm_api_key,
        temperature=s.llm_temperature,
        timeout=s.llm_timeout_s,
    )


def main() -> None:
    prompt = " ".join(sys.argv[1:]) or "Merhaba! Kendini tek bir cümleyle tanıtır mısın?"
    s = get_settings()
    print(f"[model={s.llm_model} base_url={s.llm_base_url}]")
    reply = get_chat_model(s).invoke(prompt)
    print(reply.content)


if __name__ == "__main__":
    main()

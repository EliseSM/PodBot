from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic


def get_llm(provider: str, temperature: float = 0.7) -> BaseChatModel:
    """
    Returns a LangChain-compatible chat model for the given provider.

    provider: "openai" | "anthropic"
    Reads API keys from environment variables automatically:
      - OPENAI_API_KEY for OpenAI
      - ANTHROPIC_API_KEY for Anthropic
    """
    if provider == "openai":
        return ChatOpenAI(
            model="gpt-4o",
            temperature=temperature,
            max_retries=2,
        )
    elif provider == "anthropic":
        return ChatAnthropic(
            model="claude-sonnet-4-6",
            temperature=temperature,
            max_tokens=4096,
            max_retries=2,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider!r}. Must be 'openai' or 'anthropic'.")

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.base import BaseLLMProvider
from langchain_core.language_models import BaseChatModel


def get_llm_provider() -> BaseLLMProvider:
    from config import LLM_PROVIDER

    provider = LLM_PROVIDER.lower()
    if provider == "groq":
        from llm.groq_provider import GroqProvider
        return GroqProvider()
    elif provider == "openai":
        from llm.openai_provider import OpenAIProvider
        return OpenAIProvider()
    elif provider == "bedrock":
        from llm.bedrock_provider import BedrockProvider
        return BedrockProvider()
    elif provider == "ollama":
        from llm.ollama_provider import OllamaProvider
        return OllamaProvider()
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. Choose: groq, openai, bedrock, ollama"
        )


def get_llm_with_tools(tools: list) -> BaseChatModel:
    provider = get_llm_provider()
    llm = provider.get_llm()
    return llm

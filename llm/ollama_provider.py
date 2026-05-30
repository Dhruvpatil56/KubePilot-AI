import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.base import BaseLLMProvider
from langchain_core.language_models import BaseChatModel


class OllamaProvider(BaseLLMProvider):
    def get_llm(self) -> BaseChatModel:
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise ImportError("Run: pip install langchain-ollama")

        from config import OLLAMA_BASE_URL, OLLAMA_MODEL
        from agent.tools import TOOLS

        return ChatOllama(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL).bind_tools(TOOLS)

    def get_provider_name(self) -> str:
        return "ollama"

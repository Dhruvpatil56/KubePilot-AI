import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.base import BaseLLMProvider
from langchain_core.language_models import BaseChatModel


class OpenAIProvider(BaseLLMProvider):
    def get_llm(self) -> BaseChatModel:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("Run: pip install langchain-openai")

        from config import OPENAI_API_KEY, OPENAI_MODEL
        from agent.tools import TOOLS

        if not OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is not set. Add it to your .env file to use the OpenAI provider."
            )
        return ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL).bind_tools(TOOLS)

    def get_provider_name(self) -> str:
        return "openai"

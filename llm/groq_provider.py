import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.base import BaseLLMProvider
from langchain_core.language_models import BaseChatModel


class GroqProvider(BaseLLMProvider):
    def get_llm(self) -> BaseChatModel:
        from langchain_groq import ChatGroq
        from config import GROQ_API_KEY, GROQ_MODEL
        from agent.tools import TOOLS

        if not GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set. Add it to your .env file to use the Groq provider."
            )
        return ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL).bind_tools(TOOLS)

    def get_provider_name(self) -> str:
        return "groq"

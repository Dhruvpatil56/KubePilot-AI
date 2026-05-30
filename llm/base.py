from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel


class BaseLLMProvider(ABC):
    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        """Return a LangChain-compatible chat model bound with tools"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name string"""
        pass

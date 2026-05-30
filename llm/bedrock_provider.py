import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.base import BaseLLMProvider
from langchain_core.language_models import BaseChatModel


class BedrockProvider(BaseLLMProvider):
    def get_llm(self) -> BaseChatModel:
        try:
            from langchain_aws import ChatBedrock
        except ImportError:
            raise ImportError("Run: pip install langchain-aws")

        from config import BEDROCK_MODEL_ID, BEDROCK_REGION
        from agent.tools import TOOLS

        # Bedrock uses IAM auth — boto3 default credential chain, no API key needed
        return ChatBedrock(model_id=BEDROCK_MODEL_ID, region_name=BEDROCK_REGION).bind_tools(TOOLS)

    def get_provider_name(self) -> str:
        return "bedrock"

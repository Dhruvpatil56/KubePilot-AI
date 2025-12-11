import os
from dotenv import load_dotenv

# Load .env for local development. In Kubernetes, env vars override this.
load_dotenv()


class Config:
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Kubernetes Configuration
    K8S_NAMESPACE = os.getenv("K8S_NAMESPACE", "sre-demo")

    # Slack Configuration (optional, not wired yet)
    SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

    # Healing Agent Configuration
    ENABLE_AUTO_REMEDIATION = os.getenv("ENABLE_AUTO_REMEDIATION", "true").lower() == "true"
    DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

    # Allowed Actions
    ALLOWED_ACTIONS = [
        "restart_pod",
        "scale_up",
        "scale_down",
        "rollback",
        "no_action",
    ]

    # Confidence Threshold (LLM must be this confident to take action)
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))


config = Config()


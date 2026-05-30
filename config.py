from dotenv import load_dotenv
import os

load_dotenv()

# LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Kubernetes
K8S_NAMESPACE = os.getenv("K8S_NAMESPACE", "sre-demo")

# Agent
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
ENABLE_AUTO_REMEDIATION = os.getenv("ENABLE_AUTO_REMEDIATION", "true").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

# Allowed actions
ALLOWED_ACTIONS = ["restart_pod", "scale_up", "scale_down", "rollback", "no_action"]

# GitOps
GITOPS_MODE = os.getenv("GITOPS_MODE", "false").lower() == "true"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
ARGOCD_URL = os.getenv("ARGOCD_URL")
ARGOCD_TOKEN = os.getenv("ARGOCD_TOKEN")

# Slack
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")

# Pluggable LLM (Sprint 6)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-east-1")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.3")

# Feedback loop (Sprint 5)
ESCALATION_THRESHOLD = int(os.getenv("ESCALATION_THRESHOLD", "3"))

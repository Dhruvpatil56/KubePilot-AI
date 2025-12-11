import json
import logging
from typing import Dict, List
from openai import OpenAI
from config import config

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    def __init__(self):
        if not config.OPENAI_API_KEY:
            logger.warning("No OpenAI API key provided. LLM analysis will be disabled (fallback only).")
            self.client = None
        else:
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    def analyze_incident(
        self,
        alert_data: Dict,
        pod_details: Dict,
        logs: str,
        previous_logs: str,
        events: List[Dict],
    ) -> Dict:
        """Use LLM to analyze the incident and suggest remediation"""

        if not self.client:
            return self._fallback_analysis(alert_data, pod_details)

        logs = logs or ""
        previous_logs = previous_logs or ""

        try:
            context = self._build_context(alert_data, pod_details, logs, previous_logs, events)

            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": context},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            analysis = json.loads(raw)

            if not self._validate_analysis(analysis):
                logger.error("LLM returned invalid analysis, falling back to rules")
                return self._fallback_analysis(alert_data, pod_details)

            return analysis

        except Exception as e:
            logger.error(f"Error in LLM analysis: {e}")
            return self._fallback_analysis(alert_data, pod_details)

    def _get_system_prompt(self) -> str:
        return f"""You are an SRE AI assistant that analyzes Kubernetes incidents and suggests remediation actions.

Your task:
1. Analyze the incident data (alert, pod status, logs, events)
2. Determine the root cause
3. Suggest ONE remediation action from this list: {config.ALLOWED_ACTIONS}
4. Provide a confidence score (0.0 to 1.0)
5. Explain your reasoning

Response format (JSON):
{{
  "root_cause": "brief description of root cause",
  "recommended_action": "one of the allowed actions",
  "confidence": 0.85,
  "reasoning": "explanation of why this action",
  "risk_level": "low|medium|high",
  "additional_notes": "any other relevant info"
}}

Rules:
- Only recommend actions from the allowed list
- Be conservative: if unsure, recommend "no_action"
- Consider restart_pod for crashes
- Consider scale_up for OOMKilled or high resource usage
- Consider rollback for recent deployment issues
- Confidence must be honest (0.0-1.0)
"""

    def _build_context(self, alert_data, pod_details, logs, previous_logs, events) -> str:
        return f"""
Incident Analysis Request:

ALERT INFORMATION:
- Alert Name: {alert_data.get('labels', {}).get('alertname', 'Unknown')}
- Severity: {alert_data.get('labels', {}).get('severity', 'Unknown')}
- SLO Impact: {alert_data.get('labels', {}).get('slo_impact', 'Unknown')}
- Description: {alert_data.get('annotations', {}).get('description', 'No description')}

POD DETAILS:
{json.dumps(pod_details or {}, indent=2)}

RECENT LOGS (last 50 lines, truncated):
{logs[:2000]}

PREVIOUS LOGS (from crashed container, truncated):
{previous_logs[:2000]}

RECENT EVENTS:
{json.dumps(events[:5] if events else [], indent=2)}

Analyze this incident and provide remediation recommendation.
"""

    def _validate_analysis(self, analysis: Dict) -> bool:
        required_fields = ["root_cause", "recommended_action", "confidence", "reasoning"]

        if not all(field in analysis for field in required_fields):
            return False

        if analysis["recommended_action"] not in config.ALLOWED_ACTIONS:
            return False

        if not (0.0 <= float(analysis["confidence"]) <= 1.0):
            return False

        return True

    def _fallback_analysis(self, alert_data: Dict, pod_details: Dict) -> Dict:
        """Rule-based fallback when LLM is unavailable"""
        alert_name = alert_data.get("labels", {}).get("alertname", "")

        # Simple rule-based logic
        if "OOMKilled" in alert_name:
            return {
                "root_cause": "Container exceeded memory limits",
                "recommended_action": "scale_up",
                "confidence": 0.8,
                "reasoning": "OOMKilled typically requires more resources or replicas",
                "risk_level": "low",
                "additional_notes": "Fallback rule-based analysis (no LLM)",
            }

        elif "CrashLoop" in alert_name:
            restart_count = 0
            if pod_details and pod_details.get("container_statuses"):
                restart_count = pod_details["container_statuses"][0].get("restart_count", 0)

            if restart_count > 5:
                action = "no_action"
                reasoning = "Too many restarts, manual investigation safer"
            else:
                action = "restart_pod"
                reasoning = "Pod is crash looping, restart may help"

            return {
                "root_cause": "Application is repeatedly crashing",
                "recommended_action": action,
                "confidence": 0.7,
                "reasoning": reasoning,
                "risk_level": "medium",
                "additional_notes": "Fallback rule-based analysis (no LLM)",
            }

        else:
            return {
                "root_cause": "Unknown issue",
                "recommended_action": "no_action",
                "confidence": 0.5,
                "reasoning": "Insufficient information for safe automated remediation",
                "risk_level": "high",
                "additional_notes": "Fallback rule-based analysis (no LLM)",
            }


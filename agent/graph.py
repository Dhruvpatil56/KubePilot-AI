from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict, Annotated
import operator
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ALLOWED_ACTIONS
from agent.tools import TOOLS
from llm.factory import get_llm_provider

# ---------- State ----------
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    pod_name: str
    namespace: str
    alert_name: str
    rca: dict

# ---------- LLM ----------
provider = get_llm_provider()
print(f"LLM Provider: {provider.get_provider_name()}")
llm = provider.get_llm()

# ---------- System Prompt ----------
SYSTEM_PROMPT = """You are KubePilot AI, an expert Site Reliability Engineer agent.

When you receive an alert about a Kubernetes pod, you MUST:
1. Check pod status first
2. Get current pod logs
3. Get previous pod logs (most important for crashes)
4. Get pod events
5. Get deployment info
6. Based on ALL evidence, produce a final RCA

Always use the tools step by step. Never guess without checking.

After investigation, respond with this exact JSON:
{
  "root_cause": "clear explanation of what went wrong",
  "recommended_action": "one of: restart_pod, scale_up, scale_down, rollback, no_action",
  "confidence": 0.0 to 1.0,
  "reasoning": "what evidence led to this conclusion",
  "risk_level": "low, medium, or high"
}"""

# ---------- Agent Node ----------
def agent_node(state: AgentState):
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

# ---------- Should Continue ----------
def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# ---------- Build Graph ----------
tool_node = ToolNode(TOOLS)

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)

graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")

kubepilot_agent = graph.compile()

# ---------- Run Agent ----------
def investigate(pod_name: str, namespace: str, alert_name: str) -> dict:
    print(f"\n🔍 KubePilot AI investigating: {pod_name} | Alert: {alert_name}")

    initial_message = HumanMessage(
        content=f"""Alert received: {alert_name}
Pod: {pod_name}
Namespace: {namespace}

Please investigate this incident step by step using your tools and provide a full RCA."""
    )

    result = kubepilot_agent.invoke({
        "messages": [SystemMessage(content=SYSTEM_PROMPT), initial_message],
        "pod_name": pod_name,
        "namespace": namespace,
        "alert_name": alert_name,
        "rca": {}
    })

    # Extract final response
    final = result["messages"][-1].content
    print(f"\n✅ Investigation complete:\n{final}")
    return {"raw": final, "pod": pod_name, "alert": alert_name}

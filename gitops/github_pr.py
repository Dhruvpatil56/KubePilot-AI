import logging
import os
import sys
from datetime import datetime, timezone
from typing import Tuple

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GITHUB_TOKEN, GITHUB_REPO


# ── YAML fix generation ────────────────────────────────────────────────────────

def _apply_fix(content: str, action: str, timestamp: str) -> Tuple[str, str]:
    """Parse deployment.yaml, apply the fix, return (new_content, changes_description)."""
    import yaml

    docs = [d for d in yaml.safe_load_all(content) if d is not None]

    deployment = next((d for d in docs if isinstance(d, dict) and d.get("kind") == "Deployment"), None)

    if deployment is None:
        return content, "No Deployment document found in YAML — no changes applied."

    if action == "restart_pod":
        ann_key = "kubepilot.ai/restarted-at"
        (deployment
         .setdefault("spec", {})
         .setdefault("template", {})
         .setdefault("metadata", {})
         .setdefault("annotations", {})[ann_key]) = timestamp
        description = (
            f"Added annotation `{ann_key}: {timestamp}` to deployment spec template "
            "to trigger a rolling restart."
        )

    elif action == "rollback":
        ann_key = "kubepilot.ai/rollback"
        (deployment
         .setdefault("spec", {})
         .setdefault("template", {})
         .setdefault("metadata", {})
         .setdefault("annotations", {})[ann_key]) = timestamp
        description = (
            f"Added annotation `{ann_key}: {timestamp}` to trigger a rollback "
            "to the previous stable image."
        )

    elif action == "scale_up":
        spec = deployment.setdefault("spec", {})
        spec["replicas"] = min(spec.get("replicas", 1) + 1, 5)
        description = (
            f"Incremented `spec.replicas` to {spec['replicas']} "
            "(capped at 5) to distribute load."
        )

    elif action == "scale_down":
        spec = deployment.setdefault("spec", {})
        spec["replicas"] = max(spec.get("replicas", 1) - 1, 1)
        description = (
            f"Decremented `spec.replicas` to {spec['replicas']} "
            "(minimum 1) to reduce resource usage."
        )

    else:
        description = f"Applied `{action}` remediation action."

    new_content = yaml.dump_all(docs, default_flow_style=False, allow_unicode=True)
    return new_content, description


# ── PR body ───────────────────────────────────────────────────────────────────

def _build_pr_body(
    incident: dict,
    action: str,
    pod_name: str,
    namespace: str,
    timestamp: str,
    changes_desc: str,
) -> str:
    rca = incident.get("rca") or {}
    alert_name = incident.get("alert") or "Unknown Alert"
    confidence = rca.get("confidence")
    confidence_str = f"{round(confidence * 100)}%" if confidence is not None else "N/A"

    return f"""## \U0001f916 KubePilot AI — Automated Remediation PR

**Alert**: {alert_name}
**Pod**: {pod_name}
**Namespace**: {namespace}
**Timestamp**: {timestamp}

## Root Cause Analysis
{rca.get("root_cause", "N/A")}

## Recommended Action
**Action**: {action}
**Confidence**: {confidence_str}
**Risk Level**: {rca.get("risk_level", "N/A")}

## Reasoning
{rca.get("reasoning", "N/A")}

## Changes Made
{changes_desc}

---
*Generated automatically by KubePilot AI*
*Review carefully before merging*
"""


# ── Main function ─────────────────────────────────────────────────────────────

def create_remediation_pr(
    incident: dict, action: str, pod_name: str, namespace: str
) -> dict:
    """
    Open a GitHub PR with the YAML fix for the given incident action.
    Returns {"status": "created", "pr_url": ..., "pr_number": N, "branch": ...}
    or      {"status": "skipped", "reason": ...}
    or      {"status": "error",   "reason": ...}
    """
    if not GITHUB_TOKEN:
        logger.warning("GITHUB_TOKEN not set — skipping GitOps PR creation")
        return {"status": "skipped", "reason": "GITHUB_TOKEN not set"}
    if not GITHUB_REPO:
        logger.warning("GITHUB_REPO not set — skipping GitOps PR creation")
        return {"status": "skipped", "reason": "GITHUB_REPO not set"}

    try:
        from github import Github
    except ImportError:
        logger.warning("PyGithub not installed — skipping GitOps PR creation")
        return {"status": "skipped", "reason": "PyGithub not installed"}

    alert_name = incident.get("alert") or "unknown"
    now_utc = datetime.now(timezone.utc)
    timestamp_tag = now_utc.strftime("%Y%m%dT%H%M%SZ")
    timestamp_human = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    safe_alert = alert_name.lower().replace(" ", "-")
    branch_name = f"kubepilot/fix-{safe_alert}-{timestamp_tag}"
    file_path = "manifest_files/deployment.yaml"

    try:
        gh = Github(GITHUB_TOKEN)
        repo = gh.get_repo(GITHUB_REPO)

        # 1. Read current deployment.yaml from main
        contents = repo.get_contents(file_path, ref="main")
        current_content = contents.decoded_content.decode("utf-8")

        # 2. Generate fix
        new_content, changes_desc = _apply_fix(current_content, action, timestamp_human)

        # 3. Create branch from main HEAD
        main_branch = repo.get_branch("main")
        repo.create_git_ref(f"refs/heads/{branch_name}", main_branch.commit.sha)

        # 4. Commit updated YAML to new branch
        repo.update_file(
            path=file_path,
            message=f"[KubePilot AI] Fix {action} for {alert_name} on {pod_name}",
            content=new_content,
            sha=contents.sha,
            branch=branch_name,
        )

        # 5. Open PR
        pr_body = _build_pr_body(
            incident, action, pod_name, namespace, timestamp_human, changes_desc
        )
        pr = repo.create_pull(
            title=f"[KubePilot AI] Fix: {alert_name} on {pod_name}",
            body=pr_body,
            head=branch_name,
            base="main",
        )

        logger.info(f"Created remediation PR #{pr.number}: {pr.html_url}")
        return {
            "status": "created",
            "pr_url": pr.html_url,
            "pr_number": pr.number,
            "branch": branch_name,
        }

    except Exception as e:
        logger.error(f"Failed to create GitHub PR: {e}")
        return {"status": "error", "reason": str(e)}

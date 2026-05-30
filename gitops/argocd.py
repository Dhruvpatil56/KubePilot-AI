import logging
import os
import sys
import time

import requests

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ARGOCD_URL, ARGOCD_TOKEN


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {ARGOCD_TOKEN}",
        "Content-Type": "application/json",
    }


def get_argocd_app_status(app_name: str) -> dict:
    """Return sync and health status for an ArgoCD application."""
    if not ARGOCD_URL:
        logger.warning("ARGOCD_URL not set — skipping ArgoCD status check")
        return {"status": "skipped", "reason": "ARGOCD_URL not set"}

    try:
        resp = requests.get(
            f"{ARGOCD_URL}/api/v1/applications/{app_name}",
            headers=_headers(),
            timeout=10,
            verify=False,
        )
        resp.raise_for_status()
        data = resp.json()
        sync_status = data.get("status", {}).get("sync", {}).get("status")
        health_status = data.get("status", {}).get("health", {}).get("status")
        logger.info(f"ArgoCD app {app_name}: sync={sync_status}, health={health_status}")
        return {
            "status": "ok",
            "app_name": app_name,
            "sync_status": sync_status,
            "health_status": health_status,
        }
    except Exception as e:
        logger.warning(f"ArgoCD status check failed for {app_name}: {e}")
        return {"status": "error", "reason": str(e)}


def sync_argocd_app(app_name: str) -> dict:
    """Trigger an ArgoCD sync for the given application."""
    if not ARGOCD_URL:
        logger.warning("ARGOCD_URL not set — skipping ArgoCD sync")
        return {"status": "skipped", "reason": "ARGOCD_URL not set"}

    try:
        resp = requests.post(
            f"{ARGOCD_URL}/api/v1/applications/{app_name}/sync",
            headers=_headers(),
            json={},
            timeout=30,
            verify=False,
        )
        resp.raise_for_status()
        logger.info(f"ArgoCD sync triggered for {app_name}")
        return {"status": "syncing", "app_name": app_name}
    except Exception as e:
        logger.warning(f"ArgoCD sync failed for {app_name}: {e}")
        return {"status": "error", "reason": str(e)}


def wait_for_argocd_sync(app_name: str, timeout: int = 120) -> bool:
    """
    Poll every 10 s until the ArgoCD app reaches sync_status == 'Synced'
    or the timeout expires. Returns True if synced, False otherwise.
    """
    if not ARGOCD_URL:
        logger.warning("ARGOCD_URL not set — skipping ArgoCD sync wait")
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        result = get_argocd_app_status(app_name)
        if result.get("sync_status") == "Synced":
            logger.info(f"ArgoCD app {app_name} is Synced")
            return True
        time.sleep(10)

    logger.warning(f"ArgoCD sync timeout after {timeout}s for app {app_name}")
    return False

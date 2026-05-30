import time
import logging
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


def _load_k8s():
    try:
        from kubernetes import client, config as k8s_config
        try:
            k8s_config.load_incluster_config()
        except Exception:
            k8s_config.load_kube_config()
        return client.CoreV1Api()
    except Exception as e:
        logger.error(f"Failed to load K8s config: {e}")
        return None


def get_restart_count(pod_name: str, namespace: str) -> int:
    v1 = _load_k8s()
    if v1 is None:
        return -1
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        total = 0
        for cs in (pod.status.container_statuses or []):
            total += cs.restart_count
        return total
    except Exception as e:
        logger.warning(f"get_restart_count: {e}")
        return -1


def verify_pod_health(pod_name: str, namespace: str, timeout: int = 600) -> dict:
    v1 = _load_k8s()
    if v1 is None:
        return {"healthy": False, "reason": "could not connect to Kubernetes", "duration_seconds": 0}

    start = time.time()
    initial_restarts = get_restart_count(pod_name, namespace)
    poll_interval = 30

    while True:
        elapsed = int(time.time() - start)

        try:
            pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        except Exception as e:
            msg = str(e)
            if "not found" in msg.lower() or "404" in msg:
                return {"healthy": False, "reason": "pod not found", "duration_seconds": elapsed}
            logger.warning(f"verify_pod_health poll error: {e}")
            if elapsed >= timeout:
                return {"healthy": False, "reason": f"poll error: {e}", "duration_seconds": elapsed}
            time.sleep(poll_interval)
            continue

        phase = (pod.status.phase or "").lower()
        conditions = pod.status.conditions or []
        ready = any(c.type == "Ready" and c.status == "True" for c in conditions)

        current_restarts = sum(
            cs.restart_count for cs in (pod.status.container_statuses or [])
        )
        restarts_increased = initial_restarts >= 0 and current_restarts > initial_restarts

        if phase == "running" and ready and not restarts_increased:
            return {"healthy": True, "reason": "pod running, ready, no new restarts", "duration_seconds": elapsed}

        if elapsed >= timeout:
            reason_parts = []
            if phase != "running":
                reason_parts.append(f"phase={phase}")
            if not ready:
                reason_parts.append("not ready")
            if restarts_increased:
                reason_parts.append(f"restarts increased ({initial_restarts}->{current_restarts})")
            return {
                "healthy": False,
                "reason": "; ".join(reason_parts) or "timeout",
                "duration_seconds": elapsed,
            }

        logger.info(f"verify_pod_health: {pod_name} phase={phase} ready={ready} restarts={current_restarts} elapsed={elapsed}s")
        time.sleep(poll_interval)

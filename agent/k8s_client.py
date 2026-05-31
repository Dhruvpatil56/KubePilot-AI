from kubernetes import client, config as k8s_config
from typing import Dict, List, Optional
from datetime import datetime, timezone
import logging
import time

logger = logging.getLogger(__name__)


class K8sClient:
    def __init__(self):
        try:
            # Try to load in-cluster config first (when running in k8s)
            k8s_config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except Exception:
            # Fall back to local kubeconfig (for dev)
            k8s_config.load_kube_config()
            logger.info("Loaded local Kubernetes config")

        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

    def get_pod_details(self, pod_name: str, namespace: str) -> Optional[Dict]:
        """Get detailed information about a pod"""
        try:
            pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)

            return {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "conditions": [
                    {
                        "type": c.type,
                        "status": c.status,
                        "reason": c.reason,
                        "message": c.message,
                    }
                    for c in (pod.status.conditions or [])
                ],
                "container_statuses": [
                    {
                        "name": cs.name,
                        "ready": cs.ready,
                        "restart_count": cs.restart_count,
                        "state": self._get_container_state(cs),
                        "last_state": self._get_container_last_state(cs),
                    }
                    for cs in (pod.status.container_statuses or [])
                ],
                "node_name": pod.spec.node_name,
                "labels": pod.metadata.labels or {},
            }
        except Exception as e:
            logger.error(f"Error getting pod details: {e}")
            return None

    def _get_container_state(self, container_status) -> Dict:
        """Extract current container state"""
        state = container_status.state
        if state.running:
            return {"status": "running", "started_at": str(state.running.started_at)}
        elif state.waiting:
            return {
                "status": "waiting",
                "reason": state.waiting.reason,
                "message": state.waiting.message,
            }
        elif state.terminated:
            return {
                "status": "terminated",
                "reason": state.terminated.reason,
                "exit_code": state.terminated.exit_code,
                "message": state.terminated.message,
            }
        return {"status": "unknown"}

    def _get_container_last_state(self, container_status) -> Optional[Dict]:
        """Extract last container state (useful for crashes)"""
        last = container_status.last_state
        if not last:
            return None

        if last.terminated:
            return {
                "status": "terminated",
                "reason": last.terminated.reason,
                "exit_code": last.terminated.exit_code,
                "message": last.terminated.message,
                "finished_at": str(last.terminated.finished_at),
            }
        return None

    def get_pod_logs(self, pod_name: str, namespace: str, lines: int = 50) -> str:
        """Get recent logs from a pod"""
        try:
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name, namespace=namespace, tail_lines=lines
            )
            return logs or ""
        except Exception as e:
            logger.error(f"Error getting pod logs: {e}")
            return f"Error retrieving logs: {str(e)}"

    def get_previous_pod_logs(self, pod_name: str, namespace: str, lines: int = 50) -> str:
        """Get logs from previous container (if pod crashed)"""
        try:
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=lines,
                previous=True,
            )
            return logs or ""
        except Exception as e:
            return f"No previous logs available: {str(e)}"

    def get_pod_events(self, pod_name: str, namespace: str) -> List[Dict]:
        """Get recent events related to a pod"""
        try:
            events = self.core_v1.list_namespaced_event(
                namespace=namespace,
                field_selector=f"involvedObject.name={pod_name}",
            )

            return [
                {
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "count": event.count,
                    "first_timestamp": str(event.first_timestamp),
                    "last_timestamp": str(event.last_timestamp),
                }
                for event in sorted(
                    events.items,
                    key=lambda x: x.last_timestamp or x.first_timestamp,
                    reverse=True,
                )[:10]
            ]
        except Exception as e:
            logger.error(f"Error getting pod events: {e}")
            return []

    def restart_pod(self, pod_name: str, namespace: str) -> bool:
        """Restart a pod by deleting it (ReplicaSet will recreate)"""
        try:
            self.core_v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
            logger.info(f"Deleted pod {pod_name} for restart")
            return True
        except Exception as e:
            logger.error(f"Error restarting pod: {e}")
            return False

    def scale_deployment(self, deployment_name: str, namespace: str, replicas: int) -> bool:
        """Scale a deployment"""
        try:
            self.apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=namespace,
                body={"spec": {"replicas": replicas}},
            )
            logger.info(f"Scaled deployment {deployment_name} to {replicas} replicas")
            return True
        except Exception as e:
            logger.error(f"Error scaling deployment: {e}")
            return False

    def get_deployment_from_pod(self, pod_name: str, namespace: str) -> Optional[str]:
        """Infer deployment name that owns this pod"""
        try:
            pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)

            # Check owner references
            if pod.metadata.owner_references:
                for owner in pod.metadata.owner_references:
                    if owner.kind == "ReplicaSet":
                        rs = self.apps_v1.read_namespaced_replica_set(
                            name=owner.name,
                            namespace=namespace,
                        )
                        if rs.metadata.owner_references:
                            for rs_owner in rs.metadata.owner_references:
                                if rs_owner.kind == "Deployment":
                                    return rs_owner.name
            return None
        except Exception as e:
            logger.error(f"Error getting deployment from pod: {e}")
            return None

    def restart_deployment(self, deployment_name: str, namespace: str) -> bool:
        """Trigger a restart of deployment by touching an annotation (rollout restart style)"""
        try:
            body = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "self-healer/restarted-at": client.V1Time().to_str()
                            }
                        }
                    }
                }
            }
            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=body,
            )
            logger.info(f"Triggered restart for deployment {deployment_name}")
            return True
        except Exception as e:
            logger.error(f"Error restarting deployment: {e}")
            return False

    def rollback_deployment(self, deployment_name: str, namespace: str) -> bool:
        """Roll back a deployment to its previous revision via ReplicaSet history."""
        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name, namespace=namespace
            )
            selector = deployment.spec.selector.match_labels
            label_selector = ",".join(f"{k}={v}" for k, v in selector.items())

            all_rs = self.apps_v1.list_namespaced_replica_set(
                namespace=namespace, label_selector=label_selector
            )

            def _revision(rs):
                return int((rs.metadata.annotations or {}).get(
                    "deployment.kubernetes.io/revision", 0
                ))

            sorted_rs = sorted(all_rs.items, key=_revision, reverse=True)
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            if len(sorted_rs) >= 2:
                prev_rs = sorted_rs[1]
                containers = prev_rs.spec.template.spec.containers
                image_patch = [{"name": c.name, "image": c.image} for c in containers]
                logger.info(
                    f"Rolling back {deployment_name} to revision {_revision(prev_rs)}"
                )
            else:
                logger.warning(
                    f"No previous revision for {deployment_name}, triggering restart"
                )
                image_patch = None

            patch: dict = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "kubectl.kubernetes.io/restartedAt": now_str
                            }
                        },
                        "spec": {},
                    }
                }
            }
            if image_patch:
                patch["spec"]["template"]["spec"]["containers"] = image_patch

            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name, namespace=namespace, body=patch
            )

            # Wait up to 60s for rollback to complete
            deadline = time.time() + 60
            while time.time() < deadline:
                dep = self.apps_v1.read_namespaced_deployment(
                    name=deployment_name, namespace=namespace
                )
                desired = dep.spec.replicas or 1
                available = dep.status.available_replicas or 0
                if available >= desired:
                    logger.info(
                        f"Rollback complete: {deployment_name} {available}/{desired} available"
                    )
                    return True
                time.sleep(5)

            logger.warning(f"Rollback timeout: {deployment_name} not fully available after 60s")
            return False

        except Exception as e:
            logger.error(f"Error rolling back deployment {deployment_name}: {e}")
            return False


# ---------- Remediation Actions ----------
def restart_pod(pod_name: str, namespace: str):
    try:
        k8s_config.load_incluster_config()
    except:
        k8s_config.load_kube_config()
    v1 = client.CoreV1Api()
    v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
    logger.info(f"✅ Deleted pod {pod_name} — Kubernetes will recreate it")

def scale_deployment(pod_name: str, namespace: str, replicas: int):
    try:
        k8s_config.load_incluster_config()
    except:
        k8s_config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    # Get deployment name from pod
    v1 = client.CoreV1Api()
    pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
    owner = pod.metadata.owner_references[0]
    rs = apps_v1.read_namespaced_replica_set(name=owner.name, namespace=namespace)
    deploy_name = rs.metadata.owner_references[0].name
    # Scale it
    apps_v1.patch_namespaced_deployment_scale(
        name=deploy_name,
        namespace=namespace,
        body={"spec": {"replicas": replicas}}
    )
    logger.info(f"✅ Scaled {deploy_name} to {replicas} replicas")


def verify_rollback(deployment_name: str, namespace: str, timeout: int = 60) -> bool:
    """Return True when availableReplicas >= replicas within timeout seconds."""
    try:
        k8s_config.load_incluster_config()
    except Exception:
        k8s_config.load_kube_config()

    apps_v1 = client.AppsV1Api()
    deadline = time.time() + timeout
    while time.time() < deadline:
        dep = apps_v1.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        desired = dep.spec.replicas or 1
        available = dep.status.available_replicas or 0
        if available >= desired:
            logger.info(f"✅ {deployment_name}: {available}/{desired} replicas available — rollback healthy")
            return True
        time.sleep(5)
    logger.warning(f"❌ Rollback timeout: {deployment_name} not fully available after {timeout}s")
    return False


def rollback_deployment(pod_name: str, namespace: str) -> bool:
    """
    Roll back the deployment that owns pod_name to its previous revision.
    Steps:
      1. Trace pod → ReplicaSet → Deployment
      2. List all ReplicaSets ordered by deployment.kubernetes.io/revision annotation
      3. Patch deployment spec with previous revision's container images
         and set kubectl.kubernetes.io/restartedAt to trigger a rolling update
      4. Wait up to 60s via verify_rollback for healthy state
    """
    try:
        k8s_config.load_incluster_config()
    except Exception:
        k8s_config.load_kube_config()

    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    # Step 1: pod → ReplicaSet → Deployment
    pod = core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)

    rs_name = None
    for ref in pod.metadata.owner_references or []:
        if ref.kind == "ReplicaSet":
            rs_name = ref.name
            break
    if not rs_name:
        logger.error(f"❌ Could not find ReplicaSet owner for pod {pod_name}")
        return False

    rs = apps_v1.read_namespaced_replica_set(name=rs_name, namespace=namespace)

    deploy_name = None
    for ref in rs.metadata.owner_references or []:
        if ref.kind == "Deployment":
            deploy_name = ref.name
            break
    if not deploy_name:
        logger.error(f"❌ Could not find Deployment owner for ReplicaSet {rs_name}")
        return False

    logger.info(f"🔁 Rolling back deployment {deploy_name} in {namespace}")

    # Step 2: rollout history via ReplicaSets ordered by revision annotation
    deployment = apps_v1.read_namespaced_deployment(name=deploy_name, namespace=namespace)
    selector = deployment.spec.selector.match_labels
    label_selector = ",".join(f"{k}={v}" for k, v in selector.items())

    all_rs = apps_v1.list_namespaced_replica_set(namespace=namespace, label_selector=label_selector)

    def _revision(r):
        return int((r.metadata.annotations or {}).get("deployment.kubernetes.io/revision", 0))

    sorted_rs = sorted(all_rs.items, key=_revision, reverse=True)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Step 3: build rollback patch
    if len(sorted_rs) >= 2:
        prev_rs = sorted_rs[1]
        containers = prev_rs.spec.template.spec.containers
        image_patch = [{"name": c.name, "image": c.image} for c in containers]
        logger.info(f"⏪ Targeting revision {_revision(prev_rs)}: {[c['image'] for c in image_patch]}")
    else:
        logger.warning(f"⚠️  No previous revision found for {deploy_name} — triggering restart")
        image_patch = None

    patch: dict = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "kubectl.kubernetes.io/restartedAt": now_str
                    }
                },
                "spec": {},
            }
        }
    }
    if image_patch:
        patch["spec"]["template"]["spec"]["containers"] = image_patch

    apps_v1.patch_namespaced_deployment(name=deploy_name, namespace=namespace, body=patch)
    logger.info(f"✅ Rollback patch applied to {deploy_name}")

    # Step 4: wait up to 60s for rollback to complete
    return verify_rollback(deploy_name, namespace)

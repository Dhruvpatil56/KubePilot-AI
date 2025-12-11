from kubernetes import client, config as k8s_config
from typing import Dict, List, Optional
import logging

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
        """
        'Rollback' placeholder – here implemented as a restart trigger.
        Real rollback would be via GitOps or previous ReplicaSet selection.
        """
        return self.restart_deployment(deployment_name, namespace)


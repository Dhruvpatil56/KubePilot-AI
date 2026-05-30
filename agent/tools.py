from langchain_core.tools import tool
from kubernetes import client, config as k8s_config
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import K8S_NAMESPACE

# Load k8s config
try:
    k8s_config.load_incluster_config()
except:
    k8s_config.load_kube_config()

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

@tool
def get_pod_status(pod_name: str) -> str:
    """Get current status, restart count, and conditions of a pod."""
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=K8S_NAMESPACE)
        container = pod.status.container_statuses[0] if pod.status.container_statuses else None
        result = {
            "phase": pod.status.phase,
            "restart_count": container.restart_count if container else 0,
            "ready": container.ready if container else False,
            "state": str(container.state) if container else "unknown"
        }
        return str(result)
    except Exception as e:
        return f"Error getting pod status: {str(e)}"

@tool
def get_pod_logs(pod_name: str) -> str:
    """Get the last 50 lines of current logs from a pod."""
    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=K8S_NAMESPACE,
            tail_lines=50
        )
        return logs if logs else "No logs available"
    except Exception as e:
        return f"Error getting logs: {str(e)}"

@tool
def get_previous_pod_logs(pod_name: str) -> str:
    """Get logs from the previously crashed container — critical for RCA."""
    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=K8S_NAMESPACE,
            previous=True,
            tail_lines=50
        )
        return logs if logs else "No previous logs available"
    except Exception as e:
        return f"Error getting previous logs: {str(e)}"

@tool
def get_pod_events(pod_name: str) -> str:
    """Get Kubernetes events for a pod — timeline of what happened."""
    try:
        events = v1.list_namespaced_event(namespace=K8S_NAMESPACE)
        pod_events = [
            f"{e.reason}: {e.message} (count: {e.count})"
            for e in events.items
            if e.involved_object.name == pod_name
        ]
        return "\n".join(pod_events) if pod_events else "No events found"
    except Exception as e:
        return f"Error getting events: {str(e)}"

@tool
def get_deployment_info(pod_name: str) -> str:
    """Get deployment info by tracing pod → replicaset → deployment."""
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=K8S_NAMESPACE)
        owner = pod.metadata.owner_references[0] if pod.metadata.owner_references else None
        if not owner:
            return "No owner found for pod"

        rs = apps_v1.read_namespaced_replica_set(name=owner.name, namespace=K8S_NAMESPACE)
        deploy_owner = rs.metadata.owner_references[0] if rs.metadata.owner_references else None
        if not deploy_owner:
            return "No deployment found"

        deploy = apps_v1.read_namespaced_deployment(name=deploy_owner.name, namespace=K8S_NAMESPACE)
        result = {
            "deployment_name": deploy.metadata.name,
            "replicas": deploy.spec.replicas,
            "available_replicas": deploy.status.available_replicas,
            "image": deploy.spec.template.spec.containers[0].image
        }
        return str(result)
    except Exception as e:
        return f"Error getting deployment info: {str(e)}"

# Tool list for agent
TOOLS = [
    get_pod_status,
    get_pod_logs,
    get_previous_pod_logs,
    get_pod_events,
    get_deployment_info
]

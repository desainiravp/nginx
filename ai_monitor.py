import subprocess
import requests

DEPLOYMENT_NAME = "nginx-deployment"
APP_LABEL = "nginx"


def get_pod_logs():
    pod = subprocess.check_output(
        f"kubectl get pods -l app={APP_LABEL} -o jsonpath='{{.items[0].metadata.name}}'",
        shell=True
    ).decode().strip().replace("'", "")

    logs = subprocess.check_output(
        f"kubectl logs {pod} --tail=50",
        shell=True
    ).decode()

    return logs


def rollback(reason):
    print("🔁 Rolling back deployment...")
    subprocess.call(
        f"kubectl rollout undo deployment/{DEPLOYMENT_NAME}",
        shell=True
    )
    print(f"Rollback done. Reason: {reason}")


def analyze_logs(logs):
    prompt = f"""
    Analyze Kubernetes logs and detect issues.

    Return ONLY:
    OK
    or
    FAIL with reason

    Logs:
    {logs}
    """

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
    )

    result = response.json()["response"]
    print("AI Result:", result)

    if "fail" in result.lower():
        rollback(result)
        exit(1)
    else:
        print("✅ Deployment looks healthy")


if __name__ == "__main__":
    logs = get_pod_logs()
    analyze_logs(logs)

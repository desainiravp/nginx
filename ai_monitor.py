import os
import subprocess
import requests
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEPLOYMENT_NAME = "nginx-deployment"
APP_LABEL = "nginx"   # must match your k8s label
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")


def send_slack(message):
    if not SLACK_WEBHOOK:
        return
    requests.post(SLACK_WEBHOOK, json={"text": message})


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
    subprocess.call(
        f"kubectl rollout undo deployment/{DEPLOYMENT_NAME}",
        shell=True
    )
    send_slack(f"❌ Rollback triggered\nReason: {reason}")


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

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    result = response.choices[0].message.content
    print(result)

    if "FAIL" in result:
        rollback(result)
        exit(1)
    else:
        send_slack("✅ Deployment successful")


if __name__ == "__main__":
    logs = get_pod_logs()
    analyze_logs(logs)

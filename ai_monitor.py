import subprocess
import requests

DEPLOYMENT_NAME = "nginx-deployment"
APP_LABEL = "nginx"


# 🔥 Check pod status FIRST (most reliable)
def check_pod_status():
    output = subprocess.check_output(
        f"kubectl get pods -l app={APP_LABEL}",
        shell=True
    ).decode().lower()

    print("📊 POD STATUS:\n", output)

    if "crashloopbackoff" in output or "error" in output or "imagepullbackoff" in output:
        print("❌ Pod status indicates failure")
        rollback("Pod failure detected (CrashLoop/ImagePull)")
        exit(1)


# 🔥 Get logs from ALL pods
def get_pod_logs():
    pods = subprocess.check_output(
        f"kubectl get pods -l app={APP_LABEL} -o jsonpath='{{.items[*].metadata.name}}'",
        shell=True
    ).decode().strip().replace("'", "").split()

    all_logs = ""

    for pod in pods:
        print(f"🔍 Checking pod: {pod}")
        try:
            logs = subprocess.check_output(
                f"kubectl logs {pod} --tail=20",
                shell=True
            ).decode()
            all_logs += f"\n--- Logs from {pod} ---\n{logs}\n"
        except:
            all_logs += f"\n--- Logs from {pod} ---\nERROR fetching logs\n"

    return all_logs


def rollback(reason):
    print("🔁 Rolling back deployment...")
    subprocess.call(
        f"kubectl rollout undo deployment/{DEPLOYMENT_NAME}",
        shell=True
    )
    print(f"Rollback done. Reason: {reason}")


def analyze_logs(logs):
    prompt = f"""
You are a strict DevOps validator.

ONLY respond with:
OK
or
FAIL: <reason>

Do not repeat logs.

Logs:
{logs}
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "tinyllama:latest",
                "prompt": prompt,
                "stream": False
            }
        )

        print("RAW RESPONSE:", response.text)

        data = response.json()
        result = data.get("response", "").strip()

        if not result:
            print("⚠️ No response from AI:", data)
            return

        print("AI Result:", result)

    except Exception as e:
        print("⚠️ AI error:", str(e))
        return

    # 🔥 fallback keyword detection (important)
    logs_lower = logs.lower()
    error_keywords = [
        "error",
        "exception",
        "failed",
        "connection refused",
        "crashloopbackoff",
        "oomkilled"
    ]

    if any(keyword in logs_lower for keyword in error_keywords):
        print("❌ Error detected in logs")
        rollback("Detected error in logs")
        exit(1)

    # 🔥 AI-based decision
    if "fail" in result.lower():
        rollback(result)
        exit(1)

    print("✅ Deployment looks healthy")


if __name__ == "__main__":
    check_pod_status()   # 🔥 NEW (critical)
    logs = get_pod_logs()
    analyze_logs(logs)

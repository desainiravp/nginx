import subprocess
import requests

DEPLOYMENT_NAME = "nginx-deployment"
APP_LABEL = "nginx"


# 🔥 1. Check pod status (most reliable)
def check_pod_status():
    output = subprocess.check_output(
        f"kubectl get pods -l app={APP_LABEL}",
        shell=True
    ).decode().lower()

    print("📊 POD STATUS:\n", output)

    if (
        "crashloopbackoff" in output
        or "error" in output
        or "imagepullbackoff" in output
        or "errimagepull" in output
    ):
        print("❌ Pod status indicates failure")
        rollback("Pod failure detected")
        exit(1)


# 🔥 2. Get logs from ALL pods
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
        except Exception as e:
            all_logs += f"\n--- Logs from {pod} ---\nERROR fetching logs: {str(e)}\n"

    return all_logs


# 🔥 3. Rollback deployment
def rollback(reason):
    print("🔁 Rolling back deployment...")
    subprocess.call(
        f"kubectl rollout undo deployment/{DEPLOYMENT_NAME}",
        shell=True
    )
    print(f"Rollback done. Reason: {reason}")


# 🔥 4. AI + Rule-based analysis
def analyze_logs(logs):
    prompt = f"""
You are a Kubernetes log analyzer.

ONLY return:
OK
or
FAIL: <reason>

If logs are normal, return OK.
Do NOT invent issues.
Do NOT assume missing logs.

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

    # 🔥 PRIMARY: Real log-based detection (most reliable)
    logs_lower = logs.lower()

    error_keywords = [
        "error",
        "exception",
        "failed",
        "crashloopbackoff",
        "oomkilled",
        "connection refused",
        "panic"
    ]

    if any(keyword in logs_lower for keyword in error_keywords):
        print("❌ Real issue detected from logs")
        rollback("Detected error in logs")
        exit(1)

    # 🔥 SECONDARY: AI decision (controlled)
    if result.lower().startswith("fail"):
        print("⚠️ AI detected failure:", result)
        rollback(result)
        exit(1)

    # ✅ Final success
    print("✅ Deployment looks healthy")


# 🚀 MAIN
if __name__ == "__main__":
    check_pod_status()     # ✅ Step 1: pod health
    logs = get_pod_logs()  # ✅ Step 2: logs
    analyze_logs(logs)     # ✅ Step 3: AI + rules

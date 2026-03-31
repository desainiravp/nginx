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
You are a strict DevOps validator.

ONLY respond with:
OK
or
FAIL: <reason>

Logs:
{logs}
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "tinyllama:latest",   # ✅ changed here
                "prompt": prompt,
                "stream": False
            }
        )

        # 🔍 Debug (optional but useful)
        print("RAW RESPONSE:", response.text)

        data = response.json()

        # ✅ safe extraction (no KeyError)
        result = data.get("response")

        if not result:
            print("⚠️ No response from AI:", data)
            return

        result = result.strip()
        print("AI Result:", result)

    except Exception as e:
        print("⚠️ AI error:", str(e))
        return

    # 🔥 flexible check (tinyllama not always strict)
    if "fail" in result.lower() or "error" in result.lower():
        rollback(result)
        exit(1)
    else:
        print("✅ Deployment looks healthy")


if __name__ == "__main__":
    logs = get_pod_logs()
    analyze_logs(logs)

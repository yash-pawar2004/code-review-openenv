"""
OpenEnv-compliant inference script for code_review_env.
Reads API config from env vars. Emits [START], [STEP], [END] logs.
"""
import os, sys, json
from openai import OpenAI

ENV_URL    = os.getenv("ENV_URL",      "http://localhost:7860")
MODEL_NAME = os.getenv("MODEL_NAME",   "gpt-4o-mini")
API_BASE   = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
API_KEY    = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY", "")

TASK_IDS = ["style_review", "bug_review", "security_review"]

SYSTEM = "You are an expert Python code reviewer. Be concise and specific."

def _post(path: str, body: dict = None) -> dict:
    import requests
    url = ENV_URL.rstrip("/") + path
    r = requests.post(url, json=body or {}, timeout=30)
    r.raise_for_status()
    return r.json()

def _get(path: str) -> dict:
    import requests
    url = ENV_URL.rstrip("/") + path
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def _sanitize(s: str) -> str:
    return str(s).replace("\n", " ").replace("\r", " ").strip()[:200]

def run():
    print(f"[START] task=code_review env=code_review_env model={MODEL_NAME}")

    try:
        client = OpenAI(api_key=API_KEY, base_url=API_BASE)
    except Exception as e:
        print(f"[STEP] step=1 action=null reward=0.01 done=true error={_sanitize(e)}")
        print(f"[END] success=false steps=1 score=0.01 rewards=0.01")
        return 0.01

    all_rewards = []
    step_no = 0
    had_error = False

    for task_id in TASK_IDS:
        try:
            obs = _post("/reset", {"task_id": task_id})
        except Exception as e:
            step_no += 1
            print(f"[STEP] step={step_no} action=null reward=0.01 done=true error={_sanitize(e)}")
            all_rewards.append(0.01)
            had_error = True
            break

        done = False
        while not done:
            step_no += 1
            action = "null"
            reward = 0.01
            error = "null"
            try:
                prompt = (
                    f"Code to review:\n{obs['code']}\n\n"
                    f"Task: {obs['task_type']} ({obs['difficulty']})\n"
                    f"{obs['description']}"
                )
                resp = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role":"system","content":SYSTEM},
                              {"role":"user","content":prompt}],
                    max_tokens=150,
                )
                action = resp.choices[0].message.content.strip()
                result = _post("/step", {"review": action})
                reward = float(result["reward"])
                done = bool(result["done"])
                obs = result.get("observation", obs)
            except Exception as e:
                error = _sanitize(e)
                done = True
                had_error = True

            all_rewards.append(reward)
            print(f"[STEP] step={step_no} action={_sanitize(action)} reward={reward:.2f} done={str(done).lower()} error={error}")

    score = round(sum(all_rewards) / max(len(all_rewards), 1), 4)
    print(f"[END] success={str(not had_error).lower()} steps={step_no} score={score:.2f} rewards={','.join(f'{r:.2f}' for r in all_rewards)}")
    return score

if __name__ == "__main__":
    run()

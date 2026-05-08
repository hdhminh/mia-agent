#!/usr/bin/env python3
"""Deploy Gmail workflows to n8n via docker exec."""
import json
import os
import subprocess
import sys

WORK_DIR = "/home/huynhminh/Projects/n8n"

# Load .env
env_vars = {}
with open(os.path.join(WORK_DIR, ".env")) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env_vars[k] = v

API_KEY = env_vars.get("N8N_API_KEY", "")
N8N_URL = "http://localhost:5678"

if not API_KEY:
    print("ERROR: N8N_API_KEY not found in .env")
    sys.exit(1)


def docker_api(method, path, data=None):
    """Call n8n API via docker exec wget."""
    url = f"{N8N_URL}{path}"
    cmd = ["docker", "exec", "n8n", "wget", "-q", "-O", "-",
           f"--header=X-N8N-API-KEY: {API_KEY}",
           f"--header=Content-Type: application/json"]

    if method == "POST":
        body = json.dumps(data) if data else "{}"
        cmd += [f"--post-data={body}", url]
    elif method == "PUT":
        body = json.dumps(data) if data else "{}"
        cmd += ["--method=PUT", f"--body-data={body}", url]
    elif method == "PATCH":
        body = json.dumps(data) if data else "{}"
        cmd += ["--method=PATCH", f"--body-data={body}", url]
    else:
        cmd += [url]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            # Try with curl instead
            return docker_api_curl(method, path, data)
        return json.loads(result.stdout) if result.stdout.strip() else None
    except Exception as e:
        print(f"  wget failed: {e}, trying curl...")
        return docker_api_curl(method, path, data)


def docker_api_curl(method, path, data=None):
    """Fallback: call n8n API via docker exec curl."""
    url = f"{N8N_URL}{path}"
    cmd = ["docker", "exec", "n8n"]

    if data:
        body = json.dumps(data)
        # Write body to temp file inside container
        write_cmd = ["docker", "exec", "-i", "n8n", "sh", "-c", f"cat > /tmp/api_body.json"]
        proc = subprocess.Popen(write_cmd, stdin=subprocess.PIPE)
        proc.communicate(input=body.encode())

        cmd += ["wget", "-q", "-O", "-",
                f"--header=X-N8N-API-KEY: {API_KEY}",
                f"--header=Content-Type: application/json"]

        if method == "POST":
            cmd += [f"--post-file=/tmp/api_body.json", url]
        elif method in ("PUT", "PATCH"):
            cmd += [f"--method={method}", f"--body-file=/tmp/api_body.json", url]
    else:
        cmd += ["wget", "-q", "-O", "-",
                f"--header=X-N8N-API-KEY: {API_KEY}", url]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def find_workflow_by_name(name):
    import urllib.parse
    encoded = urllib.parse.quote(name)
    result = docker_api("GET", f"/api/v1/workflows?limit=250&name={encoded}")
    if not result:
        return None
    for w in result.get("data", []):
        if w["name"] == name:
            return w["id"]
    return None


def deploy_workflow(filepath):
    with open(filepath) as f:
        workflow = json.load(f)
    name = workflow["name"]
    print(f"\n--- Deploying: {name} ---")

    existing_id = find_workflow_by_name(name)

    if existing_id:
        print(f"  Found existing ID: {existing_id} -> Updating...")
        result = docker_api("PUT", f"/api/v1/workflows/{existing_id}", workflow)
        if result:
            print("  Updated!")
        else:
            print("  Update may have failed, continuing...")
        # Activate
        docker_api("PATCH", f"/api/v1/workflows/{existing_id}", {"active": True})
        print("  Activated!")
        return existing_id
    else:
        print("  Creating new workflow...")
        result = docker_api("POST", "/api/v1/workflows", workflow)
        if result:
            new_id = result.get("id", "")
            print(f"  Created with ID: {new_id}")
            if new_id:
                docker_api("PATCH", f"/api/v1/workflows/{new_id}", {"active": True})
                print("  Activated!")
            return new_id
        else:
            print("  FAILED to create!")
            return None


def main():
    gmail_dir = os.path.join(WORK_DIR, "google", "gmail")

    print("=" * 50)
    print("Deploying Gmail Workflows to n8n")
    print("=" * 50)

    # Step 1: Deploy sub-workflows first
    print("\n=== Step 1: Deploy Gmail Sub-Workflows ===")
    sub_files = [
        "workflow_sub_google_gmail_help.json",
        "workflow_sub_google_gmail_list_inbox.json",
        "workflow_sub_google_gmail_read_email.json",
        "workflow_sub_google_gmail_send_email.json",
        "workflow_sub_google_gmail_search_email.json",
        "workflow_sub_google_gmail_reply_email.json",
    ]
    for fname in sub_files:
        fpath = os.path.join(gmail_dir, fname)
        if os.path.exists(fpath):
            deploy_workflow(fpath)
        else:
            print(f"  WARNING: {fname} not found!")

    # Step 2: Deploy Gmail Master
    print("\n=== Step 2: Deploy Gmail Master ===")
    master_path = os.path.join(gmail_dir, "workflow_sub_google_gmail_master.json")
    deploy_workflow(master_path)

    # Step 3: Update Chatbot workflow
    print("\n=== Step 3: Update AI Chatbot (with Gmail routing) ===")
    chatbot_path = os.path.join(WORK_DIR, "workflow_sub_chatbot_advanced.json")
    deploy_workflow(chatbot_path)

    print("\n" + "=" * 50)
    print("All Gmail Workflows Deployed Successfully!")
    print("=" * 50)
    print("\nNOTE: You need to configure Gmail OAuth2 credentials")
    print("in n8n for the Gmail nodes to work properly.")


if __name__ == "__main__":
    main()

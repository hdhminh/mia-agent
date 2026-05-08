#!/usr/bin/env python3
import os
import subprocess
import json
import urllib.request
import sys

# Đổi đường dẫn vào thư mục n8n
WORK_DIR = "/home/huynhminh/Projects/n8n"
os.chdir(WORK_DIR)

def run(cmd, check=True):
    result = subprocess.run(cmd, text=True)
    if check and result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        sys.exit(result.returncode)
    return result

# 1. Kiểm tra xem có sự thay đổi nào không
status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
if not status:
    print("No changes found. Skipping.")
    sys.exit(0)

print("Changes detected! Gathering diff...")

# 2. Add tất cả các file đã thay đổi
subprocess.run(["git", "add", "."])

# 3. Lấy nội dung chi tiết của những đoạn code bị sửa (Diff)
diff = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True).stdout.strip()

if not diff:
    print("No diff generated.")
    sys.exit(0)

# Giới hạn diff 2000 ký tự để AI xử lý nhanh trên Pi 5
diff_excerpt = diff[:2000]

print("Asking Local Ollama AI to generate a meaningful English commit message...")

# 4. Nhờ AI đọc code và tạo Commit Message tiếng Anh
prompt = f"Write a short, professional, single-line Git commit message in English explaining these changes. Only output the commit message, no quotes, no explanations:\n\n{diff_excerpt}"

url = "http://localhost:11434/api/generate"
data = json.dumps({
    "model": "qwen2.5:3b",
    "prompt": prompt,
    "stream": False
}).encode("utf-8")

commit_msg = ""
try:
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    response = urllib.request.urlopen(req)
    result = json.loads(response.read().decode("utf-8"))
    commit_msg = result.get("response", "").strip()
    
    # Xóa dấu ngoặc kép nếu AI bị thừa
    if commit_msg.startswith('"') and commit_msg.endswith('"'):
        commit_msg = commit_msg[1:-1]
        
except Exception as e:
    print(f"Ollama AI failed: {e}")
    commit_msg = "Update n8n configurations and workflows"

if not commit_msg:
    commit_msg = "Update files automatically"

print(f"-> Generated Commit: {commit_msg}")

# 5. Tiến hành Commit, đồng bộ remote, rồi Push
print("Creating commit...")
run(["git", "commit", "-m", commit_msg])

print("Pulling latest changes from origin/main with rebase...")
run(["git", "pull", "--rebase", "origin", "main"])

print("Pushing to Github...")
run(["git", "push", "origin", "main"])

print("Sync completed successfully!")

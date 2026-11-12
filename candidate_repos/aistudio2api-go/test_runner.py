import os
import sys
import time
import json
import urllib.request
import urllib.error
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

base_dir = r"D:\Projects\cookie-service-suite\candidate_repos\aistudio2api-go\aistudio2api-v0.3.5-windows-amd64"
exe_path = os.path.join(base_dir, "aistudio2api.exe")

print("=" * 60)
print("🚀 [1/5] 启动 aistudio2api 核心守护进程...")
print("=" * 60)

# Check if already running or launch
proc = subprocess.Popen([exe_path], cwd=base_dir)
print(f"aistudio2api 已拉起，PID: {proc.pid}")

# Wait for HTTP server
ready = False
for i in range(20):
    time.sleep(1)
    try:
        req = urllib.request.Request("http://127.0.0.1:2048/api/status")
        with opener.open(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"✅ 管理端在线! HTTP {resp.status}, 状态: {data}")
            ready = True
            break
    except Exception as e:
        print(f"等待端口 2048 就绪 ({i+1}/20)...")

if not ready:
    print("❌ 管理端未能按期就绪，退出测试。")
    proc.terminate()
    sys.exit(1)

print("\n" + "=" * 60)
print("👤 [2/5] 检查已载入的 Google AI Studio 账户列表...")
print("=" * 60)
try:
    req = urllib.request.Request("http://127.0.0.1:2048/api/accounts")
    with opener.open(req, timeout=5) as resp:
        accounts = json.loads(resp.read().decode("utf-8"))
        print(f"账号列表响应:\n{json.dumps(accounts, indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"获取账号列表失败: {e}")

print("\n" + "=" * 60)
print("⚡ [3/5] 发送 POST /api/control/start 启动数据面与模型实时探测...")
print("=" * 60)
try:
    start_req = urllib.request.Request(
        "http://127.0.0.1:2048/api/control/start",
        data=b"{}",
        headers={"Content-Type": "application/json"}
    )
    with opener.open(start_req, timeout=30) as resp:
        start_res = resp.read().decode("utf-8")
        print(f"启动响应: {start_res}")
except Exception as e:
    print(f"启动控制面失败或响应: {e}")

time.sleep(3)

print("\n" + "=" * 60)
print("📋 [4/5] 获取 AI Studio 模型目录 (/v1/models)...")
print("=" * 60)
models = []
try:
    req = urllib.request.Request("http://127.0.0.1:2048/v1/models")
    with opener.open(req, timeout=10) as resp:
        model_data = json.loads(resp.read().decode("utf-8"))
        models = [m.get("id") for m in model_data.get("data", [])]
        print(f"获取到模型总数: {len(models)}")
        print(f"模型列表: {models[:10]}")
except Exception as e:
    print(f"获取模型列表失败: {e}")

print("\n" + "=" * 60)
print("🧪 [5/5] 测试 OpenAI 兼容聊天生成 (/v1/chat/completions)...")
print("=" * 60)
test_model = "gemini-2.5-flash" if "gemini-2.5-flash" in models else (models[0] if models else "gemini-2.5-flash")
print(f"选用测试模型: {test_model}")

chat_payload = json.dumps({
    "model": test_model,
    "messages": [
        {"role": "user", "content": "请回答：1+1等于几？请严格只回答一个阿拉伯数字。"}
    ],
    "stream": False
}).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:2048/v1/chat/completions",
    data=chat_payload,
    headers={"Content-Type": "application/json"}
)

t0 = time.time()
try:
    with opener.open(req, timeout=60) as resp:
        elapsed = round(time.time() - t0, 2)
        res_data = json.loads(resp.read().decode("utf-8"))
        print(f"🟢 调用成功! HTTP {resp.status} (耗时: {elapsed}s)")
        print(f"响应结果:\n{json.dumps(res_data, indent=2, ensure_ascii=False)}")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"🔴 HTTP 异常 {e.code}: {body}")
except Exception as e:
    print(f"🔴 请求失败: {e}")

# Check recent log
print("\n" + "=" * 60)
print("📜 最终服务日志 (runtime/logs/aistudio2api.log)...")
print("=" * 60)
log_file = os.path.join(base_dir, "runtime", "logs", "aistudio2api.log")
if os.path.exists(log_file):
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        for line in lines[-15:]:
            print(line.strip())

proc.terminate()
print("\n测试脚本执行完毕。")

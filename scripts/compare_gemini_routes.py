#!/usr/bin/env python3
"""Paired benchmark: Gemini Cookie Pool vs Google AI Studio direct endpoint."""
import csv, json, os, statistics, tempfile, time, urllib.error, urllib.request, sys, math
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
from pathlib import Path

BASE = "http://127.0.0.1:18800"
MODEL = "gemini-3.8-flash"
ROUNDS = 5
GEMINI_MIN_GAP_SECONDS = 12.5
TIMEOUT_SECONDS = 180
PROMPT = ("请用中文写一段约100字的家庭教育建议，主题是孩子顶嘴时父母应该如何回应。"
          "内容要具体、自然、有可执行性，不要列标题，不要编造书籍引用。")

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "model-benchmarks"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
STAMP = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
PREFIX = "gemini-pool-vs-aistudio-" + STAMP
JSON_PATH, CSV_PATH, MD_PATH = (REPORT_DIR / (PREFIX + ext) for ext in (".json", ".csv", ".md"))
HISTORY_JSONL = REPORT_DIR / "hourly-history.jsonl"
HISTORY_CSV = REPORT_DIR / "hourly-history.csv"

def request_json(path, payload=None, timeout=30):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data,
        headers={"Content-Type":"application/json"} if data is not None else {},
        method="POST" if data is not None else "GET")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw, status = resp.read().decode("utf-8", errors="replace"), resp.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read().decode("utf-8", errors="replace"), exc.code
    except Exception as exc:
        return {"http_status":None, "transport_error":repr(exc),
                "client_wall_ms":round((time.perf_counter()-started)*1000), "body":None}
    try: body = json.loads(raw)
    except Exception: body = {"raw":raw[:5000]}
    return {"http_status":status, "client_wall_ms":round((time.perf_counter()-started)*1000), "body":body}

def extract_result(record):
    body = record.get("body") or {}
    result = body.get("result") if isinstance(body,dict) else {}
    result = result if isinstance(result,dict) else {}
    choices = result.get("choices") or body.get("choices") or []
    reply = ""
    if choices:
        msg = choices[0].get("message") or {}
        reply = msg.get("content") or choices[0].get("text") or ""
    reply = reply or body.get("reply") or body.get("text") or ""
    usage = result.get("usage") or body.get("usage") or {}
    detail = body.get("detail") or {}
    error = (detail.get("message") if isinstance(detail,dict) else str(detail)) or body.get("error") or record.get("transport_error") or ""
    return {
        "success": bool(body.get("success") is True or (record.get("http_status")==200 and bool(reply or choices))),
        "model": result.get("model") or body.get("model") or MODEL,
        "provider_model": result.get("provider_model") or body.get("provider_model") or "",
        "provider_latency_ms": result.get("latency_ms") or body.get("total_ms") or body.get("latency_ms"),
        "account_id": body.get("account_id") or body.get("account") or "",
        "account_label": body.get("account_label") or "",
        "prompt_tokens": usage.get("prompt_tokens") if isinstance(usage,dict) else None,
        "completion_tokens": usage.get("completion_tokens") if isinstance(usage,dict) else None,
        "total_tokens": usage.get("total_tokens") if isinstance(usage,dict) else None,
        "reply": reply,
        "error": str(error)[:2000],
    }

def snapshot():
    g = request_json("/api/gemini/accounts")
    a = request_json("/api/aistudio/status")
    gb, ab = g.get("body") or {}, a.get("body") or {}
    accounts = []
    for x in gb.get("accounts",[]):
        accounts.append({k:x.get(k) for k in (
            "id","status","fail_count","quota_5h_used","quota_5h_limit","quota_5h_remaining",
            "quota_weekly_used","quota_weekly_limit","quota_weekly_remaining","quota_status")})
    return {
        "captured_at":datetime.now().astimezone().isoformat(),
        "gemini_accounts_total":gb.get("total"), "gemini_accounts":accounts,
        "aistudio_running":ab.get("running"), "aistudio_state":ab.get("state"),
        "aistudio_accounts_total":ab.get("accounts_total"), "aistudio_accounts_ready":ab.get("accounts_ready"),
        "aistudio_benefit_tier":((ab.get("accounts") or [{}])[0].get("benefit_tier")),
        "aistudio_quota_numeric":None,
        "aistudio_quota_note":"AI Studio status endpoint does not expose numeric remaining quota."
    }

def save_json(data):
    fd,tmp = tempfile.mkstemp(prefix="benchmark-",suffix=".tmp",dir=str(REPORT_DIR))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
        os.replace(tmp,JSON_PATH)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def append_history(data):
    """Append one idempotent aggregate row for long-term hourly trend analysis."""
    run_id = data.get("run_id") or PREFIX
    existing_ids = set()
    if HISTORY_JSONL.exists():
        with HISTORY_JSONL.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    existing_ids.add(json.loads(line).get("run_id"))
                except Exception:
                    continue
    if run_id in existing_ids:
        return
    summary = {
        "run_id": run_id,
        "created_at": data.get("created_at"),
        "model": data.get("model"),
    }
    for route, prefix in (("gemini_pool", "pool"), ("aistudio", "aistudio")):
        xs = [x for x in data["tests"] if x["route"] == route]
        good = [x for x in xs if x["success"] and isinstance(x.get("client_wall_ms"), int)]
        vals = sorted(x["client_wall_ms"] for x in good)
        p95 = vals[max(0, math.ceil(0.95 * len(vals)) - 1)] if vals else None
        summary[prefix + "_success"] = len(good)
        summary[prefix + "_total"] = len(xs)
        summary[prefix + "_avg_ms"] = round(statistics.mean(vals)) if vals else None
        summary[prefix + "_median_ms"] = round(statistics.median(vals)) if vals else None
        summary[prefix + "_p95_ms"] = p95
    pool_rounds = {x["round"]: x for x in data["tests"] if x["route"] == "gemini_pool"}
    ai_rounds = {x["round"]: x for x in data["tests"] if x["route"] == "aistudio"}
    paired = [(pool_rounds[n], ai_rounds[n]) for n in sorted(set(pool_rounds) & set(ai_rounds))
              if pool_rounds[n]["success"] and ai_rounds[n]["success"]]
    summary["paired_rounds"] = len(paired)
    summary["pool_wins"] = sum(1 for p, a in paired if p["client_wall_ms"] < a["client_wall_ms"])
    summary["aistudio_wins"] = sum(1 for p, a in paired if a["client_wall_ms"] < p["client_wall_ms"])
    summary["ties"] = sum(1 for p, a in paired if a["client_wall_ms"] == p["client_wall_ms"])
    after = data.get("after") or {}
    accounts = after.get("gemini_accounts") or []
    summary["gemini_enabled_accounts"] = sum(1 for a in accounts if a.get("status") == "enabled")
    summary["gemini_fail_count_total"] = sum(int(a.get("fail_count") or 0) for a in accounts)
    summary["gemini_5h_remaining_total"] = sum(int(a.get("quota_5h_remaining") or 0) for a in accounts)
    summary["gemini_5h_limit_total"] = sum(int(a.get("quota_5h_limit") or 0) for a in accounts)
    summary["gemini_weekly_remaining_total"] = sum(int(a.get("quota_weekly_remaining") or 0) for a in accounts)
    summary["gemini_weekly_limit_total"] = sum(int(a.get("quota_weekly_limit") or 0) for a in accounts)
    summary["aistudio_state"] = after.get("aistudio_state")
    summary["aistudio_ready_accounts"] = after.get("aistudio_accounts_ready")
    summary["errors"] = [x for x in data["tests"] if not x["success"]]
    with HISTORY_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    fields = [k for k in summary if k != "errors"]
    write_header = not HISTORY_CSV.exists() or HISTORY_CSV.stat().st_size == 0
    with HISTORY_CSV.open("a", newline="", encoding="utf-8-sig" if write_header else "utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if write_header:
            w.writeheader()
        w.writerow(summary)

def main():
    data = {
        "benchmark":"Gemini Cookie Pool vs AI Studio direct",
        "created_at":datetime.now().astimezone().isoformat(), "run_id":PREFIX,
        "base_url":BASE, "model":MODEL, "rounds_requested":ROUNDS, "prompt":PROMPT,
        "methodology":{"same_model_and_prompt_per_pair":True,"stream":False,
            "gemini_reasoning_level":"off","alternating_order":True,
            "minimum_gap_between_gemini_pool_requests_seconds":GEMINI_MIN_GAP_SECONDS,
            "client_wall_ms_includes_http_round_trip":True},
        "before":snapshot(), "tests":[]
    }
    last_gemini_end = None
    save_json(data)
    for round_no in range(1,ROUNDS+1):
        order = ["gemini_pool","aistudio"] if round_no%2 else ["aistudio","gemini_pool"]
        for route in order:
            if route=="gemini_pool" and last_gemini_end is not None:
                delay = GEMINI_MIN_GAP_SECONDS-(time.monotonic()-last_gemini_end)
                if delay>0: time.sleep(delay)
            endpoint = "/api/gemini/chat" if route=="gemini_pool" else "/api/aistudio/chat"
            payload = {"prompt":PROMPT,"model":MODEL,"stream":False,"timeout":TIMEOUT_SECONDS}
            if route=="gemini_pool": payload["reasoning_level"]="off"
            raw = request_json(endpoint,payload,timeout=TIMEOUT_SECONDS+15)
            if route=="gemini_pool": last_gemini_end=time.monotonic()
            item = {"round":round_no,"route":route,"endpoint":endpoint,
                "requested_model":MODEL,"tested_at":datetime.now().astimezone().isoformat(),
                "http_status":raw.get("http_status"),"client_wall_ms":raw.get("client_wall_ms"),
                **extract_result(raw)}
            data["tests"].append(item)
            save_json(data)
            print(json.dumps({k:item.get(k) for k in ("round","route","http_status","success",
                "client_wall_ms","provider_latency_ms","total_tokens","error")},ensure_ascii=False),flush=True)

    data["after"]=snapshot()
    save_json(data)
    fields=["round","route","requested_model","http_status","success","client_wall_ms",
        "provider_latency_ms","account_id","prompt_tokens","completion_tokens","total_tokens","reply","error"]
    with CSV_PATH.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for x in data["tests"]: w.writerow({k:x.get(k) for k in fields})

    lines=["# Gemini Cookie Pool vs AI Studio 直连对比测试","",
        "- 测试时间："+data["created_at"],"- 模型："+MODEL,
        "- 配对轮数："+str(ROUNDS),"- 每组使用完全相同的提示词",
        "- 非流式；Gemini 号池 reasoning_level=off",
        "- Gemini 号池请求之间至少间隔 12.5 秒","",
        "## 单次结果","","| 轮次 | 路线 | HTTP | 成功 | 客户端耗时(ms) | 服务端耗时(ms) | Tokens |",
        "|---:|---|---:|---|---:|---:|---:|"]
    for x in data["tests"]:
        lines.append("| {round} | {route} | {http_status} | {ok} | {wall} | {provider} | {tokens} |".format(
            round=x["round"],route=x["route"],http_status=x["http_status"],
            ok="是" if x["success"] else "否",wall=x["client_wall_ms"],
            provider=x["provider_latency_ms"] or "",tokens=x["total_tokens"] or ""))
    lines += ["","## 汇总",""]
    for route in ("gemini_pool","aistudio"):
        xs=[x for x in data["tests"] if x["route"]==route]
        good=[x for x in xs if x["success"] and isinstance(x["client_wall_ms"],int)]
        vals=[x["client_wall_ms"] for x in good]
        lines += ["### "+route,"- 成功：{}/{}".format(len(good),len(xs))]
        if vals:
            lines += ["- 平均客户端耗时：{:.0f} ms".format(statistics.mean(vals)),
                "- 中位数客户端耗时：{:.0f} ms".format(statistics.median(vals)),
                "- 最快/最慢：{} / {} ms".format(min(vals),max(vals))]
        lines.append("")
    pool_by_round={x["round"]:x for x in data["tests"] if x["route"]=="gemini_pool"}
    ai_by_round={x["round"]:x for x in data["tests"] if x["route"]=="aistudio"}
    lines += ["## 配对对照","","| 轮次 | Gemini Pool (ms) | AI Studio (ms) | 更快线路 |",
        "|---:|---:|---:|---|"]
    for rn in sorted(set(pool_by_round)&set(ai_by_round)):
        p,a=pool_by_round[rn],ai_by_round[rn]
        if p["success"] and a["success"]:
            faster="Gemini Pool" if p["client_wall_ms"]<a["client_wall_ms"] else "AI Studio"
            lines.append("| {} | {} | {} | {} |".format(rn,p["client_wall_ms"],a["client_wall_ms"],faster))
        else:
            lines.append("| {} | {} | {} | 至少一方失败 |".format(rn,p.get("client_wall_ms"),a.get("client_wall_ms")))
    gp=[x["client_wall_ms"] for x in data["tests"] if x["route"]=="gemini_pool" and x["success"] and isinstance(x.get("client_wall_ms"),int)]
    av=[x["client_wall_ms"] for x in data["tests"] if x["route"]=="aistudio" and x["success"] and isinstance(x.get("client_wall_ms"),int)]
    if gp and av:
        lines += ["","- 平均耗时差：AI Studio 相比 Gemini Pool {:+.0f} ms（负值代表 AI Studio 更快）。".format(statistics.mean(av)-statistics.mean(gp))]
    lines += ["","- 比较限制：Gemini Pool 本次使用 reasoning_level=off；AI Studio 专属接口没有暴露对应推理级别参数，按服务端默认配置执行。速度结果代表当前实际调用配置，不是完全等推理强度的纯基准。",""]
    lines += ["## 额度快照","","### Gemini Cookie 号池（本地额度计数）",
        "| 账号ID | 状态 | 5小时剩余 | 每周剩余 |","|---:|---|---:|---:|"]
    for a in data["after"].get("gemini_accounts",[]):
        lines.append("| {id} | {status} | {r5}/{l5} | {rw}/{lw} |".format(
            id=a["id"],status=a["status"],r5=a["quota_5h_remaining"],l5=a["quota_5h_limit"],
            rw=a["quota_weekly_remaining"],lw=a["quota_weekly_limit"]))
    lines += ["","### AI Studio",
        "- 运行状态："+str(data["after"].get("aistudio_state")),
        "- 就绪账号：{}/{}".format(data["after"].get("aistudio_accounts_ready"),data["after"].get("aistudio_accounts_total")),
        "- 权益等级："+str(data["after"].get("aistudio_benefit_tier")),
        "- 数值剩余额度：接口未提供，不能据此推算。","",
        "## 注意事项",
        "- 客户端耗时包含本地 HTTP 往返；服务端耗时使用接口提供的上游延迟字段。",
        "- 5 组顺序配对，不是并发压测。",
        "- 失败请求也保留；失败请求不计入成功耗时平均值。","",
        "## 文件","- 完整 JSON："+JSON_PATH.name,"- CSV："+CSV_PATH.name,
        "- Markdown："+MD_PATH.name,"- 可复用脚本：scripts/compare_gemini_routes.py"]
    MD_PATH.write_text("\n".join(lines)+"\n",encoding="utf-8")
    append_history(data)
    print(json.dumps({"done":True,"json":str(JSON_PATH),"csv":str(CSV_PATH),
        "markdown":str(MD_PATH),"tests":len(data["tests"]),"before":data["before"],
        "after":data["after"]},ensure_ascii=False),flush=True)

if __name__=="__main__": main()

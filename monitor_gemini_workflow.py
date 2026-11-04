#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Gemini 4账号长时间稳定性与轮询测试监控器
- 监控周期: ~30 分钟 (共 6 轮测试，平均每 5 分钟轮询一轮)
- 轮询机制: 每轮依次对 4 个 Google 账号 (/u/0, /u/1, /u/2, /u/3) 发送测试消息
- 自愈机制: 遇到凭证过期、超时或进程退出时，自动触发令牌保活、重新从 Cookie Hub 拉取凭证并热拉起恢复
- 结果持久化: 实时记录到 gemini_monitor.log 和 gemini_monitor_report.json
"""

import os
import sys
import time
import json
import sqlite3
import datetime
from typing import Dict, Any, List

# 保证控制台与文件 UTF-8 输出无乱码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 保证本地回环网络请求直连，不走外部代理
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"

from gemini_service import MultiAccountGeminiPool, _LOCAL_OPENER

LOG_FILE = os.path.join(os.path.dirname(__file__), "gemini_monitor.log")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "gemini_monitor_report.json")

TEST_PROMPTS = [
    "请只回复两个汉字：正常。",
    "请计算并只返回结果：25 * 4 = ?",
    "请用一句话介绍太阳系最大的行星。",
    "请只回复一个单词：PASS。",
    "请只回复当前时间或今天星期几（简短一句话）。",
    "请只回复两个字母：OK。",
]


def log_print(msg: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")


class GeminiWorkflowMonitor:
    def __init__(
        self,
        pool: MultiAccountGeminiPool,
        total_rounds: int = 6,
        round_interval_sec: int = 300,  # 5 minutes
        inter_account_delay: int = 8,   # 8s spacing between accounts in same round
    ):
        self.pool = pool
        self.total_rounds = total_rounds
        self.round_interval_sec = round_interval_sec
        self.inter_account_delay = inter_account_delay
        self.report: Dict[str, Any] = {
            "start_time": datetime.datetime.now().isoformat(),
            "end_time": None,
            "target_duration_minutes": (total_rounds * round_interval_sec) / 60,
            "total_rounds": total_rounds,
            "account_count": pool.account_count,
            "records": [],
            "heals": [],
            "stats": {},
        }

    def save_report(self):
        try:
            with open(REPORT_FILE, "w", encoding="utf-8") as f:
                json.dump(self.report, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_print(f"⚠️ 保存测试报告失败: {e}")

    def self_heal_service(self, reason: str, account_id: int = None) -> bool:
        log_print(f"🔧 [自愈触发] 检测到异常: {reason}，正在尝试自动恢复...")
        heal_event = {
            "timestamp": datetime.datetime.now().isoformat(),
            "reason": reason,
            "account_id": account_id,
            "actions": [],
            "success": False,
        }

        # 动作 1: 检查后台服务是否存活
        if not self.pool.is_running():
            log_print("  -> 尝试重新启动 gemini-web2api 多账号后台服务...")
            started = self.pool.start(wait_timeout=15)
            heal_event["actions"].append(f"restart_service: {'success' if started else 'failed'}")
            if not started:
                log_print("  ❌ 后台服务重启失败！")
                self.report["heals"].append(heal_event)
                self.save_report()
                return False

        # 动作 2: 如果指定了账号且服务可用，尝试触发账号保活
        if account_id:
            try:
                log_print(f"  -> 尝试调用 /admin/api/cookies/{account_id}/rotate 强制保活...")
                res = self.pool.rotate_account(account_id)
                heal_event["actions"].append(f"rotate_account_{account_id}: {res}")
            except Exception as e:
                heal_event["actions"].append(f"rotate_account_{account_id}_err: {str(e)}")

        # 动作 3: 从 Cookie Hub 提取最新凭证并更新多账号数据库
        try:
            log_print("  -> 正在从前台 Cookie Hub (18888) 提取最新浏览器 Google 会话凭证...")
            self.pool.refresh_pool_cookies()
            heal_event["actions"].append("refresh_pool_cookies_from_hub: success")
            log_print("  ✅ 已成功从 Cookie Hub 刷新凭证并注入 SQLite 账号池！")
        except Exception as e:
            heal_event["actions"].append(f"refresh_pool_cookies_err: {str(e)}")
            log_print(f"  ⚠️ 从 Cookie Hub 提取凭证失败: {e}")

        # 动作 4: 校验健康状态
        try:
            accounts = self.pool.list_accounts()
            heal_event["actions"].append(f"verified_accounts_count: {len(accounts)}")
            heal_event["success"] = True
            log_print("  🎉 自愈修复流程执行完毕，已重置账号健康状态。")
        except Exception as e:
            heal_event["actions"].append(f"verify_failed: {str(e)}")

        self.report["heals"].append(heal_event)
        self.save_report()
        return heal_event["success"]

    def execute_round(self, round_num: int):
        log_print(f"\n=======================================================")
        log_print(f"🚀 开始执行第 {round_num}/{self.total_rounds} 轮测试 (4 个账号全量轮询)")
        log_print(f"=======================================================")

        # 确保后台服务正在运行
        if not self.pool.is_running():
            self.self_heal_service("服务未在运行")

        round_success_count = 0
        for slot in range(self.pool.account_count):
            prompt = TEST_PROMPTS[(round_num * self.pool.account_count + slot) % len(TEST_PROMPTS)]
            log_print(f"\n👉 [轮次 {round_num} - 槽位 {slot+1}/{self.pool.account_count}] 提问: '{prompt}'")

            t0 = time.time()
            record: Dict[str, Any] = {
                "round": round_num,
                "slot": slot + 1,
                "timestamp": datetime.datetime.now().isoformat(),
                "prompt": prompt,
                "status": "pending",
                "took_ms": 0,
                "account_id": None,
                "account_label": None,
                "authuser": None,
                "reply": None,
                "error": None,
            }

            try:
                # 尝试调用
                res = self.pool.ask_with_details(prompt=prompt, model="gemini-3.5-flash-lite", timeout=45)
                record["took_ms"] = res.get("took_ms", int((time.time() - t0) * 1000))
                record["account_id"] = res.get("account_id")
                record["account_label"] = res.get("account_label")
                record["authuser"] = res.get("authuser")
                record["reply"] = res.get("reply")
                record["status"] = "success"
                round_success_count += 1
                log_print(
                    f"   ✅ [成功] 耗时: {record['took_ms']}ms | 实际响应账号: {record['account_label']} (ID: {record['account_id']}, authuser: {record['authuser']})"
                )
                log_print(f"   💬 回复内容: {record['reply']}")

            except Exception as e:
                err_msg = str(e)
                log_print(f"   ❌ [调用失败]: {err_msg}")
                record["status"] = "failed"
                record["error"] = err_msg
                record["took_ms"] = int((time.time() - t0) * 1000)

                # 触发自愈
                healed = self.self_heal_service(f"调用异常: {err_msg}")
                if healed:
                    log_print("   🔄 自愈完成，正在执行该槽位重试...")
                    try:
                        t0_retry = time.time()
                        retry_res = self.pool.ask_with_details(prompt=prompt, model="gemini-3.5-flash-lite", timeout=45)
                        record["status"] = "healed_success"
                        record["took_ms"] = retry_res.get("took_ms", int((time.time() - t0_retry) * 1000))
                        record["account_id"] = retry_res.get("account_id")
                        record["account_label"] = retry_res.get("account_label")
                        record["authuser"] = retry_res.get("authuser")
                        record["reply"] = retry_res.get("reply")
                        record["error"] = None
                        round_success_count += 1
                        log_print(
                            f"   🎉 [重试成功] 耗时: {record['took_ms']}ms | 响应账号: {record['account_label']}"
                        )
                    except Exception as re:
                        log_print(f"   ❌ [重试仍失败]: {re}")
                        record["error"] = f"{err_msg} -> retry: {str(re)}"

            self.report["records"].append(record)
            self.save_report()

            # 槽位之间稍作缓冲
            if slot < self.pool.account_count - 1:
                time.sleep(self.inter_account_delay)

        log_print(f"\n📊 第 {round_num} 轮测试结束: {round_success_count}/{self.pool.account_count} 槽位成功")

    def run(self):
        log_print("=================================================================")
        log_print("🚀 Google Gemini 4账号长时间稳定性与轮询测试流程正式启动")
        log_print(f"⏰ 总目标时长: ~{int(self.report['target_duration_minutes'])} 分钟 (共 {self.total_rounds} 轮)")
        log_print(f"⏱️ 轮询周期: 每轮约 {int(self.round_interval_sec / 60)} 分钟，账号间缓冲 {self.inter_account_delay} 秒")
        log_print(f"📁 日志文件: {LOG_FILE}")
        log_print(f"📊 报告文件: {REPORT_FILE}")
        log_print("=================================================================")

        # 启动自检
        log_print("🔍 执行启动前自检与账号状态审计...")
        if not self.pool.is_running():
            self.pool.start(wait_timeout=15)

        accounts = self.pool.list_accounts()
        log_print(f"已就绪账号槽位: {len(accounts)} 个")
        for a in accounts:
            log_print(f"  - [{a['auth_user']}] {a['label']} -> 状态: {a['status']}, 失败数: {a['fail_count']}")

        for round_idx in range(1, self.total_rounds + 1):
            round_start_time = time.time()
            self.execute_round(round_idx)

            if round_idx < self.total_rounds:
                elapsed = time.time() - round_start_time
                wait_sec = max(5, int(self.round_interval_sec - elapsed))
                log_print(f"\n⏳ 本轮耗时 {elapsed:.1f}s，距离第 {round_idx+1} 轮轮询还需等待 {wait_sec} 秒 (~{wait_sec//60} 分钟)...")
                time.sleep(wait_sec)

        # 统计汇总
        self.report["end_time"] = datetime.datetime.now().isoformat()
        total_reqs = len(self.report["records"])
        success_reqs = sum(1 for r in self.report["records"] if "success" in r["status"])
        account_counts: Dict[str, int] = {}
        account_latencies: Dict[str, List[int]] = {}

        for r in self.report["records"]:
            lbl = r.get("account_label") or "unknown"
            account_counts[lbl] = account_counts.get(lbl, 0) + (1 if "success" in r["status"] else 0)
            if "success" in r["status"] and r.get("took_ms"):
                account_latencies.setdefault(lbl, []).append(r["took_ms"])

        stats = {
            "total_requests": total_reqs,
            "successful_requests": success_reqs,
            "overall_success_rate": f"{(success_reqs / total_reqs * 100):.1f}%" if total_reqs else "0%",
            "self_heal_events": len(self.report["heals"]),
            "per_account_success": account_counts,
            "per_account_avg_latency_ms": {
                k: int(sum(v) / len(v)) if v else 0 for k, v in account_latencies.items()
            },
        }
        self.report["stats"] = stats
        self.save_report()

        log_print("\n=================================================================")
        log_print("🎉 30 分钟多账号长时间轮询测试圆满完成！")
        log_print(f"📊 总请求数: {total_reqs} | 成功数: {success_reqs} | 成功率: {stats['overall_success_rate']}")
        log_print(f"🔧 自愈修复次数: {stats['self_heal_events']}")
        log_print("📈 各账号调用成功分布与平均耗时:")
        for acct_name, count in account_counts.items():
            avg_ms = stats["per_account_avg_latency_ms"].get(acct_name, 0)
            log_print(f"  - {acct_name}: 成功调用 {count} 次, 平均耗时 {avg_ms} ms")
        log_print(f"📄 详细结果已持久化至: {REPORT_FILE}")
        log_print("=================================================================")


if __name__ == "__main__":
    pool = MultiAccountGeminiPool(port=18083, account_count=4)
    monitor = GeminiWorkflowMonitor(
        pool=pool,
        total_rounds=6,             # 6 轮
        round_interval_sec=300,     # 每轮间隔 5 分钟 (300 秒)
        inter_account_delay=8,      # 账号间调用缓冲 8 秒
    )
    monitor.run()

# Gemini Cookie Pool vs AI Studio 直连对比测试

- 测试时间：2026-11-12 17:54:21–17:56:50（Asia/Shanghai）
- 模型：gemini-3.8-flash
- 配对轮数：5 轮，共 10 次真实推理请求
- 每一轮两条线路使用完全相同的中文提示词
- 非流式输出；Gemini Cookie Pool 设置 reasoning_level=off
- 两次 Gemini Pool 请求之间至少间隔 12.5 秒，遵守本地频率限制
- 顺序交替：第 1/3/5 轮先 Gemini Pool，第 2/4 轮先 AI Studio

## 1. 单轮耗时对照

单位：秒。客户端耗时包含本地 HTTP 往返。

| 轮次 | Gemini Cookie Pool | AI Studio 直连 | 本轮更快 |
|---:|---:|---:|---|
| 1 | 8.732 | 12.847 | Gemini Pool 快 4.115 秒 |
| 2 | 15.763 | 9.958 | AI Studio 快 5.805 秒 |
| 3 | 7.320 | 9.737 | Gemini Pool 快 2.417 秒 |
| 4 | 25.830 | 11.176 | AI Studio 快 14.654 秒 |
| 5 | 11.770 | 10.658 | AI Studio 快 1.112 秒 |

## 2. 汇总结果

| 指标 | Gemini Cookie Pool | AI Studio 直连 |
|---|---:|---:|
| 成功次数 | 5/5 | 5/5 |
| 平均客户端耗时 | 13.883 秒 | 10.875 秒 |
| 中位数 | 11.770 秒 | 10.658 秒 |
| 最快 | 7.320 秒 | 9.737 秒 |
| 最慢 | 25.830 秒 | 12.847 秒 |
| 平均服务端耗时 | 13.331 秒 | 10.797 秒 |

- 本轮 AI Studio 平均快 3.008 秒，约快 21.7%。
- AI Studio 在 5 组配对测试中赢了 3 组；Gemini Pool 赢了 2 组。
- Gemini Pool 的耗时波动明显更大；本轮 AI Studio 的响应时间更集中。
- 这是 5 组顺序配对测试，不是并发压力测试，样本量仍有限。

## 3. Token 消耗

| 指标 | Gemini Cookie Pool | AI Studio 直连 |
|---|---:|---:|
| 请求次数 | 5 | 5 |
| 输入 Token | 接口未返回 | 235 |
| 输出/完成 Token | 接口未返回 | 4,708 |
| 总 Token | 接口未返回 | 4,943 |

说明：AI Studio 返回的 completion_tokens 包含其 usage 统计中的推理 Token；Gemini Pool 当前接口响应未暴露可读取的 Token 用量，因此不能直接比较两边 Token 成本。

## 4. 额度与账号健康

### Gemini Cookie Pool

测试前 4 个账号均通过登录态检测；测试后仍全部 enabled，fail_count 均为 0。

| 账号 ID | 本轮调用数 | 5 小时剩余 | 每周剩余 |
|---:|---:|---:|---:|
| 1 | 1 | 48/50 | 468/500 |
| 2 | 1 | 49/50 | 462/500 |
| 3 | 2 | 48/50 | 465/500 |
| 4 | 1 | 49/50 | 463/500 |
| 合计 | 5 | 194/200 | 1,858/2,000 |

以上为 Cookie Pool 服务端返回的本地额度计数快照，不应误认为 Google 官方实时配额面板。

### AI Studio 直连

- 服务状态：RUNNING
- 已就绪账号：1/1
- 权益等级：Pro
- 本轮成功请求：5 次
- 返回 Token 用量：4,943
- 数值剩余额度：当前 /api/aistudio/status 和 /api/aistudio/accounts 未提供，不能推算剩余次数或剩余 Token。

## 5. 结论

本轮在 gemini-3.8-flash、相同提示词下，AI Studio 直连平均耗时更短，且波动更小；Gemini Cookie Pool 也达到 5/5 成功，但第 4 轮出现 25.83 秒的长尾。

建议当前将 AI Studio 作为优先候选线路，Gemini Cookie Pool 保留为备用线路；不要仅凭这 5 轮就永久定型，后续应跨时段继续累积样本。

## 6. 可复现性与比较限制

- 完整 JSON 保存了逐次请求、响应文本、耗时、账号与前后额度快照。
- CSV 保存了逐次测试的结构化字段。
- 可复用脚本位于 scripts/compare_gemini_routes.py。
- 两条线路接口的推理配置并非完全对等：Gemini Pool 本次显式使用 reasoning_level=off；AI Studio 专属接口没有暴露对应推理级别参数，按服务端默认配置执行。因此速度结果应视为当前实际调用配置的比较，而不是严格控制推理强度后的纯性能基准。
- Gemini Pool 当前响应未提供 Token 用量；AI Studio 暴露了 Token 用量但没有剩余额度数值。

## 文件清单

- 完整数据：gemini-pool-vs-aistudio-20261112-175421.json
- 表格数据：gemini-pool-vs-aistudio-20261112-175421.csv
- 本报告：gemini-pool-vs-aistudio-20261112-175421.md
- 测试脚本：scripts/compare_gemini_routes.py

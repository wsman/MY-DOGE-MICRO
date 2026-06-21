---
name: anomaly
description: 查询成交量异常股票（量比排名，发现放量异动）。Use when the user asks for volume spikes, unusual activity, or volume anomalies.
argument-hint: "[--min-ratio N] [--top N]"
allowed-tools: Bash(doge anomaly *)
---

## User Guide

- When to use: Use `/anomaly` when the operator wants a ranked view of unusual
  volume activity, volume ratio spikes, or possible accumulation/distribution
  candidates.
- Inputs: Optional `--min-ratio N` and `--top N` arguments.
- Outputs: Volume anomaly table plus a brief interpretation of whether the
  anomalies are broad-based, clustered, or concentrated.
- Memory-bank writes: None.
- Next steps: Suggested follow-up commands are advisory only and must not
  auto-run.

查询成交量异常股票。

运行以下命令并将结果展示给用户：

```bash
doge anomaly $ARGUMENTS
```

**参数说明：**
- `--min-ratio N` 最低量比阈值（默认 3.0，越大越严格）
- `--top N` 返回数量（默认 20）

**输出包含：**
- 股票代码、日期、成交量、20日均量、量比、日内涨跌幅

展示结果后，简要分析异动特征（放量大涨/放量下跌、是否集中出现、值得关注的标的）。

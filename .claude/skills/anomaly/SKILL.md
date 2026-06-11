---
name: anomaly
description: 查询成交量异常股票（量比排名，发现放量异动）。Use when the user asks for volume spikes, unusual activity, or volume anomalies.
argument-hint: "[--min-ratio N] [--top N]"
allowed-tools: Bash(python src/cli.py anomaly *)
---

查询成交量异常股票。

运行以下命令并将结果展示给用户：

```bash
python src/cli.py anomaly $ARGUMENTS
```

**参数说明：**
- `--min-ratio N` 最低量比阈值（默认 3.0，越大越严格）
- `--top N` 返回数量（默认 20）

**输出包含：**
- 股票代码、日期、成交量、20日均量、量比、日内涨跌幅

展示结果后，简要分析异动特征（放量大涨/放量下跌、是否集中出现、值得关注的标的）。

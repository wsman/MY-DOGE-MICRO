---
name: rsrs
description: 查询 RSRS 动量排名（A 股/美股最强趋势股票排行）。Use when the user asks for momentum ranking, strongest stocks, or top movers.
argument-hint: "[--market cn|us] [--top N]"
allowed-tools: Bash(python src/cli.py rsrs *)
---

查询 RSRS 动量排名。

运行以下命令并将结果展示给用户：

```bash
python src/cli.py rsrs $ARGUMENTS
```

**参数说明：**
- `--market cn` 或 `--market us` 指定市场（默认 cn）
- `--top N` 指定排名数量（默认 20）

**输出包含：**
- 排名、股票代码、RSRS 分数（越接近 1 趋势越强）、20日均量、最新价、20日涨跌幅

展示结果后，简要解读 Top 排名的整体特征（强势板块、极端值、值得关注标的）。

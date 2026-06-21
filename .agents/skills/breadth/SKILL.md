---
name: breadth
description: 查询市场宽度（每日涨跌家数、上涨占比、平均涨跌幅）。Use when the user asks about market sentiment, breadth, or advance/decline ratio.
argument-hint: "[--market cn|us] [--days N]"
allowed-tools: Bash(doge breadth *)
---

## User Guide

- When to use: Use `/breadth` when the operator asks about market participation,
  advance/decline balance, sentiment breadth, or whether a move is broad or
  narrow.
- Inputs: Optional `--market cn|us` and `--days N` arguments.
- Outputs: Market breadth table plus a brief summary of breadth direction and
  any divergence.
- Memory-bank writes: None.
- Next steps: Suggested follow-up commands are advisory only and must not
  auto-run.

查询市场宽度数据。

运行以下命令并将结果展示给用户：

```bash
doge breadth $ARGUMENTS
```

**参数说明：**
- `--market cn` 或 `--market us` 指定市场（默认 cn）
- `--days N` 指定查询天数（默认 10）

**输出包含：**
- 日期、上涨家数、下跌家数、平盘家数、活跃股票数、平均涨跌幅、标准差、上涨占比

展示结果后，简要分析近期市场情绪（偏多/偏空/分化）和趋势变化。

---
name: stock
description: 查询个股行情数据（OHLCV、均线、ATR、波动率等技术指标）。Use when the user asks about a specific stock's price, indicators, or recent performance.
argument-hint: "<ticker> [--market cn|us] [--days N]"
arguments: [ticker]
allowed-tools: Bash(doge stock *)
---

## User Guide

- When to use: Use `/stock` when the operator asks for one ticker's recent
  OHLCV data, technical indicators, trend state, or short-term context.
- Inputs: Required ticker plus optional `--market cn|us` and `--days N`
  arguments.
- Outputs: OHLCV/indicator rows plus a brief interpretation of trend,
  volatility, and notable support or pressure context.
- Memory-bank writes: None.
- Next steps: Suggested follow-up commands are advisory only and must not
  auto-run.

查询股票 `$ticker` 的行情数据。

运行以下命令并将结果展示给用户：

```bash
doge stock $ARGUMENTS
```

**参数说明：**
- 第一个参数是股票代码（必填），如 `301599.SZ`、`600809.SH`、`AAPL`
- `--market cn` 或 `--market us` 指定市场（默认 cn）
- `--days N` 指定查询天数（默认 20）

**输出包含：**
- A 股：日期、OHLCV、涨跌幅、MA5/10/20/60、ATR14、MA60偏离度、20日波动率
- 美股：日期、OHLCV、成交量、成交额

展示结果后，简要分析该股近期走势特征（趋势方向、支撑/压力位、波动状态）。

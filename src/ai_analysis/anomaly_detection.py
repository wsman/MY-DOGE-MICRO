"""Deprecated anomaly-detection module — forwards to ``GenerateAnomalyReportUseCase``.

``src/ai_analysis/anomaly_detection.py`` is kept as a backwards-compatible shim
for Sprint 007. The canonical implementation now lives in
``doge.application.use_cases.generate_anomaly_report``. This module re-exports
``generate()`` so existing scripts and tests keep working. It will be removed in
Sprint 008.
"""
import argparse
import warnings

warnings.warn(
    "ai_analysis.anomaly_detection is deprecated; use "
    "doge.application.use_cases.generate_anomaly_report instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.application.composition import build_generate_anomaly_report_use_case
from doge.application.contracts.request import GenerateAnomalyReportRequest


def generate(min_ratio=3.0, gap_threshold=5.0, recent_days=3):
    """生成异常检测报告"""
    uc = build_generate_anomaly_report_use_case()
    resp = uc.execute(
        GenerateAnomalyReportRequest(
            min_ratio=min_ratio,
            gap_threshold=gap_threshold,
            recent_days=recent_days,
        )
    )
    return resp.markdown


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="异常检测")
    parser.add_argument("--min-ratio", type=float, default=3.0, help="量比阈值 (default: 3.0)")
    parser.add_argument("--gap-threshold", type=float, default=5.0, help="跳空百分比阈值")
    parser.add_argument("--days", type=int, default=3, help="最近 N 天 (default: 3)")
    args = parser.parse_args()
    generate(args.min_ratio, args.gap_threshold, args.days)

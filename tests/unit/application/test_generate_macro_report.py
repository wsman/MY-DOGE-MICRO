import pandas as pd
import pytest

from doge.application.contracts.request import GenerateMacroReportRequest
from doge.application.use_cases.generate_macro_report import GenerateMacroReportUseCase


class FakeViewRepo:
    def __init__(self, frames=None, fail=False):
        self.frames = list(frames or [])
        self.fail = fail
        self.queries = []

    def execute(self, sql, params=None):
        self.queries.append((sql, params))
        if self.fail:
            raise RuntimeError("view unavailable")
        if self.frames:
            return self.frames.pop(0)
        return pd.DataFrame()


class FakeLLM:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def chat(self, system_prompt, user_prompt, *, max_tokens=4096, temperature=0.7):
        self.calls.append({
            "system": system_prompt,
            "user": user_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        return self.content


class FakeReportRepo:
    def __init__(self):
        self.saved = []

    def save_macro_report(self, **kwargs):
        self.saved.append(kwargs)


def _use_case(*, llm_content, frames=None, fail=False):
    report_repo = FakeReportRepo()
    llm = FakeLLM(llm_content)
    use_case = GenerateMacroReportUseCase(FakeViewRepo(frames, fail=fail), llm, report_repo)
    return use_case, llm, report_repo


def test_execute_generates_and_persists_report():
    frames = [
        pd.DataFrame([{"date": "2026-06-19", "advance_ratio": 0.62}]),
        pd.DataFrame([{"rank": 1, "ticker": "000001.SZ", "rsrs": 0.8}]),
        pd.DataFrame([{"ticker": "000002.SZ", "vol_ratio": 3.2}]),
    ]
    use_case, llm, report_repo = _use_case(
        llm_content="Risk-on posture. Volatility: high. [数据: advance_ratio 0.62]",
        frames=frames,
    )

    response = use_case.execute(GenerateMacroReportRequest(market="cn"))

    assert response.error is None
    assert response.risk_signal == "risk-on"
    assert response.volatility == "high"
    assert response.report_id is None
    assert report_repo.saved[0]["content"] == response.content
    assert report_repo.saved[0]["risk_signal"] == "risk-on"
    assert "[数据:" in llm.calls[0]["system"]
    assert "vw_volume_anomalies_cn" in llm.calls[0]["user"]


def test_execute_degrades_when_llm_unavailable_and_does_not_persist():
    use_case, _llm, report_repo = _use_case(llm_content=None)

    response = use_case.execute(GenerateMacroReportRequest())

    assert response.error == "LLM unavailable"
    assert response.analyst == "deepseek-chat"
    assert report_repo.saved == []


def test_execute_handles_empty_or_unavailable_views():
    use_case, llm, report_repo = _use_case(
        llm_content="Neutral. Volatility: low.",
        fail=True,
    )

    response = use_case.execute(GenerateMacroReportRequest(market="cn"))

    assert response.error is None
    assert "No data available" in llm.calls[0]["user"]
    assert len(report_repo.saved) == 1


def test_execute_skips_us_volume_anomalies_view():
    frames = [
        pd.DataFrame([{"date": "2026-06-19", "active": 10}]),
        pd.DataFrame([{"rank": 1, "ticker": "AAPL", "rsrs": 0.2}]),
    ]
    use_case, llm, _report_repo = _use_case(llm_content="Neutral. Volatility: medium.", frames=frames)

    response = use_case.execute(GenerateMacroReportRequest(market="us"))

    assert response.volatility == "medium"
    assert "US volume anomaly data is unavailable" in llm.calls[0]["user"]
    assert "vw_volume_anomalies_us" not in llm.calls[0]["user"]


def test_execute_rejects_unknown_market():
    use_case, _llm, _report_repo = _use_case(llm_content="unused")

    with pytest.raises(ValueError):
        use_case.execute(GenerateMacroReportRequest(market="hk"))

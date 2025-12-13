"""
MY-DOGE 宏观战略分析包

一个基于 DeepSeek API 的量化宏观对冲策略工具，用于分析全球市场资金流向和制定投资决策。
"""

__version__ = "1.0.0"
__author__ = "MY-DOGE Team"
__email__ = "contact@example.com"

from .config import MacroConfig
from .data_loader import GlobalMacroLoader
from .strategist import DeepSeekStrategist
from .utils import setup_logging

__all__ = [
    "MacroConfig",
    "GlobalMacroLoader", 
    "DeepSeekStrategist",
    "setup_logging"
]

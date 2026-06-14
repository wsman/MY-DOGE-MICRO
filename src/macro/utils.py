"""
工具模块

包含日志配置和其他工具函数
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


def _safe_print(text: str) -> None:
    """Print *text* to stdout, falling back on encoding errors."""
    try:
        sys.stdout.buffer.write(text.encode("utf-8", "replace") + b"\n")
        return
    except Exception:
        pass
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            encoded = text.encode(sys.stdout.encoding or "utf-8", "replace")
            sys.stdout.buffer.write(encoded + b"\n")
        except Exception:  # pragma: no cover - last-resort fallback
            print(text.encode("ascii", "ignore").decode("ascii"))


class _SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that writes bytes to avoid Windows GBK encoding errors."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            stream = self.stream
            if hasattr(stream, "buffer"):
                stream.buffer.write((msg + self.terminator).encode("utf-8", "replace"))
            else:
                stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def setup_logging(
    log_level: int = logging.DEBUG,
    log_file: str = "logs/app.log",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    配置日志系统

    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        max_file_size: 单个日志文件最大大小
        backup_count: 备份文件数量
    """
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
        _safe_print(f"📁 创建日志目录: {log_dir}")

    # 创建根日志记录器
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # 清除现有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 创建格式化器
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台处理器（字节写入，兼容 GBK 控制台）
    console_handler = _SafeStreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（轮转日志）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # 文件记录更详细的日志
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info("✅ 日志系统初始化完成 - 控制台级别: %s, 文件级别: DEBUG", logging.getLevelName(log_level))


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    return logging.getLogger(name)


def validate_api_key(api_key: Optional[str]) -> bool:
    """
    验证 API Key 格式
    
    Args:
        api_key: 要验证的 API Key
        
    Returns:
        bool: 是否有效
    """
    if not api_key:
        return False
    
    # 基本的 API Key 格式验证
    if len(api_key) < 10:
        return False
        
    # 可以添加更多验证逻辑
    return True


def format_percentage(value: float) -> str:
    """
    格式化百分比数值
    
    Args:
        value: 原始数值
        
    Returns:
        str: 格式化后的百分比字符串
    """
    return f"{value:.2%}"


def format_currency(value: float) -> str:
    """
    格式化货币数值
    
    Args:
        value: 原始数值
        
    Returns:
        str: 格式化后的货币字符串
    """
    return f"${value:.2f}"

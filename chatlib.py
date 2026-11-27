#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chatlib —— 聊天机器人的共享逻辑。

包含四件事，全部不打印内容、不解析命令行参数：
    - 计费：PRICE / get_usage_field() / cost()
    - 历史管理：trim()
    - 错误分类：ChatError 及 6 个子类 / classify_error() / call_with_retry()
    - 初始化：load_system_prompt() / make_client()

命令行交互在 chat_cli.py，本模块可被其他脚本直接 import 复用。
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# 来源：DeepSeek 官网定价页，查询日期 2026-11-26
# 单位：元 / 百万 token
PRICE = {
    "in": 1.0,
    "in_cached": 0.02,
    "out": 4.0,
}

MAX_MESSAGES = 12          # 含 system 的总条数上限
KEEP_RECENT = 8            # 截断时保留最近几条

DEFAULT_SYSTEM = "你是一个简洁的助手，回答不超过三句话。"
DEFAULT_SYSTEM_FILE = ROOT / "system_prompt.md"

# ============================================================ 一、计费
def get_usage_field(usage, name: str, default: int = 0) -> int:
    """从对象或 dict 里取值，拿不到（或为 None）就返回默认值。"""
    if usage is None:
        return default
    if isinstance(usage, dict):
        value = usage.get(name, default)
    else:
        value = getattr(usage, name, default)
    if value is None:
        return default
    return int(value)


def cost(usage) -> float:
    """按 usage 算本次费用（元）。

    Args:
        usage: openai 返回的 CompletionUsage 对象，也可以是 dict。

    Returns:
        本次调用费用，单位元。

    Raises:
        不抛异常：缺字段时按 0 处理。
    """
    prompt = get_usage_field(usage, "prompt_tokens")
    completion = get_usage_field(usage, "completion_tokens")
    cached = get_usage_field(usage, "prompt_cache_hit_tokens")
    # prompt_tokens 是总数，已包含缓存命中部分
    uncached = max(prompt - cached, 0)

    return (
        uncached / 1_000_000 * PRICE["in"]
        + cached / 1_000_000 * PRICE["in_cached"]
        + completion / 1_000_000 * PRICE["out"]
    )

# ---------- system prompt ----------
def load_system_prompt(explicit: Path | None) -> str:
    """读取 system prompt。

    Args:
        explicit: 显式传的路径（命令行 --system）。为 None 时走默认逻辑。

    Returns:
        system prompt 文本。

    Raises:
        SystemExit: 退出码 2（用法错误）。
            - explicit 指定了但文件不存在
            - 读文件时出现 OSError（权限/编码等）
    """
    if explicit is not None:
        if not explicit.is_file():
            # 退出码 2 = 用法错误，和 argparse 保持一致
            print(f"错误：--system 指定的文件不存在：{explicit}", file=sys.stderr)
            raise SystemExit(2)
        try:
            return explicit.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"错误：读取 {explicit} 失败：{e}", file=sys.stderr)
            raise SystemExit(2) from e

    if DEFAULT_SYSTEM_FILE.is_file():
        try:
            return DEFAULT_SYSTEM_FILE.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"警告：读取 {DEFAULT_SYSTEM_FILE} 失败，改用内置默认：{e}",
                  file=sys.stderr)
            return DEFAULT_SYSTEM
    return DEFAULT_SYSTEM


# ============================================================ 二、历史管理
def trim(
    messages: list[dict[str, str]],
    max_messages: int = MAX_MESSAGES,
    keep_recent: int = KEEP_RECENT,
) -> list[dict[str, str]]:
    """保留 system + 最近若干条，返回新列表（不改动入参）。

    规则：
      - 不超过 max_messages 时原样返回副本
      - system 永远保留
      - keep_recent 会被夹到 max_messages - 1 以内，保证结果一定 <= max_messages
        （否则 max_messages=8、keep_recent=8 时会得到 1+8=9 条，越截越多）
      - 若截断后第一条是 assistant（孤儿回复），再丢掉它

    Args:
        messages: 完整消息列表，第 0 条通常是 system。
        max_messages: 截断后允许的最大条数（含 system）。
        keep_recent: 想保留的最近条数，会被上限约束。

    Returns:
        截断后的新列表。

    Raises:
        ValueError: max_messages < 2 时（无法同时容纳 system 和一条对话）。
    """
    if max_messages < 2:
        raise ValueError("max_messages 至少为 2（1 条 system + 1 条对话）")

    if len(messages) <= max_messages:
        return list(messages)

    # 关键：system 占 1 条，所以最近对话最多只能留 max_messages - 1 条
    keep = min(keep_recent, max_messages - 1)

    head = messages[:1]                     # system
    tail = messages[1:][-keep:]             # 最近 keep 条
    if tail and tail[0].get("role") == "assistant":
        tail = tail[1:]
    return head + tail


# ============================================================ 三、异常树（复用第 2 周的分类思路）
#
# openai SDK 实际层次（3.26.0 实测）：
#   OpenAIError
#   ├── APIError
#   │   ├── APIStatusError        ← 带 .status_code
#   │   │   ├── BadRequestError          400
#   │   │   ├── AuthenticationError      401
#   │   │   ├── PermissionDeniedError    403
#   │   │   ├── NotFoundError            404
#   │   │   ├── UnprocessableEntityError 422
#   │   │   ├── RateLimitError           429
#   │   │   └── InternalServerError      500
#   │   ├── APIConnectionError
#   │   │   └── APITimeoutError
#   │   └── APIResponseValidationError
#   └── LengthFinishReasonError / ContentFilterFinishReasonError
#
# 本模块把它们翻译成 6 个"业务语义"明确的类，每个自带退出码与可重试标记。


class ChatError(Exception):
    """本模块所有错误的基类。

    Attributes:
        message: 给人看的一句话。
        exit_code: 建议的进程退出码。
        retryable: 重试是否可能成功。
        retry_after: 服务端建议的等待秒数（来自 Retry-After 头），没有则 None。
    """

    exit_code: int = 1
    retryable: bool = False

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


class ConfigError(ChatError):
    """配置/用法错误：key 缺失、模型名写错、参数不合法。→ 退出码 2，不该重试。"""

    exit_code = 2
    retryable = False


class AuthError(ChatError):
    """认证失败（401/403）：key 无效或不符权限。→ 退出码 2，重试没用。"""

    exit_code = 2
    retryable = False


class ContextOverflowError(ChatError):
    """上下文超长（400 且消息含 maximum context length）。→ 退出码 4。"""

    exit_code = 4
    retryable = False


class NetworkError(ChatError):
    """连不上 / 超时。→ 退出码 3，可重试。"""

    exit_code = 3
    retryable = True


class TooManyRequestsError(ChatError):
    """限流（429）。→ 退出码 3，可重试，优先听 Retry-After。"""

    exit_code = 3
    retryable = True


class ServerError(ChatError):
    """上游 5xx。→ 退出码 3，可重试。"""

    exit_code = 3
    retryable = True


def _retry_after_from(exc: BaseException) -> float | None:
    """从异常里尽量读出 Retry-After（秒）。拿不到就返回 None。"""
    resp = getattr(exc, "response", None)
    headers = getattr(resp, "headers", None)
    if headers is None:
        return None
    try:
        raw = headers.get("retry-after")
    except Exception:  # noqa: BLE001 —— headers 可能是各种实现
        return None
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _wrap(err: ChatError, exc: BaseException) -> ChatError:
    """把原始异常挂到 __cause__ 上（等价于 raise ... from，但这里是 return）。"""
    err.__cause__ = exc
    return err


def classify_error(exc: BaseException) -> ChatError:
    """把任意异常翻译成 ChatError 的子类。

    已经是 ChatError 就原样返回，所以可以安全地重复调用。
    原始异常会挂在结果的 __cause__ 上，方便调试。

    Args:
        exc: 捕获到的异常。

    Returns:
        一个 ChatError 实例（带 message / exit_code / retryable / retry_after）。
    """
    if isinstance(exc, ChatError):
        return exc

    # ---- 延迟导入：让本模块在没装 openai 时也能被 import 做纯逻辑测试 ----
    try:
        import openai as _oai
    except ImportError:                        # pragma: no cover
        return _wrap(ChatError(f"未知错误：{type(exc).__name__}: {exc}"), exc)

    # 连接层：注意 APITimeoutError 是 APIConnectionError 的子类，
    # 所以先判超时会更精确地给出"超时"而不是"连不上"。
    if isinstance(exc, _oai.APITimeoutError):
        return _wrap(NetworkError("请求超时，请稍后重试"), exc)
    if isinstance(exc, _oai.APIConnectionError):
        return _wrap(NetworkError("连不上服务器，请检查网络或代理设置"), exc)

    # 状态码层
    if isinstance(exc, _oai.APIStatusError):
        code = getattr(exc, "status_code", None)
        text = str(exc)

        if code == 400:
            if "maximum context length" in text:
                return _wrap(ContextOverflowError(
                    "输入太长了，超出模型上下文上限。建议 /clear 或分段提问"
                ), exc)
            low = text.lower()
            if "model" in low and any(k in low for k in
                                      ("not found", "supported", "no such",
                                       "does not exist", "invalid")):
                return _wrap(ConfigError(
                    "模型名不对，请检查 --model 或 .env 里的 LLM_MODEL"
                ), exc)
            return _wrap(ConfigError(f"请求参数有问题（400）：{text[:200]}"), exc)

        if code in (401, 403):
            return _wrap(AuthError(
                f"认证失败（HTTP {code}）：API Key 无效或权限不足"
            ), exc)

        if code == 429:
            return _wrap(TooManyRequestsError(
                "请求太频繁（429），请等一会儿再试",
                retry_after=_retry_after_from(exc),
            ), exc)

        if code is not None and 500 <= code < 600:
            return _wrap(ServerError(
                f"服务端暂时故障（HTTP {code}），请稍后重试"
            ), exc)

        return _wrap(ChatError(f"上游返回 HTTP {code}：{text[:200]}"), exc)

    # 兜底
    return _wrap(ChatError(f"未预期的错误：{type(exc).__name__}: {exc}"), exc)


def call_with_retry(
    fn,
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
    on_retry=None,
):
    """执行 fn()，只对"可重试"的 ChatError 重试（第 2 周 with_retry 的精简版）。

    Args:
        fn: 零参数可调用对象。
        attempts: 最多尝试次数（含第一次）。
        base_delay: 指数退避基数（秒）。
        max_delay: 单次等待上限（秒）。
        on_retry: 可选回调，签名 (attempt, err, delay) -> None，用于打印日志。

    Returns:
        fn() 的返回值。

    Raises:
        ChatError: 最后一次失败翻译后的异常。
    """
    if attempts < 1:
        raise ValueError("attempts 至少为 1")

    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except BaseException as exc:  # noqa: BLE001 —— 统一交给 classify_error
            err = classify_error(exc)
            if not err.retryable or attempt == attempts:
                raise err from exc
            delay = err.retry_after if err.retry_after is not None \
                else base_delay * 2 ** (attempt - 1)
            delay = min(delay, max_delay)
            if on_retry is not None:
                on_retry(attempt, err, delay)
            time.sleep(delay)

    raise RuntimeError("不可达：最后一次一定已经 raise")


# ============================================================ 四、客户端
def make_client() -> tuple[OpenAI, str]:
    """从 .env 构造客户端，返回 (client, model)。

    Raises:
        SystemExit: 退出码 2（配置缺失，属于用法问题）。
    """
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("错误：没有找到 API Key，请检查 .env 里的 DEEPSEEK_API_KEY",
              file=sys.stderr)
        raise SystemExit(2)

    base_url = os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_API_BASE_URL")
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    return OpenAI(api_key=api_key, base_url=base_url), model
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D4 多轮对话与历史管理。

修复要点（对照原版）：
  1. P0：请求成功后才把 user 消息提交进历史 —— 出错不会毒化 messages
  2. trim() 对空列表 / 空 tail 做防御，不再 IndexError
  3. 变量 round1 → turn（不再遮蔽内置 round）
  4. 模型从 .env 读（LLM_MODEL），不写死
  5. input() 捕获 EOFError / KeyboardInterrupt
  6. 日志区分"本轮"与"累计"
  7. 补 /clear、/cost、/exit 命令
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import BadRequestError, OpenAI

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


# ============================================================ 一、计费
def _get(usage, name: str, default: int = 0) -> int:
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
    prompt = _get(usage, "prompt_tokens")
    completion = _get(usage, "completion_tokens")
    cached = _get(usage, "prompt_cache_hit_tokens")
    # prompt_tokens 是总数，已包含缓存命中部分
    uncached = max(prompt - cached, 0)

    return (
        uncached / 1_000_000 * PRICE["in"]
        + cached / 1_000_000 * PRICE["in_cached"]
        + completion / 1_000_000 * PRICE["out"]
    )


# ============================================================ 二、历史管理
def trim(
    messages: list[dict[str, str]],
    max_messages: int = MAX_MESSAGES,
    keep_recent: int = KEEP_RECENT,
) -> list[dict[str, str]]:
    """保留 system + 最近 keep_recent 条，返回新列表（不改动入参）。

    规则：
      - 不超过 max_messages 时原样返回副本
      - system 永远保留
      - 若截断后第一条是 assistant（孤儿回复），再丢掉它
    """
    if len(messages) <= max_messages:
        return list(messages)

    head = messages[:1]                     # system
    tail = messages[1:][-keep_recent:]      # 最近 N 条
    if tail and tail[0].get("role") == "assistant":
        tail = tail[1:]
    return head + tail


# ============================================================ 三、客户端
def make_client() -> tuple[OpenAI, str]:
    """从 .env 构造客户端，返回 (client, model)。"""
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("没有找到 API Key，请检查 .env 里的 DEEPSEEK_API_KEY")

    base_url = os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_API_BASE_URL")
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    return OpenAI(api_key=api_key, base_url=base_url), model


# ============================================================ 四、主循环
def run() -> int:
    """交互式多轮对话，返回进程退出码。"""
    client, model = make_client()

    system_prompt = DEFAULT_SYSTEM
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    total_prompt = 0
    total_completion = 0
    total_cached = 0
    total_cost = 0.0
    turn = 1

    print(f"模型：{model}｜消息上限：{MAX_MESSAGES} 条（保留最近 {KEEP_RECENT} 条）")
    print("命令：/clear 清空历史 ｜ /cost 查看花费 ｜ /exit 退出\n")

    while True:
        try:
            raw = input("你：")
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            return 0

        user_input = raw.strip()
        if not user_input:
            print("输入不能为空")
            continue

        # ---------- 命令 ----------
        lowered = user_input.lower()
        if lowered in {"/exit", "exit", "quit", "q"}:
            print(f"再见。本次共 {turn - 1} 轮，累计 ¥{total_cost:.6f}")
            return 0

        if lowered == "/clear":
            messages = [{"role": "system", "content": system_prompt}]
            print("已清空历史（保留 system）")
            continue

        if lowered == "/cost":
            print(
                f"本次会话：输入 {total_prompt:,} tokens（缓存命中 {total_cached:,}）"
                f"｜输出 {total_completion:,} tokens\n"
                f"累计费用：¥{total_cost:.6f}"
            )
            continue

        # ---------- P0 修复：成功后才提交历史 ----------
        candidate = messages + [{"role": "user", "content": user_input}]
        try:
            # messages 用 dict[str, str] 表示更宽松；SDK 要的是 TypedDict 联合类型，
            # 运行时等价，这里只让 mypy 闭嘴。
            resp = client.chat.completions.create(
                model=model,
                messages=candidate,  # type: ignore[arg-type]
            )
        except BadRequestError as e:
            msg = str(e)
            if "maximum context length" in msg:
                print("输入太长了，本次请求未发送成功。")
                print(f"当前历史 {len(messages)} 条。建议 /clear 清空，或分几段提问。")
                # 关键：messages 未被污染，可以直接重试
                continue
            print(f"请求被拒绝（400）：{msg[:200]}")
            return 4
        except Exception as e:  # noqa: BLE001 —— 网络类错误统一提示
            print(f"调用失败：{type(e).__name__}: {str(e)[:200]}")
            return 3

        # 到这里说明请求成功了，才提交
        messages = candidate
        reply = resp.choices[0].message.content or ""
        messages.append({"role": "assistant", "content": reply})

        # ---------- 记账 ----------
        usage = resp.usage
        prompt = _get(usage, "prompt_tokens")
        completion = _get(usage, "completion_tokens")
        cached = _get(usage, "prompt_cache_hit_tokens")
        cost1 = cost(usage)

        total_prompt += prompt
        total_completion += completion
        total_cached += cached
        total_cost += cost1

        print(reply)

        # ---------- 截断 ----------
        before = len(messages)
        if before > MAX_MESSAGES:
            messages = trim(messages, MAX_MESSAGES, KEEP_RECENT)
            print(f"  [截断] 消息 {before} -> {len(messages)} 条")

        finish = resp.choices[0].finish_reason
        flag = "" if finish == "stop" else f"  ⚠ finish_reason={finish}"

        print(
            f"[第{turn}轮] 消息 {len(messages)} 条｜"
            f"本轮 输入 {prompt}（缓存 {cached}）/ 输出 {completion}｜¥{cost1:.6f}｜"
            f"累计 输入 {total_prompt} / 输出 {total_completion}｜¥{total_cost:.6f}{flag}"
        )
        turn += 1


if __name__ == "__main__":
    sys.exit(run())

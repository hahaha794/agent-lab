#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chatlib


# ============================================================
# 配置结构
# ============================================================
@dataclass
class Config:
    client: Any
    model: str
    stream: bool
    temperature: float
    system_prompt: str
    max_messages: int
    attempts: int


# ============================================================
# 公共一：参数解析 + 校验 + system prompt + client
# ============================================================
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="LLM CLI")
    p.add_argument("--no-stream", action="store_true",
                   help="关闭流式输出（默认开启流式）")
    p.add_argument("--temperature", type=float, default=0.7,
                   help="采样温度，0 稳定、1.2+ 发散（默认 0.7）")
    p.add_argument("--system", type=Path, default=None,
                   help=f"system prompt 文件路径（默认读 {chatlib.DEFAULT_SYSTEM_FILE}，不存在则用内置默认）")
    p.add_argument("--model", type=str, default=None,
                   help="模型名（默认读 .env 的 LLM_MODEL）")
    p.add_argument("--max-messages", type=int, default=12,
                   help="历史条数上限，超出触发 trim()（默认 12）")
    p.add_argument("--attempts", type=int, default=3,
                   help="单次请求最多尝试次数，仅对可重试错误生效（默认 3）")
    return p


def build_config(argv: list[str] | None = None) -> Config:
    """两个入口共用的初始化：解析、校验、system prompt、client。

    Raises:
        SystemExit: 退出码 2（用法/配置错误，与 argparse 一致）。
    """
    args = build_parser().parse_args(argv)

    if not (0.0 <= args.temperature <= 2.0):
        print("错误：--temperature 需在 0.0 ~ 2.0 之间", file=sys.stderr)
        raise SystemExit(2)
    if args.max_messages < 2:
        print("错误：--max-messages 需 >= 2（1 条 system + 至少 1 条对话）",
              file=sys.stderr)
        raise SystemExit(2)
    if args.attempts < 1:
        print("错误：--attempts 需 >= 1", file=sys.stderr)
        raise SystemExit(2)

    client, model = chatlib.make_client()
    if args.model:                       # 命令行优先覆盖 .env 里的 LLM_MODEL
        model = args.model

    return Config(
        client=client,
        model=model,
        stream=not args.no_stream,       # 开关默认关 => 默认流式
        temperature=args.temperature,
        system_prompt=chatlib.load_system_prompt(args.system),
        max_messages=args.max_messages,
        attempts=args.attempts,
    )


# ============================================================
# 公共二：交互式对话主循环（原 run 的主体）
# ============================================================
def chat_loop(cfg: Config) -> int:
    system_prompt = cfg.system_prompt
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    total_prompt = total_completion = total_cached = 0
    total_cost = 0.0
    turn = 1

    print(f"模型：{cfg.model}｜消息上限：{cfg.max_messages} 条"
          f"（保留最近 {chatlib.KEEP_RECENT} 条）")
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

        lowered = user_input.lower()
        if lowered in {"/exit", "exit", "quit", "q"}:
            print(f"再见。本次共 {turn - 1} 轮，累计 ¥{total_cost:.6f}")
            return 0
        if lowered == "/clear":
            messages = [{"role": "system", "content": system_prompt}]
            print("已清空历史（保留 system）")
            continue
        if lowered == "/cost":
            print(f"本次会话：输入 {total_prompt:,} tokens（缓存命中 {total_cached:,}）"
                  f"｜输出 {total_completion:,} tokens\n累计费用：¥{total_cost:.6f}")
            continue

        # ---------- P0：成功后才提交历史 ----------
        candidate = messages + [{"role": "user", "content": user_input}]

        def _call():
            return cfg.client.chat.completions.create(
                model=cfg.model,
                messages=candidate,        # type: ignore[arg-type]
                stream=cfg.stream,
                temperature=cfg.temperature,
                **(  # type: ignore[arg-type]
                    {"stream_options": {"include_usage": True}}
                    if cfg.stream
                    else {}
                ),
            )

        try:
            # 复用第 2 周的重试思路：只对"可重试"的错误（超时/连接/429/5xx）重试
            resp = chatlib.call_with_retry(
                _call,
                attempts=cfg.attempts,
                on_retry=lambda n, err, d: print(
                    f"  ↻ 第 {n} 次失败（{type(err).__name__}），{d:.1f} 秒后重试"
                ),
            )
        except chatlib.ContextOverflowError as e:
            # 超长不重试、也不进历史 —— messages 没被污染，可以直接重试
            print(e.message)
            print(f"当前历史 {len(messages)} 条。建议 /clear 清空，或分几段提问。")
            continue
        except chatlib.ChatError as e:
            print(e.message)
            return e.exit_code

        messages = candidate

        # ---------- 流式/非流式取回复与 usage ----------
        usage = None
        finish = None
        if cfg.stream:
            parts: list[str] = []
            for chunk in resp:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        print(delta.content, end="", flush=True)
                        parts.append(delta.content)
                    if chunk.choices[0].finish_reason:
                        finish = chunk.choices[0].finish_reason
                # 注意这一行在 if chunk.choices 外面：OpenAI 的 usage chunk
                # 的 choices 是空列表，写里面就永远拿不到。
                if getattr(chunk, "usage", None):
                    usage = chunk.usage
            print()
            reply = "".join(parts)
        else:
            reply = resp.choices[0].message.content or ""
            usage = resp.usage
            finish = resp.choices[0].finish_reason

        messages.append({"role": "assistant", "content": reply})

        # ---------- 记账 ----------
        if usage is None:
            # 拿不到 usage 就明确说出来，别静默算成 0 元 —— 那是"看起来免费"
            print("⚠ 本次未能获取 usage，费用未统计（可能是模型/接口不支持）")
            prompt = completion = cached = 0
            cost1 = 0.0
        else:
            prompt = chatlib.get_usage_field(usage, "prompt_tokens")
            completion = chatlib.get_usage_field(usage, "completion_tokens")
            cached = chatlib.get_usage_field(usage, "prompt_cache_hit_tokens")
            cost1 = chatlib.cost(usage)

        total_prompt += prompt
        total_completion += completion
        total_cached += cached
        total_cost += cost1

        if not cfg.stream:
            print(reply)

        # ---------- 截断 ----------
        before = len(messages)
        if before > cfg.max_messages:
            messages = chatlib.trim(messages, cfg.max_messages, chatlib.KEEP_RECENT)
            print(f"  [截断] 消息 {before} -> {len(messages)} 条"
                  f"（上限 {cfg.max_messages}，保留最近 {chatlib.KEEP_RECENT} 条）")

        flag = "" if finish == "stop" else f"  ⚠ finish_reason={finish}"
        print(
            f"[第{turn}轮] 消息 {len(messages)} 条｜"
            f"本轮 输入 {prompt}（缓存 {cached}）/ 输出 {completion}｜¥{cost1:.6f}｜"
            f"累计 输入 {total_prompt} / 输出 {total_completion}｜¥{total_cost:.6f}{flag}"
        )
        turn += 1


# ============================================================
# 入口
# ============================================================
def run() -> int:
    """交互入口（供 import 调用，走默认配置）。"""
    return chat_loop(build_config(None))


def main(argv: list[str] | None = None) -> int:
    """命令行入口：解析 argv（None 时读 sys.argv[1:]）后进入对话。"""
    return chat_loop(build_config(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())
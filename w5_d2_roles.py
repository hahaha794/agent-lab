#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 来源：DeepSeek 官网定价页，查询日期 2026-11-26
# 单位：元 / 百万 token
PRICE = {
    "in": 1.0,          # ← 换成你查到的数字
    "in_cached": 0.02,   # ← 换成你查到的数字
    "out": 4.0,         # ← 换成你查到的数字
}

def _get(usage, name: str, default: int = 0) -> int:
    """从对象或 dict 里取值，拿不到就返回默认值。"""
    # 提示：先 isinstance(usage, dict)，否则 getattr
    if isinstance(usage, dict):
        value = usage.get(name, default)
    else:
        value = getattr(usage, name, default)

        # 属性/键存在但值为 None 时，也回退到默认值
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
    cached = _get(usage, "prompt_cache_hit_tokens")     # 没有就是 0
    uncached = prompt - cached if cached else prompt

    # TODO: 用 PRICE 算出来
    return (uncached/1000000)*PRICE["in"]+(cached/1000000)*PRICE["in_cached"]+(completion/1000000)*PRICE["out"]

llm = OpenAI(api_key=os.environ['DEEPSEEK_API_KEY'],
             base_url=os.environ['DEEPSEEK_API_BASE_URL'])

def run()->None:
    """
    单次调用大模型
    :param
     user_prompt:用户输入
    :return:
    无返回值
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": "你是一个简洁的助手，回答不超过三句话。"},
    ]

    while True:
        user_input = input("你：").strip()
        messages.append({"role": "user", "content": user_input})
        resp = llm.chat.completions.create(model='deepseek-flash', messages=messages)
        reply = resp.choices[0].message.content
        print(reply)
        messages.append({"role": "assistant", "content": reply})


if __name__ == '__main__':
    run()
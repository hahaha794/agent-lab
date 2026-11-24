# -*- coding: utf-8 -*-
"""
00_hello_llm.py —— 第 0 周的交付物：让模型回你一句话。

⚠️ 学习建议：先照着《第0周-环境搭建.md》自己手敲一遍，敲不出来再对照这个文件。
   复制粘贴会让你的手指记住"Ctrl+V"，而不是 python 语法。

运行：
    python code\\00_hello_llm.py            # 真实调用，打印模型回复和 token 用量
    python code\\00_hello_llm.py --check    # 环境体检，不联网，不花钱
"""

import os
import sys
from pathlib import Path

# 项目根目录（本文件在 code/ 下，所以往上两层）
ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"


# ---------------------------------------------------------------------------
# 第 1 部分：读 .env
# ---------------------------------------------------------------------------
def load_env() -> None:
    """
    把 .env 里的内容读进来。

    这里故意写成 load_dotenv(ENV_FILE)，而不是什么都不写的 load_dotenv()。
    原因：默认的 load_dotenv() 只在【当前工作目录】找 .env。
    如果你在别的文件夹里执行 python，它就找不到，于是报"没有 API Key"——
    这是新手最常见的困惑之一。写死路径最省事。
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("缺少 python-dotenv，请先执行：python -m pip install python-dotenv")
        sys.exit(1)

    if not ENV_FILE.exists():
        print(f"没有找到 .env 文件，应该在：{ENV_FILE}")
        print("请先按《第0周-环境搭建.md》第 6 步创建它。")
        sys.exit(1)

    load_dotenv(ENV_FILE)


# ---------------------------------------------------------------------------
# 第 2 部分：真正说话的地方
# ---------------------------------------------------------------------------
def say_hello() -> int:
    load_env()

    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(".env 里没读到 DEEPSEEK_API_KEY。")
        print(f"请检查 {ENV_FILE} 的内容，格式是：DEEPSEEK_API_KEY=sk-xxxx")
        return 1

    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("LLM_MODEL", "deepseek-chat")

    from openai import (
        APIConnectionError,
        APIStatusError,
        AuthenticationError,
        OpenAI,
        RateLimitError,
    )

    client = OpenAI(api_key=api_key, base_url=base_url)

    question = "你好，我是今天第一次学编程的人。请用一句话鼓励我，并告诉我你能帮我做什么。"
    messages = [
        {"role": "system", "content": "你是一位耐心的编程启蒙老师，说话简洁、具体、不说空话。"},
        {"role": "user", "content": question},
    ]

    print(f"模型：{model}    地址：{base_url}\n")
    print(f"你：{question}\n")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
        )
    except AuthenticationError:
        print("❌ 401 认证失败：API Key 不正确。")
        print("   常见原因：复制时少了几个字符 / 前后有空格 / 这是别人的 key。")
        print("   解法：去平台重新生成一个，整段（含 sk-）复制进 .env。")
        return 1
    except RateLimitError:
        print("❌ 402 / 429：余额不足或请求太频繁。")
        print("   解法：去平台充值（10 元就够学很久），或等 1 分钟再试。")
        return 1
    except APIConnectionError:
        print("❌ 连不上服务器：检查网络、代理，或 base_url 是否写错。")
        return 1
    except APIStatusError as exc:
        print(f"❌ 服务端返回 {exc.status_code}：{exc.message}")
        return 1
    except Exception as exc:  # noqa: BLE001  兜底，把原始错误露出来方便搜索
        print(f"❌ 未预期的错误：{type(exc).__name__}: {exc}")
        return 1

    # 打印模型回复
    print("=" * 60)
    print(response.choices[0].message.content)
    print("=" * 60)

    # 打印用量 —— 这就是你以后要天天盯的东西
    usage = response.usage
    if usage:
        print(
            f"\n本次用量：输入 {usage.prompt_tokens} tokens ｜ "
            f"输出 {usage.completion_tokens} tokens ｜ 合计 {usage.total_tokens} tokens"
        )
        print("提示：输入输出是分开计价的，输出通常贵 2~4 倍。")
        print("      中文大约 1 个字 = 1~1.5 个 token。")

    print("\n🎉 第 0 周完成了。你已经能调用大模型了。")
    return 0


# ---------------------------------------------------------------------------
# 第 3 部分：环境体检（--check）
# ---------------------------------------------------------------------------
def check_env() -> int:
    print("=" * 60)
    print("环境体检（不联网、不花钱）")
    print("=" * 60)

    results: list[tuple[bool, str]] = []

    # 1. Python 版本
    v = sys.version_info
    ok = (v.major, v.minor) >= (3, 9)
    results.append((ok, f"Python {v.major}.{v.minor}.{v.micro}（需要 >= 3.9）"))

    # 2. 是否在虚拟环境里
    in_venv = sys.prefix != sys.base_prefix
    results.append(
        (in_venv, f"虚拟环境：{'已激活 → ' + sys.prefix if in_venv else '未激活，请先执行 .\\.venv\\Scripts\\Activate.ps1'}")
    )

    # 3. openai 包
    try:
        import openai

        results.append((True, f"openai 已安装，版本 {openai.__version__}"))
        results.append((".venv" in str(Path(openai.__file__).parent), f"openai 位置：{Path(openai.__file__).parent}"))
    except ImportError:
        results.append((False, "openai 没安装 → python -m pip install openai"))

    # 4. python-dotenv
    try:
        import dotenv

        results.append((True, "python-dotenv 已安装"))
    except ImportError:
        results.append((False, "python-dotenv 没安装 → python -m pip install python-dotenv"))

    # 5. .env 文件
    exists = ENV_FILE.exists()
    results.append((exists, f".env 文件：{ENV_FILE}"))

    # 6. Key
    if exists:
        try:
            load_env()
        except SystemExit:
            pass
        key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not key:
            results.append((False, "env 里的 key：没读到（检查变量名是否写错）"))
        elif not key.startswith("sk-"):
            results.append((False, f"env 里的 key：格式可疑（应以 sk- 开头，当前长度 {len(key)}）"))
        else:
            results.append((True, f"env 里的 key：已读到（{key[:6]}…{key[-4:]}，长度 {len(key)}）"))
    else:
        results.append((False, "env 里的 key：跳过（.env 不存在）"))

    # 7. .gitignore
    gi = ROOT / ".gitignore"
    if gi.exists():
        text = gi.read_text(encoding="utf-8", errors="ignore")
        has = any(line.strip() == ".env" for line in text.splitlines())
        results.append((has, ".gitignore 已排除 .env" if has else ".gitignore 里缺少 .env 这一行 ← 高危！"))
    else:
        results.append((False, ".gitignore 不存在 ← key 会被推到 GitHub"))

    # 输出
    print()
    for ok, text in results:
        print(f"  [{'OK' if ok else '!!'}] {text}")

    failed = [t for ok, t in results if not ok]
    print()
    if failed:
        print(f"共 {len(failed)} 项待处理：")
        for t in failed:
            print(f"  - {t}")
        print("\n修完重新跑一次：python code\\00_hello_llm.py --check")
        return 1

    print("全部通过 ✅  现在运行：python code\\00_hello_llm.py")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check_env())
    sys.exit(say_hello())

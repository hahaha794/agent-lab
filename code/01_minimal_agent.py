"""
01_minimal_agent.py —— 不依赖任何框架的最小 Agent（约 200 行，含注释）

它做的事只有一件：让模型在一个循环里决定"调用工具"还是"给出答案"。
理解了这 200 行，你就理解了 LangGraph / OpenAI Agents SDK / CrewAI 的 90% 内核。

用法
----
# 1) 不联网，只验证"循环 + 工具 + 错误自愈"的逻辑对不对
python code/01_minimal_agent.py --selftest

# 2) 真实对话（需要一个 API Key）
$env:DEEPSEEK_API_KEY = "sk-xxxx"      # 或 $env:OPENAI_API_KEY
python code/01_minimal_agent.py

# 3) 换模型 / 换服务商
$env:LLM_BASE_URL = "https://api.deepseek.com"
$env:LLM_MODEL    = "deepseek-chat"

退出方式：输入 exit 或按 Ctrl+C

安装依赖
--------
pip install openai
"""

from __future__ import annotations

import argparse
import ast
import datetime
import json
import os
import sys
from typing import Any, Callable

# ============================================================================
# 第 1 部分：工具（Tools）
# ----------------------------------------------------------------------------
# 一个"工具"就是三样东西：一个 Python 函数 + 一份 JSON Schema 描述 + 一句何时该用。
# 注意：模型永远不会执行这些代码，它只会"请求"执行，真正运行的是你。
# ============================================================================


def _safe_eval(node: ast.AST) -> float:
    """
    安全地计算四则运算表达式。
    ⚠️ 绝对不要用 eval() 跑模型给你的字符串 —— 那是可以直接执行任意代码的漏洞。
    这里用 ast 只放行"数字 + 四则运算 + 括号"这几种节点。
    """
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _safe_eval(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(
        node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
    ):
        left, right = _safe_eval(node.left), _safe_eval(node.right)
        op = node.op
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.Div):
            return left / right
        if isinstance(op, ast.FloorDiv):
            return left // right
        if isinstance(op, ast.Mod):
            return left % right
        return left**right
    raise ValueError("表达式里只允许数字和 + - * / // % ** 与括号")


def calculator(expression: str) -> str:
    """计算一个数学表达式，例如 '(12+8)*3'。适用于任何算术问题。"""
    tree = ast.parse(expression, mode="eval")
    result = _safe_eval(tree)
    # 让 60.0 显示成 60
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return str(result)


def get_current_time(timezone: str = "local") -> str:
    """获取当前日期和时间。timezone 目前只支持 'local'（本机时区）。"""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S (%A)")


# --- 工具注册表 --------------------------------------------------------------
# 想加工具？写一个函数，然后在下面登记：名字 -> (函数, 描述, 参数schema)
# 描述里一定要写"何时该用、何时不该用"，这是新手最容易忽略、又最影响效果的地方。

TOOLS: dict[str, dict[str, Any]] = {
    "calculator": {
        "fn": calculator,
        "schema": {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": (
                    "计算数学表达式，支持 + - * / // % ** 和括号。"
                    "只要涉及任何算术、找零、百分比、单位换算，都必须用它，"
                    "不要自己心算。不适用于解方程或符号运算。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "纯数学表达式，如 '(12+8)*3'，不要包含等号或中文",
                        }
                    },
                    "required": ["expression"],
                },
            },
        },
    },
    "get_current_time": {
        "fn": get_current_time,
        "schema": {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "获取当前的日期、时间和星期。只用于回答与'现在/今天'相关的问题。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "时区，目前固定填 'local'",
                            "default": "local",
                        }
                    },
                    "required": [],
                },
            },
        },
    },
}


def run_tool(name: str, arguments_json: str) -> str:
    """
    执行一个工具，并把【所有】异常都变成一段文字返回给模型。
    这是整个 Agent 最关键的一行设计：工具失败不能让程序崩掉，
    而要让模型看到错误、自己改正（这叫"错误自愈"）。
    """
    if name not in TOOLS:
        return f"错误：不存在名为 {name} 的工具。可用工具：{list(TOOLS)}"

    try:
        args = json.loads(arguments_json) if arguments_json.strip() else {}
    except json.JSONDecodeError as exc:
        return f"错误：参数不是合法 JSON（{exc}）。请重新生成参数。"

    if not isinstance(args, dict):
        return "错误：参数必须是一个 JSON 对象。"

    fn: Callable[..., str] = TOOLS[name]["fn"]
    try:
        return fn(**args)
    except TypeError as exc:
        return f"错误：参数不匹配（{exc}）。请检查参数名和类型。"
    except Exception as exc:  # noqa: BLE001 —— 故意兜住一切，交给模型处理
        return f"工具执行出错：{type(exc).__name__}: {exc}"


# ============================================================================
# 第 2 部分：系统提示词
# ============================================================================
SYSTEM_PROMPT = """你是一个谨慎、简洁的助手。

规则：
1. 涉及任何计算时，必须调用 calculator 工具，禁止心算。
2. 涉及"现在/今天/当前时间"时，必须调用 get_current_time。
3. 工具返回"错误"时，读懂错误、修正后重试，最多重试 2 次。
4. 不确定的事情直接说"我不确定"，不要编造。
5. 回答使用中文，简洁，不超过 5 句话。
"""


# ============================================================================
# 第 3 部分：LLM 调用层
# ----------------------------------------------------------------------------
# 把"调用模型"包成一个函数，返回统一的 dict 结构。
# 好处：selftest 时可以换成假的模型，不需要网络也不需要 API Key。
# ============================================================================

Message = dict[str, Any]


def make_real_llm():
    """返回一个真实的模型调用函数。"""
    try:
        from openai import OpenAI  # 延迟导入：selftest 模式下不需要它
    except ImportError:
        sys.exit("缺少依赖，请先执行：pip install openai")

    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit(
            "没有找到 API Key。请先设置环境变量，例如：\n"
            '  $env:DEEPSEEK_API_KEY = "sk-xxxx"\n'
            "或在项目根目录建 .env 文件并用 python-dotenv 加载。"
        )

    base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    client = OpenAI(api_key=api_key, base_url=base_url)
    print(f"[配置] base_url={base_url}  model={model}\n")

    def call_llm(messages: list[Message]) -> Message:
        response = client.chat.completions.create(
            model=model,
            messages=messages,          # type: ignore[arg-type]
            tools=[t["schema"] for t in TOOLS.values()],
            tool_choice="auto",          # 让模型自己决定要不要调工具
            temperature=0.2,             # 工具调用场景要稳定
        )
        msg = response.choices[0].message
        out: Message = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            out["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in msg.tool_calls
            ]
        return out

    return call_llm


# ============================================================================
# 第 4 部分：Agent 循环（核心，就这 30 行）
# ============================================================================


def run_agent(
    user_input: str,
    call_llm: Callable[[list[Message]], Message],
    max_steps: int = 8,
    verbose: bool = True,
) -> str:
    """
    一个完整的 Agent 循环：
      组装 messages → 调模型 → 有 tool_calls 就执行并回填 → 再调模型 → ... → 给出答案

    max_steps 是安全阀：没有它，一个跑偏的 Agent 可以烧掉你几百块钱。
    """
    messages: list[Message] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]

    for step in range(1, max_steps + 1):
        reply = call_llm(messages)
        messages.append(reply)

        tool_calls = reply.get("tool_calls") or []

        # 情况 A：模型没有要求调工具 —— 说明它认为可以回答了，循环结束
        if not tool_calls:
            return reply.get("content", "")

        # 情况 B：模型要求调用工具 —— 逐个执行，把结果写回 messages
        for call in tool_calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            result = run_tool(name, args)

            if verbose:
                print(f"  ↳ [第{step}步] 调用 {name}({args}) => {result}")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],   # ⚠️ 必须和上面的 id 对应，否则 API 报错
                    "content": result,
                }
            )

    return f"已达到最大步数 {max_steps}，任务未完成（这通常意味着工具或提示词需要改进）。"


# ============================================================================
# 第 5 部分：离线自检（不需要网络、不需要 API Key）
# ============================================================================


def _fake_llm_script():
    """
    一个"假的模型"：按预设剧本返回，用来验证我们的循环逻辑是否正确。
    剧本 1：模型先算错一次（除零），看到报错后改成正确表达式，然后给出答案。
    """
    state = {"step": 0}
    seen: list[Message] = []

    def fake(messages: list[Message]) -> Message:
        state["step"] += 1
        seen.append(messages[-1])

        if state["step"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "calculator", "arguments": '{"expression": "(12+8)*3"}'},
                    }
                ],
            }

        if state["step"] == 2:
            # 检查：上一步的工具结果真的回填进来了吗？
            assert messages[-1]["role"] == "tool", "工具结果没有被回填"
            assert messages[-1]["content"] == "60", f"计算结果不对：{messages[-1]['content']}"
            # 故意再来一次会报错的调用（除零），验证错误自愈
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {"name": "calculator", "arguments": '{"expression": "1/0"}'},
                    }
                ],
            }

        if state["step"] == 3:
            assert "工具执行出错" in messages[-1]["content"], "除零错误没有被捕获并回传"
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_3",
                        "type": "function",
                        "function": {"name": "calculator", "arguments": '{"expression": "60/3"}'},
                    }
                ],
            }

        return {"role": "assistant", "content": "答案是 60，除以 3 等于 20。"}

    return fake


def selftest() -> int:
    print("=" * 62)
    print("离线自检：验证 Agent 循环 + 工具调用 + 错误自愈")
    print("=" * 62)

    fake = _fake_llm_script()
    answer = run_agent("(12+8) 乘以 3 等于多少？除以 3 呢？", fake, max_steps=8, verbose=True)

    print("\n最终回答：", answer)
    assert answer == "答案是 60，除以 3 等于 20。", "最终回答不符合预期"

    # 额外验证：未知工具 / 非法 JSON 参数 / 死循环保护
    assert run_tool("no_such_tool", "{}").startswith("错误：不存在")
    assert run_tool("calculator", "{不是json").startswith("错误：参数不是合法 JSON")
    assert run_tool("calculator", '{"expression": "__import__(\'os\')"}').startswith("工具执行出错")
    assert "达到最大步数" in run_agent("x", lambda m: {"role": "assistant", "content": "", "tool_calls": [
        {"id": "loop", "type": "function", "function": {"name": "get_current_time", "arguments": "{}"}}
    ]}, max_steps=2, verbose=False)

    print("\n✅ 全部通过：循环、工具、错误捕获、死循环保护都正常。")
    print("下一步：设置 API Key 后运行  python code/01_minimal_agent.py")
    return 0


# ============================================================================
# 第 6 部分：入口
# ============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description="最小 Agent 示例（无框架）")
    parser.add_argument("--selftest", action="store_true", help="离线自检，不联网")
    parser.add_argument("--once", type=str, default=None, help="只问一个问题就退出")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    call_llm = make_real_llm()

    if args.once:
        print(f"\n你：{args.once}")
        print(f"\nAgent：{run_agent(args.once, call_llm)}")
        return 0

    print("多工具 Agent 已就绪。输入问题，输入 exit 退出。")
    print("试试：'现在几点？'(12+8)*3 是多少？'\n")
    while True:
        try:
            user_input = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            return 0
        if user_input.lower() in {"exit", "quit", "q"}:
            return 0
        if not user_input:
            continue
        print()
        print(f"Agent：{run_agent(user_input, call_llm)}")
        print()


if __name__ == "__main__":
    sys.exit(main())

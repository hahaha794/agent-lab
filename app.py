import re
WEATHER_DATA = {
    "北京": "晴，25℃",
    "上海": "多云，23℃",
    "广州": "小雨，28℃",
    "深圳": "晴，29℃"
}
#短期记忆，保留会话历史
history = []

# 感知模块：读取输入

def perceive():
    return input("您：北京天气  ").strip()

#决策模块，识别任务的类型
def make_decision(message):
    if message.lower() in ("退出", "exit", "quit"):
        return "exit"
    if "天气" in message:
        return "weather"
    if "计算"in message or  re.search(
        r"\d\s*[\+\-\*/]\s\d",message):
        return "calculator"
    return "chat"
#天气工具，返回对应的模拟数据部分
def get_weather(message):
    for city,weather in WEATHER_DATA.items():
        if city in message:
            return f"{city}天气：{weather}（模拟数据）"
    return "请输入北京、上海、广州或深圳进行查询。"

def calculator(message):
    pattern = (
        r"(-?\d+(?:\.\d+)?)"
        #最后面来个？表示的意思是可以有后面的小数也可以没有即可
        r"\s*([\+\-\*/])\s*"
        r"(-?\d+(?:\.\d+)?)"
    )
    # 表示捕获组，把整个数字作为一组
    match = re.search(pattern, message)
    if not match:
        return "请输入算式，例如：计算 10 + 5"

    a = float(match.group(1))
    op = match.group(2)
    b = float(match.group(3))

    if op == "+":
        result = a + b
    elif op == "-":
        result = a - b
    elif op == "*":
        result = a * b
    elif op == "/":
        if b == 0:
            return "计算错误：除数不能为 0"
        result = a / b
    else:
        return "不支持的运算符"

    return f"计算结果：{result:g}"
def execute_action(decision, message):
    if decision == "weather":
        return get_weather(message)

    if decision == "calculator":
        return calculator(message)

    return "暂时无法处理该指令，请尝试天气查询或计算。"
def save_history(role, content):
    history.append({
        "role": role,
        "content": content
    })
    # 表示添加到对应的字典中去
def run_agent():
    print("简单 Agent 已启动")
    print("支持天气查询、算术计算")
    print("输入\"退出\"结束程序\n")
    while True:
        try:
            message = perceive()
        except (EOFError, KeyboardInterrupt):
            print("\n程序已结束")
            break

        if not message:
            continue

        # 识别任务
        decision = make_decision(message)

        if decision == "exit":
            print("Agent：再见！")
            break

        # 保存用户输入
        save_history("user", message)

        # 执行操作
        response = execute_action(decision, message)

        # 输出结果
        print("Agent：", response)

        # 保存 Agent 回复
        save_history("assistant", response)

    # 显示本次对话历史
    print("\n本次对话历史：")

    for item in history:
        print(f"{item['role']}：{item['content']}")


if __name__ == "__main__":
    run_agent()
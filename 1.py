import os
import time
import json
import openai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ['DEEPSEEK_API_KEY'],
    base_url=os.environ.get("DEEPSEEK_API_BASE_URL"),
)

max_attempts = 3
for attempt in range(max_attempts):
    try:
        response = client.chat.completions.create(
            model='deepseek-flash',
            messages=[
                {'role': 'system',
                 'content': '你只输出 JSON，格式为 {\"name\": \"...\", \"age\": 数字}。不要输出任何其他内容。如果有多个信息，请全部输出'},
                {'role': 'user', 'content': '提取：今年已经35岁的李老师正在教三岁的张三数学。'}
            ],
            stream=True
        )
        full_content = ''
        for chunk in response:
            if chunk.choices[0].delta.content:
                piece = chunk.choices[0].delta.content
                full_content += piece
                print(piece,end='', flush=True)

        print()
        data = json.loads(full_content)
        print("解析结果:", data)
        if isinstance(data, list):
            for item in data:
                print("name =", item["name"], ", age =", item["age"])
        elif isinstance(data, dict):
            print("name =", data["name"], ", age =", data["age"])
        else:
            print("未知结构:", data)
        break
    except openai.RateLimitError:
        if attempt == max_attempts - 1:
            print(f"429重试耗尽，请稍后再试")
            raise
        wait = 2 ** attempt#指数级退避
        print(f'出发限流，{wait}秒后重试')
        time.sleep(wait)
    except openai.InternalServerError:
        if attempt == max_attempts - 1:
            print('500服务器错误，重试耗尽')
            raise
        wait = 2 ** attempt
        print(f'服务器错误，{wait}秒后重试')
        time.sleep(wait)


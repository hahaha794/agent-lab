import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from pywin.framework.toolmenu import tools
import requests

load_dotenv()

def get_weather(city: str, unit: str = "celsius") -> dict:
    """
    获取指定城市的当前天气。
    用户询问天气、气温、是否下雨时使用。
    """
    try:
        # 1. 城市名 → 经纬度（Geocoding API，免费无需 Key）
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_resp = requests.get(
            geo_url,
            params={"name": city, "count": 1, "language": "zh"},
            timeout=10,
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return {"error": f"找不到城市: {city}"}

        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]

        # 2. 按经纬度查当前天气（Forecast API，免费无需 Key）
        temp_unit = "celsius" if unit == "celsius" else "fahrenheit"
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_resp = requests.get(
            weather_url,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                "temperature_unit": temp_unit,
            },
            timeout=10,
        )
        weather_resp.raise_for_status()
        data = weather_resp.json()["current"]

        # 3. 天气代码转可读描述（WMO 标准，Open-Meteo 官方映射的简化版）
        wmo_map = {
            0: "晴", 1: "大部晴朗", 2: "部分多云", 3: "阴",
            45: "雾", 48: "沉积雾",
            51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
            61: "小雨", 63: "中雨", 65: "大雨",
            71: "小雪", 73: "中雪", 75: "大雪",
            80: "小阵雨", 81: "阵雨", 82: "强阵雨",
            95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
        }

        return {
            "city": city,
            "temperature": data["temperature_2m"],
            "feels_like": data["apparent_temperature"],
            "unit": "°C" if unit == "celsius" else "°F",
            "humidity": data["relative_humidity_2m"],
            "wind_speed": data["wind_speed_10m"],
            "description": wmo_map.get(data["weather_code"], f"未知天气代码: {data['weather_code']}"),
        }

    except requests.exceptions.Timeout:
        return {"error": f"查询 {city} 天气超时，请稍后重试。"}
    except requests.exceptions.RequestException as e:
        return {"error": f"查询天气时发生网络错误: {str(e)}"}
    except (KeyError, IndexError) as e:
        return {"error": f"天气数据解析失败: {str(e)}"}

def get_current_time()->str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def make_tool(name:str, description:str, properties:dict, required:set):
    #工厂函数生成JSON schema
    return {
        'type': 'function',
        'function':{
            'name':name,
            'description':description,
            'parameters':{
                'type': 'object',
                'properties': properties,
                'required': required,
                'additionalProperties': False
            },
            'strict': True,
        },
    }

tools = [
    make_tool(
        "get_weather",
        "获取指定城市的当前天气。用户询问天气、气温时使用。",
        {
            "city": {"type": "string", "description": "城市名，如北京"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
        },
        ["city", "unit"],
    ),
    make_tool(
        "get_current_time",
        "获取当前时间。用户问现在几点时使用。",
        {},
        [],
    ),
]

available_functions = {
    "get_weather": get_weather,
    'get_current_time':get_current_time,
}

llm = OpenAI(api_key=os.environ['DEEPSEEK_API_KEY'],
             base_url=os.environ['DEEPSEEK_API_BASE_URL'])

# ---------- 4. Agent 循环 ----------
def run(user_input: str) -> str:
    messages = [{"role": "user", "content": user_input}]

    while True:
        response = llm.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            tools=tools,
        )
        print(response.usage)
        msg = response.choices[0].message
        print(msg)

        # 情况 A：模型不调工具，直接回答 → 结束
        if not msg.tool_calls:
            return msg.content

        # 情况 B：模型要调工具
        messages.append(msg)  # 必须先把模型的调用意图加进历史

        for call in msg.tool_calls:
            func_name = call.function.name
            args = json.loads(call.function.arguments)   # 注意：是字符串，要解析

            if func_name in available_functions:
                try:
                    result = available_functions[func_name](**args)
                except Exception as e:
                    result = {"error": str(e)}
            else:
                result = {"error": f"未知工具: {func_name}"}

            # 把工具结果作为 tool 消息追加
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

        # 循环回到顶部，再请求一次，让模型根据工具结果生成最终回答

if __name__ == "__main__":
    print(run("北京现在天气怎么样？"))
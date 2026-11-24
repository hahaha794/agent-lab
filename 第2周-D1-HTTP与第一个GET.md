# D1 · HTTP 基础与第一个 GET（2 小时）

> 今天不追求"写完天气查询"，只追求三件事：
> ① 知道一个请求由什么组成 ② 能发出去并拿到 JSON ③ 知道"状态码 200 不等于成功"
>
> 今日产出：`d1_a.py`、`d1_b.py`、`d1_c.py` 三个小文件，合计 60–70 行。

---

## 一、今天的知识地图（6 块）

### 1. URL 的解剖

拿真实地址拆开看：

```
https://geocoding-api.open-meteo.com/v1/search ? name=北京 & count=1 & language=zh
└────┬────┘ └────────────┬─────────────────┘ └┬┘   └──────┬──────┘
   协议               域名                   路径        查询串（key=value&...）
```

- **协议**：`https` 表示加密的 HTTP（现在基本只用它）
- **域名**：`geocoding-api.open-meteo.com`，DNS 会把它翻译成 IP
- **路径**：`/v1/search`，服务器靠它决定走哪段逻辑
- **查询串**：`?` 后面的一串 `key=value`，多个用 `&` 连

### 2. `params` 是干什么的

`requests` 允许你把查询串写成字典：

```python
requests.get(url, params={"name": "北京", "count": 1, "language": "zh"})
```

它会**自动做 URL 编码**，把中文转成百分号形式。实测：

```
name=北京  →  name=%E5%8C%97%E4%BA%AC
```

> ⚠️ 这就是为什么**不要手拼 URL**：`url + "?name=北京"` 在有些环境下会直接报错或发出去乱码，而 `params=` 永远正确。

### 3. `Response` 对象有什么

`requests.get()` 返回的不是数据，是一个"响应对象"，你要从它身上取东西：

| 属性 / 方法 | 是什么 | 典型值 |
|---|---|---|
| `resp.status_code` | HTTP 状态码 | `200` |
| `resp.url` | 实际请求的完整地址（含编码后的参数） | `...?name=%E5%8C%97%E4%BA%AC&count=1` |
| `resp.headers` | 响应头（字典式） | `{"content-type": "application/json; charset=utf-8", ...}` |
| `resp.text` | 原始文本 | 一长串 JSON 字符串 |
| `resp.json()` | 把文本按 JSON 解析成 dict/list | `{"results": [...]}` |

**`.text` 和 `.json()` 的区别**：`.text` 永远是字符串；`.json()` 是"解析 + 转换"，内容不是合法 JSON 时会抛 `JSONDecodeError`。

### 4. `timeout` 为什么必须写

```python
requests.get(url, params=..., timeout=10)
```

- 不写 `timeout`，服务器不回应时你的程序会**一直挂着**（看起来像死机）
- 两种超时：
  - 连接超时：TCP 握不上手（断网、域名解析失败）
  - 读取超时：连上了但迟迟不返回数据
- 进阶写法（D4 细讲）：`timeout=(3, 10)` 分别指定两者

**本周铁律：任何网络请求都必须带 timeout。** 没有例外。

### 5. JSON → dict

`resp.json()` 之后，你拿到的就是普通的 `dict` / `list`，和上周 `todo.py` 里的 `json.load` 完全一样：

```python
data = resp.json()          # dict
data["results"]             # list
data["results"][0]["name"]  # str
```

区别只是：一个从文件读，一个从网络读。

### 6. ★ 今天最重要的一课：200 不等于成功

实测三个请求：

| 请求 | 状态码 | 返回内容 |
|---|---|---|
| 查「北京」 | **200** | `{"results": [{...}], "generationtime_ms": 0.2}` |
| 查「阿斯顿发」（不存在） | **200** | `{"generationtime_ms": 0.1}` ← **没有 `results` 键** |
| 访问不存在的路径 `/v1/nope` | **404** | `{"error": true, "reason": "Not Found"}` |

看第二行：**服务器认为"查询成功"，只是没找到**，所以给你 200。如果你只用 `status_code == 200` 判断成功，就会在"城市写错"时崩在 `data["results"][0]` 上（`KeyError`）。

正确姿势：

```python
results = data.get("results")        # 没有就是 None，不抛 KeyError
if not results:
    # 城市不存在，走"人话提示"分支
```

> 记住一句话：**HTTP 状态码是"传输层"的结论，业务是否成功要自己判断。**

---

## 二、代码练习（3 个，递进）

> 全部放在 `study\` 下，命名 `d1_a.py` / `d1_b.py` / `d1_c.py`。
> 只用 `requests`，不引入别的库。每个文件写完都要**真的跑起来**再往下走。

### 练习 1：`d1_a.py`（10–15 行，跟写）

**目标**：把"响应对象"拆开看一遍。

**要求**
1. 用 `requests.get` 查 `https://geocoding-api.open-meteo.com/v1/search`，参数 `name=北京, count=1, language=zh`
2. 必须带 `timeout=10`
3. 依次打印：
   - `resp.status_code`
   - `resp.url`（看清中文被编码成什么）
   - `resp.headers.get("content-type")`
   - `resp.text` 的前 200 个字符（用切片 `[:200]`）
4. 最后打印 `type(resp.json())` 和 `len(resp.json()["results"])`

**验收**
```
200
https://geocoding-api.open-meteo.com/v1/search?name=%E5%8C%97%E4%BA%AC&count=1&language=zh
application/json; charset=utf-8
{"results":[{"id":1816670,"name":"北京",...
<class 'dict'> 1
```

**提示**
- 打印 `resp.text[:200]` 时，输出会被截断到一行，属正常
- `.json()` 调两次会解析两遍，实际项目里先存进变量（`data = resp.json()`）

---

### 练习 2：`d1_b.py`（约 30 行，自己写）

**目标**：把"城市 → 经纬度"封装成函数，并且**正确处理查不到**。

**要求**
```python
def search_city(name: str, timeout: float = 10) -> tuple[float, float] | None:
    """返回 (纬度, 经度)；找不到城市返回 None。"""
```

- 内部：`requests.get(..., params={"name": name, "count": 1, "language": "zh"}, timeout=timeout)`
- 拿到 JSON 后：用 `data.get("results")` 判断，**没有就返回 None**（不要抛异常，也不要打印）
- 有结果就返回 `(results[0]["latitude"], results[0]["longitude"])`
- 在 `if __name__ == "__main__":` 里测三个城市：
  - `北京` → `(39.9075, 116.39723)`
  - `Beijing` → 也应该能查到
  - `阿斯顿发` → `None`

**验收**
```
北京      -> (39.9075, 116.39723)
Beijing   -> (39.9042, 116.4074)     ← 数值可能略有不同，能返回坐标即可
阿斯顿发   -> None
```

**提示**
- 函数只负责"查并返回"，**不要在函数里 print** —— 打印是调用方的事
- 返回 `tuple` 而不是 `list`：坐标是固定两个值，用元组更贴切
- 类型注解写全（`str` / `float` / `tuple[float, float] | None`）

**不要做的事**
- ❌ 不要用 `except Exception` 一把抓（今天是 D1，只处理"没找到"，网络异常留给 D3）
- ❌ 不要 `data["results"]` 直接取（查不到就 KeyError）

---

### 练习 3：`d1_c.py`（约 30 行，自己写）

**目标**：把练习 2 变成一个小命令行工具，能反复查。

**要求**
1. `while True` 循环读输入：`input("城市名（q 退出）> ")`
2. 输入 `q` / `quit` / `exit` → 打印"再见"并 `break`
3. 空输入 → `continue`，不查询
4. 查到 → `print(f"{city} 的坐标：纬度 {lat:.4f}，经度 {lon:.4f}")`
5. 查不到 → `print(f"找不到城市「{city}」，试试英文名或拼音")`
6. 保留练习 2 的 `search_city`（复制过来即可）

**验收（完整交互）**
```
城市名（q 退出）> 北京
北京的坐标：纬度 39.9075，经度 116.3972
城市名（q 退出）> Beijing
Beijing 的坐标：纬度 39.9042，经度 116.4074
城市名（q 退出）> 阿斯顿发
找不到城市「阿斯顿发」，试试英文名或拼音
城市名（q 退出）>
城市名（q 退出）> q
再见
```

注意第 4 步：空输入只是重新提示，**不查也不报错**。

**加分项（有余力再做）**
把查到的城市缓存进 `cities.json`（`{"北京": [39.9075, 116.39723]}`），下次先查缓存，命中就不发请求。这就是"缓存"最原始的形态。

---

## 三、D1 四个专属坑

| # | 坑 | 现象 | 正确做法 |
|---|---|---|---|
| 1 | 忘写 `timeout` | 网络差时程序一直挂着 | 每个 `requests.get` 都带 `timeout=10` |
| 2 | 手拼 URL | 中文乱码或参数丢 | 用 `params={...}` |
| 3 | `resp.json()` 不判断 | 断网时返回 HTML 错误页 → `JSONDecodeError` | 先看 `content-type` 或捕获（D3 细讲） |
| 4 | **把 200 当成功** | 查不到城市时 `KeyError: 'results'` | `data.get("results")` 判空 |

第 4 个是今天唯一必须彻底搞懂的，因为它决定了你后面三天的代码结构。

---

## 四、20 分钟文档阅读（别通读）

只读这三节，边读边在 `d1_a.py` 里验证：

- [requests 官方 · Make a Request](https://requests.readthedocs.io/en/latest/user/quickstart/#make-a-request)
- [Passing Parameters In URLs](https://requests.readthedocs.io/en/latest/user/quickstart/#passing-parameters-in-urls)
- [Response Status Codes](https://requests.readthedocs.io/en/latest/user/quickstart/#response-status-codes)

---

## 五、收工标准（今天结束前必须满足）

- [ ] `python d1_a.py` 能跑，看到 200、编码后的 URL、content-type
- [ ] `python d1_b.py` 三个城市结果正确（北京/Beijing 有坐标，阿斯顿发是 None）
- [ ] `python d1_c.py` 完整交互符合验收（含空输入、q 退出）
- [ ] 能回答："为什么查一个不存在的城市，状态码还是 200？"
- [ ] 三个文件里每一处 `requests.get` 都带 `timeout`

---

## 六、今日复盘（写在笔记里，一句话就够）

1. 今天跑起来的东西是什么？
2. "200 不等于成功"这句话，你能用自己的话解释一遍吗？
3. 明天（D2：状态码 + `raise_for_status`）要交付什么？

# D5 · 从下往上读 traceback（1.5 小时）

> 目标：看到一屏红字，30 秒内说出 **"哪个文件、第几行、什么原因、怎么改"**。
> 产出：`d5_a.py`（六种错误制造机）、`d5_b.py`（三层调用链实验）、一张自己的"报错速查卡"。
> 素材说明：本文的案例全部来自你这两周真实出现过的报错。

---

## 一、traceback 到底长什么样

以你 `d2_c.py` 曾经那个 `KeyError` 为例：

```text
Traceback (most recent call last):
  File "d2_c.py", line 47, in <module>          ← ① 入口：谁启动了这串调用
    main()
  File "d2_c.py", line 52, in main              ← ② 上一层调用
    data = lookup_city(name, 10)
  File "d2_c.py", line 21, in lookup_city       ← ③ 真正出错的行（倒数第一个你自己的文件）
    if data['results']:
       ~~~~~~~~^^^^^^^
KeyError: 'results'                             ← ④ 异常类型 + 消息
```

**四块，只要读三块**：

| 位置 | 内容 | 要不要看 |
|---|---|---|
| 最后一行 | `异常类型: 消息` | **必看** —— 告诉你"什么错" |
| 倒数第一个**你的文件**那一段 | 文件名 + 行号 + 那行代码 | **必看** —— 告诉你"哪一行" |
| 中间的库代码（`requests/`、`urllib3/`、`http/client.py`…） | 三方库内部 | 跳过（除非怀疑库有 bug） |
| 最上面几段 | 调用从哪来的 | 出问题时才往上追 |

**一句话口诀：从下往上读，最后一行定性质，倒数第一个自己的文件定位置。**

---

## 二、四种异常消息，看懂就赢一半

### ① `ModuleNotFoundError: No module named 'xxx'`

```
ModuleNotFoundError: No module named 'requests'
```

不是代码写错，是**这个包没装在这台机器的这个 Python 里**。

```powershell
python -c "import requests; print(requests.__file__)"   # 看路径里有没有 .venv
```

### ② `AttributeError: 'NoneType' object has no attribute 'xxx'`

```
AttributeError: 'NoneType' object has no attribute 'text'
```

翻译：**"你从一个 `None` 身上取 `.text`"**。不是 `.text` 写错了，是**点号前面那个东西是 None**。

你这两周遇到的所有 `e.response.text` 崩溃都属于这一类 —— 因为 `Timeout` / `ConnectionError` 的 `.response` 是 `None`。

> 记法：`'X' object has no attribute 'Y'` 里的 **X 才是问题所在**，Y 只是受害者。

### ③ `KeyError: 'xxx'` / `IndexError: list index out of range`

```
KeyError: 'results'          # 字典里没有这个键
IndexError: list index out of range   # 列表长度不够
```

翻译：**"你以为有的东西，其实没有"**。对应改法就是 `.get()` / 先判长度。

### ④ `TypeError: Object of type xxx is not JSON serializable`

```
TypeError: Object of type datetime is not JSON serializable
```

翻译：**`json.dump` 只认 6 种类型**（dict/list/str/int/float/bool/None），`datetime` 不在里面。要么转字符串，要么写 `default=`。

---

## 三、十二类常见报错速查表

| 最后一行 | 真实含义 | 第一反应 |
|---|---|---|
| `ModuleNotFoundError: No module named 'x'` | 包没装 / 装到别的 Python | 查 `x.__file__` 里有没有 `.venv` |
| `AttributeError: 'NoneType' object has no attribute 'y'` | 点号前是 `None` | 先打印那个对象 |
| `AttributeError: 'str' object has no attribute 'y'` | 该是对象的地方给了字符串 | 检查类型转换 |
| `KeyError: 'k'` | 字典没这个键 | 用 `.get()`，或先打印 `list(d)` |
| `IndexError: list index out of range` | 列表太短 | 先判空 / 判断长度 |
| `TypeError: ... not JSON serializable` | json 不支持这个类型 | 转 `str` 或写 `default=` |
| `TypeError: unsupported operand type(s) for +` | 类型不匹配（如 Path + str） | 转成同一类型 |
| `ValueError: invalid literal for int()` | `int("abc")` | 先校验/捕获 |
| `json.decoder.JSONDecodeError` | 内容不是 JSON（常见于 HTML 错误页） | 打印 `resp.text[:200]` |
| `requests.exceptions.ConnectionError` | 连不上（DNS/拒绝/断网） | 检查域名、网络 |
| `requests.exceptions.ReadTimeout` | 连上了但不返回 | 加大 timeout 或查服务端 |
| `PermissionError: [Errno 13] Permission denied` | 文件/目录没权限 | 检查路径、ACL、是否被占用 |
| `UnicodeDecodeError: 'gbk' codec can't decode` | 读文件没指定 `encoding="utf-8"` | 补 `encoding` |
| `SyntaxError` / `IndentationError` | 编译期错误，**没有 traceback** | 看 `^` 指的那一行 |

---

## 四、异常链：三段式（最容易读错的地方）

当你看到 `During handling of the above exception...`，说明**在异常处理里又炸了一个异常**。

你 `d3_b.py` 曾经的真实链路：

```text
ConnectionRefusedError: [WinError 10061] 由于目标计算机积极拒绝，无法连接。   ← 第 1 段：最底层
    ...
The above exception was the direct cause of the following exception:
requests.exceptions.ConnectionError: HTTPConnectionPool(host='127.0.0.1', port=9): Max retries exceeded
    ...
During handling of the above exception, another exception occurred:
AttributeError: 'NoneType' object has no attribute 'text'                     ← 第 3 段：真正炸的
  File "d3_b.py", line 19, in probe
    print(f"ERROR:{e.response.text}")
```

**读法：从最后一段往上倒**。

1. 最后一段 `AttributeError` = "程序是死在这里的"（你的 `except` 分支）
2. 它上面说 `During handling of ... another exception` = "处理上一个异常时又炸了"
3. 再往上 `ConnectionError` = 最初真正发生的事（断网）
4. 最上面 `ConnectionRefusedError` = 更底层的原因（端口拒绝）

**最终结论**：不是"网络问题"，而是"网络错误发生后，我的异常处理代码自己崩了"。修的地方是 `except` 分支，不是网络。

> 这也是为什么 D3 要求你写 `raise ... from e` —— 它会让"根因"和"新异常"之间的因果关系在 traceback 里显式呈现。

---

## 五、五个真实案例（你这次遇到的）

### 案例 1

```text
  File "d4_c.py", line 43, in fetch_once
    retry_after=_parse_retry_after(e.response)) from e
NameError: name '_parse_retry_after' is not defined
```

- 什么错：名字没定义
- 哪一行：`d4_c.py:43`
- 原因：调用了不存在的函数（只在 429/5xx 分支才会走到，所以平时不出现）
- 改法：定义它，或改成已存在的名字

**教训**：这类错误**只在你没测到的那条分支上出现** —— 测试用例没覆盖，它就一直潜伏。

### 案例 2

```text
  File "d2_b.py", line 19, in probe
    print(f"ERROR:{e.response.status_code}:{e.response.reason}")
AttributeError: 'NoneType' object has no attribute 'status_code'
```

- 什么错：从 `None` 取属性
- 哪一行：`d2_b.py:19`（在 `except ConnectionError` 分支里）
- 原因：`ConnectionError.response` 是 `None`
- 改法：这一分支不要碰 `e.response`，用 `str(e)`

### 案例 3

```text
  File "d2_c.py", line 21, in lookup_city
    if data['results']:
KeyError: 'results'
```

- 什么错：字典没这个键
- 原因：城市查不到时，服务端返回 200 + `{"generationtime_ms": ...}`，**没有 `results`**
- 改法：`data.get('results')`

### 案例 4

```text
  File "todo.py", line 20, in save
    json.dump(todos, f, ensure_ascii=False, indent=2)
TypeError: Object of type datetime is not JSON serializable
```

- 什么错：不可序列化
- 原因：`created_at` 存的是 `datetime.now()` 对象
- 改法：`.isoformat()` 转字符串

### 案例 5（不是代码问题）

```text
  File ".../urllib3/util/ssl_.py", line 359, in create_urllib3_context
    context.keylog_filename = sslkeylogfile
PermissionError: [Errno 13] Permission denied: 'D:\\study\\client\\sslkeys.log'
```

- 什么错：没权限
- 哪一行：**是库的代码**，不是你写的
- 真正原因：系统环境变量 `SSLKEYLOGFILE` 指向一个被占用的 725 MB 文件
- 改法：删掉/改写这个环境变量，不是改 Python 代码

**教训**：当 traceback 里**没有你的文件**时，问题通常在**环境**（环境变量、权限、依赖版本），这时候改代码是白费力气。

---

## 六、四个练习

### 练习 1：`d5_a.py` —— 六种错误制造机（约 40 行）

**目标**：亲眼看到"捕获后 traceback 还在"。

**要求**

```python
import traceback

def boom(kind: str) -> None:
    """按 kind 制造对应异常。"""
```

六种：`KeyError`、`IndexError`、`AttributeError`（None 上取属性）、`TypeError`（json 序列化 datetime）、`ValueError`（`int("abc")`）、`ZeroDivisionError`。

主循环里逐个执行，**同时打印两种输出**：

```python
for kind in [...]:
    try:
        boom(kind)
    except Exception as e:
        print("=" * 60)
        print(f"[{kind}]")
        print(f"  print(e)          -> {e}")                 # 只有一行
        print(f"  format_exc()      -> ")                    # 完整栈
        print(traceback.format_exc())
```

**验收**：能说出 `print(e)` 和 `traceback.format_exc()` 差了多少信息（差别就在"文件+行号"）。

### 练习 2：`d5_b.py` —— 三层调用链（约 30 行）

**要求**：写 `level3()` 里制造一个 `ValueError`，由 `level2()` → `level1()` → `main()` 逐层调用，**不捕获**，让它自然抛出。

**验收**：能指出 traceback 里哪一段是 `level1`、哪一段是 `level3`，并说出"倒数第一个自己的文件"是哪一行。

### 练习 3：盲读卡片（不用写代码）

读下面五段 traceback，各写一行结论：**哪个文件哪一行 / 什么原因 / 怎么改**。答案在文末。

**卡片 A**

```text
Traceback (most recent call last):
  File "d1_a.py", line 6, in <module>
    import requests
ModuleNotFoundError: No module named 'requests'
```

**卡片 B**

```text
Traceback (most recent call last):
  File "L1.py", line 90, in main
    min_file = {"文件名字": str(sorted_files[-1][0]), ...}
IndexError: list index out of range
```

**卡片 C**

```text
Traceback (most recent call last):
  File "weather_draft.py", line 12, in build_url
    url = args.dir + "/weather"
TypeError: unsupported operand type(s) for +: 'WindowsPath' and 'str'
```

**卡片 D**

```text
Traceback (most recent call last):
  File "d2_a.py", line 10, in show
    r = requests.get(usl, params=parms)
requests.exceptions.ConnectionError: HTTPConnectionPool(host='httpbin.org', port=80): Max retries exceeded
```

**卡片 E**

```text
Traceback (most recent call last):
  File "todo_min.py", line 22, in load
    data = json.load(f)
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

### 练习 4（选做）：`logging` 对比

把 `print(traceback.format_exc())` 换成 `logging.exception("查询失败")`，比较输出差异（多了时间戳、级别、logger 名）。第 15 周接 trace 工具时就是从这个入口进去的。

---

## 七、五个坑

1. **把 traceback 直接甩给用户** —— 用户看不懂，等于没处理。用户只该看到"连不上网络，请检查 Wi-Fi"，traceback 进日志。
2. **只看最后一行、不看行号** —— 同一个 `KeyError` 可能来自十处，行号才是定位。
3. **忽略 `During handling of ...`** —— 会把"异常处理自己崩了"误判成"原始业务错误"。
4. **`except Exception: pass`** —— 把 traceback 彻底吞掉，问题变成"什么都没发生"。
5. **`print(e)` 代替 `format_exc()`** —— 只留一行消息，丢了文件、行号、调用链，线上排障时几乎没用。

---

## 八、工具箱

| 工具 | 用途 |
|---|---|
| `traceback.format_exc()` | 返回完整栈字符串（存日志用） |
| `traceback.print_exc()` | 直接打印完整栈 |
| `logging.exception("...")` | 在 `except` 里记日志，自动带栈 + 时间戳 + 级别 |
| `traceback.format_exc(limit=3)` | 只要最近 3 层（日志太长时） |
| `python -X faulthandler 脚本.py` | 进程崩死（段错误/卡死）时转储所有线程栈 |
| `breakpoint()` | 3.7+ 内置调试器，进入现场看变量 |
| `raise`（裸） | 重新抛出，保留原栈 |
| `raise X from e` | 转换异常，同时保留因果链 |

---

## 九、时间分配（1.5 小时）

| 分钟 | 做什么 |
|---|---|
| 0–20 | 读本文第一~四节 + 速查表 |
| 20–50 | 练习 1（六种错误制造机） |
| 50–70 | 练习 2（三层调用链） |
| 70–85 | 练习 3（盲读五张卡片） |
| 85–90 | 写下自己的"报错速查卡"（把这两周遇到的真实报错各写一行） |

---

## 十、收工标准

- [ ] 能不看代码说出 traceback 的"四块结构"
- [ ] 看到 `AttributeError: 'NoneType' object has no attribute 'x'` 能立刻定位到"点号前面是 None"
- [ ] 练习 1 里能说出 `print(e)` 与 `format_exc()` 的差别
- [ ] 能读懂 `During handling of the above exception` 的三段式
- [ ] 盲读五张卡片全对
- [ ] 已写下自己的报错速查卡（至少 5 条真实报错）

## 十一、复盘三问

1. 今天跑起来的东西是什么？
2. 以后遇到"traceback 里没有我的文件"时，你该查什么？
3. 下周（第 3 周：文件与字符串 / notes 关键词搜索）要交付什么？

---

## 附：盲读卡片答案

**卡片 A**
- 位置：`d1_a.py:6`
- 原因：`requests` 没装在这个 Python 里（或装到了全局）
- 改法：`.\.venv\Scripts\python.exe -m pip install requests`，再用 `requests.__file__` 确认路径含 `.venv`

**卡片 B**
- 位置：`L1.py:90`
- 原因：`--ext` 没匹配到文件时 `sorted_files` 是空列表，取 `[-1]` 越界
- 改法：取值前判空（`if not sorted_files: ...`）

**卡片 C**
- 位置：`weather_draft.py:12`
- 原因：`Path` 和 `str` 不能相加（典型写法：`args.dir + "/weather"`，而 `args.dir` 是 `Path`）
- 改法：用 `/` 拼路径 `args.dir / "weather"`，或显式 `str(args.dir) + "/weather"`

**卡片 D**
- 位置：`d2_a.py:10`
- 原因：连不上 `httpbin.org`（网络/被墙/DNS），不是代码逻辑错
- 改法：换可达的地址；给请求加 `timeout`；把网络异常单独处理

**卡片 E**
- 位置：`todo_min.py:22`
- 原因：`todos.json` 是空文件或内容损坏（`json.load` 在空文件上也抛这个）
- 改法：捕获 `json.JSONDecodeError` 并降级为空列表；提示用户文件已损坏

# -*- coding: utf-8 -*-
"""生成《Agent 开发 16 周周计划表》.xlsx（可打印 + 可勾选）"""

import math
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

OUT = r"C:\Users\admin\Desktop\agent study\Agent开发周计划表.xlsx"

FONT = "微软雅黑"
NAVY = "1F3864"
HEADER_BG = "1F4E79"
GREY_TEXT = "595959"

STAGE_FILL = {
    "0 环境": "E8F0FE",
    "1 编程地基": "FFF4E0",
    "2 LLM 基本功": "E6F4EA",
    "3 手写 Agent": "FDE7E9",
    "4 记忆与 RAG": "F0EAFB",
    "5 框架/MCP": "E0F7FA",
    "6 评估与安全": "FFF0F5",
    "7 上线": "EDEDED",
}

THIN = Side(style="thin", color="D0D7E5")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


# ---------------------------------------------------------------- 数据
WEEKS = [
    ("第 0 周", "0 环境", "环境就绪", "今天就让代码跑起来",
     "装 VS Code、建 venv、装依赖、申请 API Key；key 写进 .env 并加入 .gitignore",
     '打印出模型返回的"你好"', 2,
     "终端能看到模型回复；.gitignore 已包含 .env"),

    ("第 1 周", "1 编程地基", "Python 最小集", "能写出会存数据的脚本",
     "变量与类型、list/dict、if/for、函数、f-string、json 读写",
     "命令行待办清单（增删改查 + 存盘）", 10,
     "不抄教程能独立写完；关掉重开数据还在"),

    ("第 2 周", "1 编程地基", "调 API 与异常", "程序出错也不崩溃",
     "requests/httpx、状态码、超时设置、try/except、从下往上读 traceback",
     "天气或汇率查询 CLI，含超时与友好报错", 10,
     "断网、城市名写错时不崩，给出人话提示"),

    ("第 3 周", "1 编程地基", "文件与字符串", "能让程序读你的资料",
     "pathlib 路径、open 读写、遍历目录、split/replace、正则入门",
     "notes 目录关键词搜索（输出文件名 + 行号）", 10,
     "能搜出命中段落并标出文件与行号"),

    ("第 4 周", "1 编程地基", "模块化与 Git", "代码能给别人看",
     "类型注解、docstring、模块拆分、git add/commit/push、README 写法",
     "mytools.py（4 个带注解的工具函数）并推上 GitHub", 10,
     "每个函数有注解和 docstring；clone 下来就能跑"),

    ("第 5 周", "2 LLM 基本功", "认识模型", "搞懂 token、角色、温度、计费",
     "token 与上下文窗口、system/user/assistant 四种角色、temperature、stream 流式、输入输出分开计费",
     "流式聊天机器人（多轮 + /clear + /cost）", 10,
     "能解释温度调高会怎样；能算出这次对话花了多少钱"),

    ("第 6 周", "2 LLM 基本功", "结构化输出", "让模型稳定交出 JSON",
     "JSON 模式与 response_format、Pydantic 校验、失败重试、few-shot、提示词四条铁律",
     "JD 文本 → Pydantic 结构体（岗位/城市/薪资/技能）", 10,
     "20 条不同输入下都能返回合法 JSON"),

    ("第 7 周", "3 手写 Agent", "工具调用原理 ★", "第一次让模型真的动手",
     "function calling 全流程、JSON Schema 写法、tool_call_id 必须对应、组装-调用-判断-执行-回填",
     "跑通 01_minimal_agent.py --selftest 并读懂每一行", 12,
     "合上代码能口述完整消息序列（含 role 与 id）"),

    ("第 8 周", "3 手写 Agent", "工程化 ★", "让它稳、不死、不烧钱",
     "max_steps 防死循环、异常当观察结果回传、并行工具调用、历史压缩、工具设计五原则",
     "4–5 个工具的个人助理（手写循环，禁止框架）", 12,
     "工具报错能自愈；白板画出 3 步调用的完整流程"),

    ("第 9 周", "4 记忆与 RAG", "RAG 上手", "让它读得懂你的资料",
     "embedding 原理、切分策略、Chroma 向量库、检索 top-k、来源引用、拒答设计",
     "本地知识库问答（20 份 md/pdf，带来源标注）", 10,
     "回答必带来源；资料里没有就答\"未提及\""),

    ("第 10 周", "4 记忆与 RAG", "检索调优与评估", "用数据代替感觉",
     "chunk 与 top-k 取舍、BM25+向量混合检索、rerank、召回率@k、忠实度、Lost in the Middle",
     "20–30 条 eval 问题 + 检索评估表（含召回率）", 10,
     "答错时能判断是\"没检索到\"还是\"检索到了答歪了\""),

    ("第 11 周", "5 框架/MCP", "框架重构", "看懂别人怎么工程化",
     "LangGraph 或 OpenAI Agents SDK（二选一）、节点与状态、持久化、超时重试",
     "用框架重写第 8 周的助理，支持关掉重开继续聊", 10,
     "能说清框架版与手写版各自多做了什么"),

    ("第 12 周", "5 框架/MCP", "人工介入与 MCP", "危险动作要有人点头",
     "human-in-the-loop 审批节点、MCP 是什么、client/server、stdio 与 HTTP、tools/resources/prompts",
     "高危工具加审批 + 自己写一个 MCP server", 10,
     "MCP server 能被客户端调通；审批能暂停与恢复"),

    ("第 13 周", "5 框架/MCP", "多智能体与选型", "知道什么时候不该拆",
     "supervisor/pipeline/debate 三种拓扑、成本与错误传播、六个框架取舍对比",
     '一页技术选型说明（含"为什么不用多智能体"）', 10,
     "能举出具体不该用多智能体的例子并说明理由"),

    ("第 14 周", "6 评估与安全", "建立评估体系", '把"感觉变好了"变成数字',
     "golden set 设计（正常/边界/对抗）、规则断言优先、LLM-as-judge 与 rubric、回归测试",
     "eval.py（跑完输出通过率表格）", 10,
     "改一次 prompt，能量化说出通过率涨了还是跌了"),

    ("第 15 周", "6 评估与安全", "可观测与安全 ★", "上线前先学会防",
     "Langfuse trace 全链路、提示词注入（尤其是间接注入）、工具最小权限、输出校验、成本熔断",
     "trace 看板 + SECURITY.md + 一次注入攻击复现", 10,
     "复现一次注入并挡住它；算出 1000 次调用要多少钱"),

    ("第 16 周", "7 上线", "部署上线", "让别人能用上",
     "FastAPI + SSE 流式、Docker 打包、鉴权与限流、结构化日志、Streamlit 前端",
     "公网可访问的 URL + README + 3 分钟演示视频", 12,
     "别人打开链接就能正常使用"),
]

HEADERS = ["周次", "阶段", "本周主题", "本周目标", "具体学习内容",
           "动手任务 / 交付物", "工时", "过关标准（自查才准进入下一周）",
           "完成", "完成日期", "踩坑与复盘"]
WIDTHS = [8, 13, 16, 20, 34, 24, 6, 26, 6, 11, 20]


def text_units(s):
    """中文字符算 2 个单位宽度，英文算 1"""
    return sum(2 if ord(c) > 127 else 1 for c in str(s))


def fit_row_height(values, widths, min_h=20, line_h=14.5):
    lines = 1
    for val, w in zip(values, widths):
        if val is None:
            continue
        units = text_units(val)
        per_line = max(w - 1.5, 4)
        lines = max(lines, math.ceil(units / per_line))
    return max(min_h, lines * line_h + 8)


def style_title(ws, text, sub, ncols):
    last = get_column_letter(ncols)
    ws.merge_cells(f"A1:{last}1")
    c = ws["A1"]
    c.value = text
    c.font = Font(name=FONT, size=17, bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor=NAVY)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 38

    ws.merge_cells(f"A2:{last}2")
    c = ws["A2"]
    c.value = sub
    c.font = Font(name=FONT, size=9, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor="2E5C8A")
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 22


def style_header(ws, row, headers):
    for i, h in enumerate(headers, start=1):
        c = ws.cell(row=row, column=i, value=h)
        c.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=HEADER_BG)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER
    ws.row_dimensions[row].height = 30


def page_setup(ws, area, orientation="landscape", paper=9, rows=None):
    ws.print_area = area
    ws.page_setup.orientation = orientation
    ws.page_setup.paperSize = paper          # 9 = A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins.left = ws.page_margins.right = 0.3
    ws.page_margins.top = ws.page_margins.bottom = 0.4
    if rows:
        ws.print_title_rows = rows


# ---------------------------------------------------------------- 表1 周计划
def build_plan(wb):
    ws = wb.create_sheet("周计划表")
    ncols = len(HEADERS)
    style_title(
        ws,
        "Agent 开发 · 16 周周计划表",
        "每周 10 小时 ≈ 168 小时 ｜ 共 17 个周期（含第 0 周） ｜ ▸ 完成列可下拉选择 ✔ ｜ "
        "打印设置：A4 横向、1 页宽",
        ncols,
    )
    for i, w in enumerate(WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    style_header(ws, 3, HEADERS)

    r = 4
    for wk in WEEKS:
        no, stage, topic, goal, content, deliver, hours, pass_std = wk
        values = [no, stage, topic, goal, content, deliver, hours, pass_std, "□", "", ""]
        fill = PatternFill("solid", fgColor=STAGE_FILL[stage])

        for i, v in enumerate(values, start=1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = Font(name=FONT, size=10, color="1A1A1A")
            c.border = BORDER
            c.fill = fill
            if i in (1, 2, 7, 9):
                c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            elif i in (3, 4):
                c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            elif i in (10,):
                c.alignment = Alignment(horizontal="center", vertical="center")
                c.number_format = "yyyy-mm-dd"
            else:
                c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        # 关键周加粗
        if "★" in topic:
            for i in (1, 3, 4, 8):
                ws.cell(row=r, column=i).font = Font(name=FONT, size=10, bold=True, color="C00000")

        ws.cell(row=r, column=1).font = Font(name=FONT, size=10, bold=True, color="1A1A1A")
        ws.row_dimensions[r].height = fit_row_height(values, WIDTHS)
        r += 1

    last = r - 1

    # 合计行
    ws.merge_cells(f"A{r}:F{r}")
    c = ws[f"A{r}"]
    c.value = "合计投入时间（小时）"
    c.font = Font(name=FONT, size=10, bold=True, color=NAVY)
    c.alignment = Alignment(horizontal="right", vertical="center", indent=1)

    total = sum(w[6] for w in WEEKS)
    c = ws.cell(row=r, column=7, value=total)
    c.font = Font(name=FONT, size=11, bold=True, color="C00000")
    c.alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells(f"H{r}:K{r}")
    c = ws[f"H{r}"]
    c.value = "每周 20 小时 → 8~9 周；每周 5 小时 → 约 32 周。阶段 3 和阶段 6 不建议压缩。"
    c.font = Font(name=FONT, size=9, color=GREY_TEXT)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)

    for i in range(1, ncols + 1):
        ws.cell(row=r, column=i).border = BORDER
        ws.cell(row=r, column=i).fill = PatternFill("solid", fgColor="DCE6F1")
    ws.row_dimensions[r].height = 26

    # 下拉选项
    dv = DataValidation(type="list", formula1='"□,✔"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"I4:I{last}")

    ws.freeze_panes = "A4"
    ws.sheet_view.showGridLines = False
    page_setup(ws, f"A1:K{r}", rows="3:3")
    return ws


# ---------------------------------------------------------------- 表2 每日节奏
def build_daily(wb):
    ws = wb.create_sheet("每日节奏")
    headers = ["场景", "时间段", "时长", "做什么", "要点"]
    widths = [14, 18, 10, 40, 46]
    style_title(
        ws, "每日 / 每周节奏模板",
        "学习效果 = 写代码的天数 × 每天专注的分钟数，而不是看视频的时长", len(headers)
    )
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    style_header(ws, 3, headers)

    rows = [
        ("工作日", "第 1 段", "20 分钟", "读官方文档 / 昨天的复盘笔记", "只读要用的那 2 页，不要从头读到尾"),
        ("工作日", "第 2 段", "50 分钟", "写代码（关掉视频，边写边查）", "今天要跑起来的东西先写出来，再优化"),
        ("工作日", "第 3 段", "20 分钟", "修 bug + 记录踩坑", "每条踩坑写成一句话，周末复盘用"),
        ("周末", "上午", "2–3 小时", "推进本周项目（交付物）", "周日结束前必须有能跑的东西"),
        ("周末", "下午", "2 小时", "补没懂的概念 + 重构上周代码", "重构是理解最快的方式"),
        ("周末", "傍晚", "30 分钟", "写周复盘（三问）+ 更新打卡表", "写不出 200 字，说明这周没真的学"),
    ]
    r = 4
    band = ["FFFFFF", "F7F9FC"]
    for idx, row in enumerate(rows):
        fill = PatternFill("solid", fgColor=band[0] if row[0] == "工作日" else band[1])
        for i, v in enumerate(row, start=1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = Font(name=FONT, size=10, color="1A1A1A")
            c.fill = fill
            c.border = BORDER
            c.alignment = Alignment(
                horizontal="center" if i in (1, 2, 3) else "left",
                vertical="center", wrap_text=True)
        ws.row_dimensions[r].height = fit_row_height(row, widths)
        r += 1

    # 三问
    r += 1
    ws.merge_cells(f"A{r}:E{r}")
    c = ws[f"A{r}"]
    c.value = "每周日 30 分钟：复盘三问"
    c.font = Font(name=FONT, size=12, bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor=HEADER_BG)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[r].height = 28

    questions = [
        "1. 这周我做出了什么能跑的东西？（写不出 → 这周白学）",
        "2. 哪个概念我其实还没真懂？（下周第一天补掉它）",
        "3. 下周要交付的具体是什么？（一句话，可验证）",
    ]
    r += 1
    for q in questions:
        ws.merge_cells(f"A{r}:E{r}")
        c = ws[f"A{r}"]
        c.value = q
        c.font = Font(name=FONT, size=10, color="1A1A1A")
        c.fill = PatternFill("solid", fgColor="FFF9E6")
        c.alignment = Alignment(horizontal="left", vertical="center", indent=2)
        for i in range(1, 6):
            ws.cell(row=r, column=i).border = BORDER
        ws.row_dimensions[r].height = 26
        r += 1

    # 铁律
    r += 1
    ws.merge_cells(f"A{r}:E{r}")
    c = ws[f"A{r}"]
    c.value = "三条铁律"
    c.font = Font(name=FONT, size=12, bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor="C00000")
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[r].height = 28

    rules = [
        "① 每周至少 5 天碰代码 —— 看视频会产生「我已经会了」的幻觉。",
        "② 学完一个概念立刻写 20 行验证它 —— 不验证等于没学。",
        "③ 每周产出一次可运行的东西 —— 能跑的 demo 比精美的笔记值钱 100 倍。",
    ]
    r += 1
    for t in rules:
        ws.merge_cells(f"A{r}:E{r}")
        c = ws[f"A{r}"]
        c.value = t
        c.font = Font(name=FONT, size=10, color="1A1A1A")
        c.alignment = Alignment(horizontal="left", vertical="center", indent=2, wrap_text=True)
        for i in range(1, 6):
            ws.cell(row=r, column=i).border = BORDER
        ws.row_dimensions[r].height = 24
        r += 1

    ws.sheet_view.showGridLines = False
    page_setup(ws, f"A1:E{r}")
    return ws


# ---------------------------------------------------------------- 表3 打卡清单
CHECKLIST = [
    ("0 环境", ["venv 建好，pip list 能看到 openai",
               "拿到 API Key，.env 写好且已加入 .gitignore",
               "成功打印出模型返回的「你好」"]),
    ("1 编程地基", ["待办清单 CLI 能增删改查并存盘",
                  "调通一个公开 API（含超时与异常处理）",
                  "本地文件关键词搜索脚本",
                  "mytools.py 四个函数带类型注解与 docstring",
                  "代码已推到 GitHub，README 能看懂"]),
    ("2 LLM 基本功", ["流式聊天机器人 + /clear + /cost",
                    "JD 文本能解析成 Pydantic 结构体",
                    "校验失败会自动重试",
                    "能解释 token、上下文窗口与计费规则"]),
    ("3 手写 Agent ★", ["跑通 01_minimal_agent.py --selftest",
                      "手写版能真实对话（联网）",
                      "自己加了 2 个工具",
                      "白板画出完整消息流（role + tool_call_id）",
                      "工具报错时 Agent 能自愈",
                      "加了 max_steps，不会死循环烧钱"]),
    ("4 记忆与 RAG", ["20 份文档入库，能带来源回答",
                    "资料里没有时会明确说「未提及」",
                    "20 条 eval 问题，算出召回率",
                    "混合检索或 rerank 至少上了其中一个",
                    "能判断一次答错是检索问题还是生成问题"]),
    ("5 框架/MCP", ["用框架重构，支持关掉重开继续聊",
                  "高危工具有人工审批节点，可暂停/恢复",
                  "自己的 MCP server 能被客户端成功调用",
                  "能说清 2 个框架的取舍",
                  "能举出「不该用多智能体」的具体例子"]),
    ("6 评估与安全", ["golden set 凑够 30 条（含对抗样本）",
                   "eval.py 能输出通过率表格",
                   "接入 Langfuse，能看到全链路 trace",
                   "复现一次提示词注入并挡住它",
                   "算出 1000 次调用的成本"]),
    ("7 上线", ["FastAPI 接口可用且支持流式",
              "Docker 镜像能跑起来",
              "公网 URL 别人能访问",
              "README + 3 分钟演示视频"]),
]


def build_checklist(wb):
    ws = wb.create_sheet("打卡清单")
    headers = ["阶段", "检查项", "完成", "日期"]
    widths = [14, 66, 7, 14]
    total = sum(len(v) for _, v in CHECKLIST)
    style_title(
        ws, "打卡清单",
        f"共 {total} 项 ｜ 全部打勾 = 具备独立交付 Agent 项目的能力 ｜ 完成列可下拉选择 ✔",
        len(headers)
    )
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    style_header(ws, 3, headers)

    r = 4
    for stage, items in CHECKLIST:
        start = r
        fill = PatternFill("solid", fgColor=STAGE_FILL[stage.replace(" ★", "")])
        for item in items:
            ws.cell(row=r, column=1, value=stage)
            c = ws.cell(row=r, column=2, value=item)
            c.font = Font(name=FONT, size=10, color="1A1A1A")
            c.alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
            chk = ws.cell(row=r, column=3, value="□")
            chk.alignment = Alignment(horizontal="center", vertical="center")
            chk.font = Font(name=FONT, size=12)
            d = ws.cell(row=r, column=4, value="")
            d.alignment = Alignment(horizontal="center", vertical="center")
            d.number_format = "yyyy-mm-dd"
            for i in range(1, 5):
                ws.cell(row=r, column=i).fill = fill
                ws.cell(row=r, column=i).border = BORDER
            ws.row_dimensions[r].height = 24
            r += 1
        ws.merge_cells(f"A{start}:A{r - 1}")
        c = ws[f"A{start}"]
        c.font = Font(name=FONT, size=10, bold=True, color=NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    dv = DataValidation(type="list", formula1='"□,✔"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"C4:C{r - 1}")

    ws.freeze_panes = "A4"
    ws.sheet_view.showGridLines = False
    page_setup(ws, f"A1:D{r - 1}", rows="3:3")
    return ws


# ---------------------------------------------------------------- 表4 项目阶梯
PROJECTS = [
    ("1", "命令行聊天机器人", "第 6 周", "★☆☆",
     "API 调用、消息历史、流式输出、成本统计",
     "支持多轮对话；/cost 能显示累计花费"),
    ("2", "多工具个人助理", "第 8 周", "★★☆",
     "手写 Agent 循环、工具设计、错误自愈、上下文压缩",
     "能完成 3 步以上工具调用；工具报错后能自己改正"),
    ("3", "本地知识库问答", "第 10 周", "★★☆",
     "RAG 全链路、向量库、检索评估、来源引用",
     "回答带来源；有 20 条 eval 和召回率数据"),
    ("4", "领域助手（简历筛选 / 客服 FAQ / 读书笔记）", "第 15 周", "★★★",
     "框架、人工审批、trace、eval、安全防护",
     "有 eval 表、有审批节点、有看板、能挡住注入攻击"),
    ("5", "可上线 Web Agent", "第 16 周", "★★★",
     "FastAPI、Docker、鉴权限流、前端",
     "公网可访问，别人打开链接就能用"),
]


def build_projects(wb):
    ws = wb.create_sheet("项目阶梯")
    headers = ["#", "项目", "完成周", "难度", "核心技能", "验收标准", "状态"]
    widths = [5, 34, 10, 8, 40, 40, 12]
    style_title(
        ws, "项目阶梯（作品集路线）",
        "五个项目做完，GitHub 就是你的简历 ｜ 选择项目的唯一标准：你自己真的会用", len(headers)
    )
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    style_header(ws, 3, headers)

    r = 4
    band = ["FFFFFF", "F7F9FC"]
    for idx, row in enumerate(PROJECTS):
        fill = PatternFill("solid", fgColor=band[idx % 2])
        for i, v in enumerate(row + ("□ 未开始",), start=1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = Font(name=FONT, size=10, color="1A1A1A")
            c.fill = fill
            c.border = BORDER
            c.alignment = Alignment(
                horizontal="center" if i in (1, 3, 4, 7) else "left",
                vertical="center", wrap_text=True)
        ws.cell(row=r, column=2).font = Font(name=FONT, size=10, bold=True, color=NAVY)
        ws.row_dimensions[r].height = fit_row_height(row + ("",), widths)
        r += 1

    dv = DataValidation(type="list", formula1='"□ 未开始,◐ 进行中,✔ 已完成"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"G4:G{r - 1}")

    ws.freeze_panes = "A4"
    ws.sheet_view.showGridLines = False
    page_setup(ws, f"A1:G{r - 1}", rows="3:3")
    return ws


# ---------------------------------------------------------------- 表5 使用说明
def build_guide(wb):
    ws = wb.create_sheet("使用说明")
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 96

    style_title(
        ws, "怎么用这张表",
        "配合《Agent开发学习路线.md》使用：路线讲原理与取舍，这张表管执行", 2
    )

    blocks = [
        ("h", "一、每周的用法"),
        ("p", "1. 周日晚上：看一眼下周那一行，把「动手任务」抄到日历上。"),
        ("p", "2. 每天做完：在「踩坑与复盘」里加一句，写不出就说明没真学。"),
        ("p", "3. 周日结束：只有「过关标准」这一列全部满足，才在「完成」里选 ✔ 并填日期。"),
        ("p", "4. 没过关就老实待着补一周 —— 带着漏洞往前走，后面会一起崩。"),
        ("h", "二、三种时间投入怎么换算"),
        ("p", "每周 5 小时 → 约 32 周（适合在职，每天 45 分钟）"),
        ("p", "每周 10 小时 → 16 周（本表默认，工作日 1.5 小时 + 周末 4 小时）"),
        ("p", "每周 20 小时 → 8~9 周（全职冲刺）"),
        ("p", "无论哪种节奏：阶段 3（手写 Agent）和阶段 6（评估）不建议压缩，它们决定你是「会调 API」还是「会做产品」。"),
        ("h", "三、红字标记的是关键周"),
        ("p", "第 7–8 周（手写 Agent 循环）：决定你之后能不能看懂任何框架。"),
        ("p", "第 15 周（可观测与安全）：决定你的东西能不能给别人用。"),
        ("h", "四、卡住了怎么办"),
        ("p", "1. 先读官方文档的 Quickstart，手敲一遍，不要抄视频。"),
        ("p", "2. 把报错原样搜索，中文搜不到就用英文搜。"),
        ("p", "3. 连续卡 2 小时以上：跳过，先让流程跑通，回头再补 —— 但要记进复盘，别忘。"),
        ("p", "4. 永远不要在没有跑通的情况下继续学下一个概念。"),
        ("h", "五、打印建议"),
        ("p", "四张表都已设置 A4 横向、按 1 页宽缩放。直接 Ctrl+P 即可，无需调整。"),
        ("p", "建议只打印「周计划表」贴在桌前，其余三张在电脑上勾选。"),
    ]

    r = 4
    for kind, text in blocks:
        ws.merge_cells(f"A{r}:B{r}")
        c = ws[f"A{r}"]
        c.value = text
        if kind == "h":
            c.font = Font(name=FONT, size=11, bold=True, color=NAVY)
            c.fill = PatternFill("solid", fgColor="E8EEF7")
            c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            ws.row_dimensions[r].height = 26
        else:
            c.font = Font(name=FONT, size=10, color="1A1A1A")
            c.alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
            ws.row_dimensions[r].height = max(22, fit_row_height([text], [94]))
        r += 1

    ws.sheet_view.showGridLines = False
    page_setup(ws, f"A1:B{r - 1}", orientation="portrait")
    return ws


def main():
    wb = Workbook()
    wb.remove(wb.active)

    build_plan(wb)
    build_daily(wb)
    build_checklist(wb)
    build_projects(wb)
    build_guide(wb)

    wb.active = 0
    wb.properties.title = "Agent 开发 16 周周计划表"
    wb.properties.creator = "Agent 学习路线"
    wb.properties.created = datetime.now()

    wb.save(OUT)
    print("saved:", OUT)


if __name__ == "__main__":
    main()

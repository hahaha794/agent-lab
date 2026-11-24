# -*- coding: utf-8 -*-
"""Build an optimized one-page math-tutor resume (DOCX)."""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

NAVY = RGBColor(0x1F, 0x4E, 0x79)
ACCENT = RGBColor(0x2E, 0x75, 0xB6)
DARK = RGBColor(0x33, 0x33, 0x33)
GRAY = RGBColor(0x59, 0x59, 0x59)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "微软雅黑"

# ---- layout knobs ----
SIDE = 1.7
CONTENT_W = Cm(21.0 - SIDE * 2)
BODY = 10.0
LINE = 1.12
BAR_BEFORE, BAR_AFTER = 8, 3


def set_run_font(run, size=BODY, bold=False, color=DARK, italic=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), FONT)


def shade(paragraph, hex_fill):
    ppr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    ppr.append(shd)


def bottom_rule(paragraph, color="BFBFBF", size=6):
    ppr = paragraph._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), color)
    pbdr.append(bottom)
    ppr.append(pbdr)


def section_bar(doc, title, space_before=BAR_BEFORE, space_after=BAR_AFTER):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = 1.3
    pf.left_indent = Cm(0.16)
    shade(p, "1F4E79")
    r = p.add_run("　")
    set_run_font(r, 10.5, True, WHITE)
    r = p.add_run(title)
    set_run_font(r, 10.5, True, WHITE)
    return p


def body_paragraph(doc, space_before=0, space_after=1, line=LINE, left=0.0, hanging=0.0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = line
    pf.left_indent = Cm(left)
    if hanging:
        pf.first_line_indent = Cm(-hanging)
    return p


def entry_line(doc, org, detail, date, space_before=2):
    """Bold organisation + optional detail + right-aligned date via tab stop."""
    p = body_paragraph(doc, space_before=space_before, space_after=0)
    p.paragraph_format.tab_stops.add_tab_stop(CONTENT_W, WD_TAB_ALIGNMENT.RIGHT)
    r = p.add_run(org)
    set_run_font(r, BODY, True, NAVY)
    if detail:
        r = p.add_run("　" + detail)
        set_run_font(r, BODY, False, GRAY)
    r = p.add_run("\t" + date)
    set_run_font(r, 9.0, False, GRAY)
    return p


def bullet(doc, label, text, space_before=1):
    p = body_paragraph(doc, space_before=space_before, space_after=0, left=0.55, hanging=0.55)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(0.55))
    r = p.add_run("•")
    set_run_font(r, 10.5, True, ACCENT)
    p.add_run("\t")
    if label:
        r = p.add_run(label)
        set_run_font(r, BODY, True, DARK)
    r = p.add_run(text)
    set_run_font(r, BODY, False, DARK)
    return p


def plain(doc, text, size=BODY, color=GRAY, space_before=0, space_after=0, left=0.55):
    p = body_paragraph(doc, space_before=space_before, space_after=space_after, left=left)
    r = p.add_run(text)
    set_run_font(r, size, False, color)
    return p


doc = Document()

# ---- page setup ----
sec = doc.sections[0]
sec.page_width = Cm(21.0)
sec.page_height = Cm(29.7)
sec.top_margin = Cm(1.3)
sec.bottom_margin = Cm(1.1)
sec.left_margin = Cm(SIDE)
sec.right_margin = Cm(SIDE)
sec.header_distance = Cm(0.7)
sec.footer_distance = Cm(0.7)

normal = doc.styles["Normal"]
normal.font.name = FONT
normal.font.size = Pt(BODY)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
normal.paragraph_format.space_before = Pt(0)
normal.paragraph_format.space_after = Pt(0)

# ---- header ----
p = body_paragraph(doc, space_before=0, space_after=0, line=1.0)
r = p.add_run("潘心浩")
set_run_font(r, 21, True, NAVY)
r = p.add_run("　数学家教")
set_run_font(r, 12, False, GRAY)

p = body_paragraph(doc, space_before=1, space_after=2, line=1.0)
r = p.add_run("初中 / 高中数学 · 一对一 · 擅长把“不会”讲成“会”")
set_run_font(r, 9.5, False, ACCENT)

p = body_paragraph(doc, space_before=0, space_after=0, line=1.1)
r = p.add_run("15138779551　|　1546983291@qq.com　|　陕西 · 西安长安区")
set_run_font(r, 9.0, False, GRAY)
bottom_rule(p, "1F4E79", 8)

# ---- 基本信息 ----
section_bar(doc, "基本信息", space_before=5)

p = body_paragraph(doc, space_before=2, space_after=1)
for label, value in (("可教科目：", "初中数学、高中数学"), ("可教形式：", "线下一对一（可上门）")):
    r = p.add_run(label)
    set_run_font(r, BODY, True, DARK)
    r = p.add_run(value + "　　")
    set_run_font(r, BODY, False, DARK)

p = body_paragraph(doc, space_before=0, space_after=0)
for label, value in (("授课时间：", "周末全天，周内晚间可协商"), ("数学成绩：", "高考 134 / 150　考研 136 / 150")):
    r = p.add_run(label)
    set_run_font(r, BODY, True, DARK)
    r = p.add_run(value + "　　")
    set_run_font(r, BODY, False, DARK)

# ---- 教育背景 ----
section_bar(doc, "教育背景")

entry_line(doc, "西安电子科技大学", "网络空间安全（硕士研究生）", "2026.09 – 至今", space_before=3)
entry_line(doc, "西安工业大学", "信息对抗技术（本科）", "2021.09 – 2025.06", space_before=2)
bullet(doc, "学业成绩：", "GPA 3.3 / 5.0（专业前 3%），一等学业奖学金、国家励志奖学金。")

# ---- 数学功底 ----
section_bar(doc, "数学功底（成绩佐证）")

bullet(
    doc,
    "高考数学 134 / 150 · 考研数学 136 / 150：",
    "函数、导数、解析几何、立体几何为稳定得分模块，基础题几乎不失分；考研系统复习高数、线代、概率，能把复杂题型拆成可复用的步骤。",
)
bullet(
    doc,
    "科班功底：",
    "高数 AⅠ/AⅡ 均 91 分、线性代数 92 分，专业前 3%，知识体系连续无断层，讲得清“为什么这么做”而不只是“套公式”。",
)

# ---- 家教经历 ----
section_bar(doc, "家教经历")

entry_line(doc, "初二学生 · 数学一对一", "上门辅导 · 每周 2 次，每次 2 小时", "2023.09 – 2024.06", space_before=3)
bullet(
    doc,
    "学情诊断：",
    "接手时基础题失分多、几何辅助线没思路，遇到综合题直接放弃，单元测试常年卡在及格线，对数学畏难。",
)
bullet(
    doc,
    "因材施教：",
    "先用错题归因把“不会”拆成概念不清、计算失误、审题偏差三类，再按薄弱点单独编讲义——概念不清就回定义与例题，计算失误就限时练基础题，审题偏差就带他画图圈关键词；基础小步走、即时反馈，中档题做题型归纳，压轴题只练“能拿分的步骤”。",
)
bullet(
    doc,
    "提分效果：",
    "一学期后期末成绩较辅导前明显提升，基础题正确率大幅提高，压轴题从空白到稳定拿到步骤分，畏难情绪明显减轻，开始主动整理错题。",
)
bullet(
    doc,
    "沟通与反馈：",
    "每节课后与家长同步 5 分钟（学了什么、卡在哪、回家练什么），每月一份学习反馈（进步点 + 下阶段计划）；讲题先接住情绪再拆问题，让他敢说“这里我没听懂”。",
)

# ---- 教学理念与方法 ----
section_bar(doc, "教学理念与方法")

bullet(
    doc,
    "因材施教：",
    "先测评再定方案——基础弱的补概念、练计算，用“小步走 + 即时反馈”重建信心；中等生做题型归纳、一题多解；拔高生攻压轴拆解与限时训练，同一节课不同学生拿到的讲义不一样。",
)
bullet(
    doc,
    "善于沟通：",
    "把抽象概念翻译成生活例子（用“爬坡”讲斜率、用“切蛋糕”讲分类讨论），先共情再讲题；用提问代替灌输，让学生把思路“讲回来”，讲得清才算真会。",
)
bullet(
    doc,
    "提分路径：",
    "诊断错题 → 定位薄弱模块 → 专项突破 → 限时套卷固化；配合错题本、每周小测与课后答疑，把“听懂”练成“做对、做快”，每次课设 1–2 个可检验的小目标。",
)

# ---- 备注 ----
plain(
    doc,
    "备注：可提供 30 分钟免费试讲与学情诊断；课后微信答疑不限时；按学校进度调整讲义，期中期末前安排专项冲刺。",
    size=9.0,
    color=GRAY,
    space_before=5,
    left=0.0,
)

out = r"C:\Users\admin\Desktop\study\个人简历_优化版.docx"
doc.save(out)
print("saved:", out)

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatOpenAI(
    api_key=os.environ['DEEPSEEK_API_KEY'],
    base_url=os.environ.get("DEEPSEEK_API_BASE_URL"),
)

# ─── 定义三个步骤 ────────────────────────────────────────────
# 步骤 1：将文章翻译成中文
translate_prompt = ChatPromptTemplate.from_template(
    "将下面的英文文章翻译成中文，保持原意：\n\n{article}"
)

# 步骤 2：提取摘要
summarize_prompt = ChatPromptTemplate.from_template(
    "请将以下文章提炼成 3 个要点，每点一句话：\n\n{translated}"
)

# 步骤 3：生成标题
title_prompt = ChatPromptTemplate.from_template(
    "根据以下摘要，生成一个吸引人的中文标题（15字以内）：\n\n{summary}"
)

parser = StrOutputParser()

# ─── 用 | 操作符链接成流水线 ─────────────────────────────────
chain = (
    {"translated": translate_prompt | llm | parser}
    | {"summary": summarize_prompt | llm | parser,
       "translated": lambda x: x["translated"]}
    | title_prompt | llm | parser
)

# ─── 运行 ────────────────────────────────────────────────────
article = """
Artificial intelligence is transforming how we work and live.
From automating repetitive tasks to assisting in creative work,
AI tools are becoming indispensable in modern workflows...
"""

result = chain.invoke({"article": article})
print(result)
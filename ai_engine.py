from openai import OpenAI
import json
import datetime
import os
import sys
import re

# === 核心修复：统一配置路径逻辑 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if getattr(sys, 'frozen', False):
    # 打包后，读取用户目录下的隐藏文件 (与 main.py 保持一致)
    CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".lazymemo_config.json")
else:
    # 开发模式下，读取项目目录下的文件
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


def load_config():
    if not os.path.exists(CONFIG_PATH): return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def parse_user_input(user_text):
    config = load_config()

    # 调试信息：打印当前读取的配置文件路径 (方便你在终端看)
    print(f"DEBUG: AI Engine reading config from: {CONFIG_PATH}")

    # 1. 基础检查
    if not config or not config.get("api_key"):
        print("DEBUG: API Key is missing in config!")
        return {"error": "missing_key"}

    # === 🛡️ 核心修复：给 Key 洗个澡 ===
    raw_key = config["api_key"]
    # 逻辑：只保留 ASCII 范围内的可见字符 (编码 33-126)
    clean_key = "".join(c for c in raw_key if 33 <= ord(c) <= 126)

    if not clean_key:
        return {"error": "missing_key"}

    # 2. 初始化客户端
    try:
        client = OpenAI(
            api_key=clean_key,
            base_url="https://api.minimax.chat/v1"
        )

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 3. 构建 Prompt
        system_prompt = f"""
        你是一个智能助手。当前时间: {current_time}。
        请分析用户输入并输出 JSON。

        任务类型 (type):
        1. "reminder": 新建待办 (如 "明天开会", "买牛奶")
        2. "note": 纯想法/日记 (如 "今天心情不错", "记录一下灵感")
        3. "update": 修改/补充/查找已有任务

        输出字段:
        - type: "reminder" | "note" | "update"
        - search_term: (仅 update 必填) 
        - title: 新标题 (reminder必填)
        - notes: 任务详情
        - content: 笔记内容 (note 必填)
        - due_date: YYYY-MM-DD HH:MM:SS
        - priority: 0,1,5,9

        严禁 Markdown，只输出纯 JSON 字符串。
        """

        # 4. 调用 API
        response = client.chat.completions.create(
            model=config.get("model", "abab6.5s-chat"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.1,
        )
        content = response.choices[0].message.content

        # 5. 清洗返回结果
        cleaned_text = content.replace("```json", "").replace("```", "").strip()
        json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
        if json_match:
            cleaned_text = json_match.group(0)

        return json.loads(cleaned_text)

    except Exception as e:
        print(f"API Error: {e}")
        return None
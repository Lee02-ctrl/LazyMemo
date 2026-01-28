from openai import OpenAI
import json
import datetime
import os
import re  # 引入正则来清洗数据

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
    # 1. 基础检查
    if not config or not config.get("api_key"):
        return {"error": "missing_key"}

    # === 🛡️ 核心修复：给 Key 洗个澡 ===
    raw_key = config["api_key"]
    # 逻辑：只保留 ASCII 范围内的可见字符 (编码 33-126)，把空格、BOM、全角符号全扔掉
    clean_key = "".join(c for c in raw_key if 33 <= ord(c) <= 126)

    # 双重保险：如果清洗后是空的，报错
    if not clean_key:
        return {"error": "missing_key"}

    # 2. 初始化客户端
    client = OpenAI(
        api_key=clean_key,  # 使用洗干净的 Key
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
    3. "update": 修改/补充/查找已有任务 (如 "吃饭那事改到7点", "作业要交PDF版", "把那个任务推迟")

    输出字段:
    - type: "reminder" | "note" | "update"
    - search_term: (仅 update 必填) 用来在列表中查找任务的关键词 (如 "吃饭", "作业")
    - title: 新标题 (reminder必填，update选填)
    - notes: 任务详情 (reminder/update 选填，update时表示追加或修改详情)
    - content: 笔记内容 (note 必填)
    - due_date: YYYY-MM-DD HH:MM:SS (reminder/update 选填)
    - priority: 0,1,5,9 (reminder/update 选填)

    严禁 Markdown，只输出纯 JSON 字符串。
    """

    try:
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

        # 5. 清洗返回结果 (防止 AI 加 ```json)
        cleaned_text = content.replace("```json", "").replace("```", "").strip()
        # 尝试提取第一个 { ... } 区块，防止 AI 废话
        json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
        if json_match:
            cleaned_text = json_match.group(0)

        return json.loads(cleaned_text)

    except Exception as e:
        print(f"API Error: {e}")
        # 如果是认证错误，给个明确提示
        if "401" in str(e) or "403" in str(e):
            print("⚠️ 可能是 API Key 无效或余额不足")
        return None
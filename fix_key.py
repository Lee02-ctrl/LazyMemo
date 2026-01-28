import json
import os

# 1. 读取配置文件
if not os.path.exists("config.json"):
    print("❌ 找不到 config.json，请先运行主程序生成配置。")
    exit()

with open("config.json", "r", encoding="utf-8") as f:
    data = json.load(f)

raw_key = data.get("api_key", "")

print(f"🔍 原始 Key (长度 {len(raw_key)}): {repr(raw_key)}")

# 2. 强力清洗：只保留字母、数字、下划线、横杠
# 这是 API Key 唯四可能出现的字符类型，其他统统杀掉
clean_key = "".join(c for c in raw_key if c.isalnum() or c in "-_")

print(f"✅ 清洗后 (长度 {len(clean_key)}): {repr(clean_key)}")

# 3. 检查是否有变化
if raw_key != clean_key:
    print("⚠️ 发现非法字符！正在修复 config.json ...")
    data["api_key"] = clean_key
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print("🎉 修复完成！现在请重新运行 main.py 试试。")
else:
    print("✅ Key 看起来很干净，没发现问题。")
    print("👉 如果依然报错，请确认您是否开启了全局代理或 VPN，有时是网络层面的编码问题。")
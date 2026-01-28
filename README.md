# ⚡️ LazyMemo (懒人备忘)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey?style=flat-square&logo=apple)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-success?style=flat-square)

> **优雅、极简、即刻响应。**
> 专为 macOS 打造的智能个人助理，让记录待办像呼吸一样自然。

**LazyMemo** 是一款潜伏在菜单栏的极简生产力工具。通过全局快捷键唤醒，它能利用 AI 语义分析（或极速离线规则）将你的自然语言指令瞬间转化为 macOS 原生的 **提醒事项 (Reminders)** 或 **备忘录 (Notes)**。无需打开笨重的 App，灵感与任务，一键直达。

---

## ✨ 核心特性 (Features)

### 🧠 双核大脑引擎
- **🤖 AI 联网模式**：接入 **MiniMax** (兼容 OpenAI 协议) 大模型。
  - 懂你所想：输入 *"下周三下午两点提醒我带合同去见客户"*，自动提取时间、地点、事件。
  - 智能分类：自动识别你是想创建待办，还是仅仅想记录一条笔记。
- **⚡️ 离线极速模式**：断网也能用，隐私零泄露。
  - **关键词捕获**：自动识别 *"明天"*、*"后天"*、*"晚上"* 等时间词。
  - **强制笔记**：支持 `Memo: ` 或 `备忘录 ` 前缀，强制将内容存入备忘录。

### 🍎 原生生态深度融合
- **零迁移成本**：直接读写 macOS 系统底层的 **提醒事项** 和 **备忘录** 数据库。
- **iCloud 同步**：在 Mac 上记录，iPhone、iPad、Watch 瞬间同步。

### ⏰ 语义时间自定义
- **你的时间你做主**：系统不懂你的作息？在 LazyMemo 里，你可以定义 *"早上"* 是 09:00 还是 11:00，*"夜里"* 是 22:00 还是 02:00。让 AI 适应你的生物钟。

### 📰 贴心的早晚报
- **每日简报**：每天早晚定时（可配置）推送今日待办概览。哪怕无事发生，也会贴心地报个平安。

### 🎨 极简主义 UI
- **沉浸式设计**：无边框黑色半透明悬浮窗，搭配 macOS 原生质感的设置面板。呼之即来，挥之即去。

---

## 🚀 快速开始 (Getting Started)

### 1. 环境要求
- **操作系统**: macOS 11.0 (Big Sur) 及以上 (依赖 AppleScript)
- **Python**: 3.10+

### 2. 安装
克隆项目到本地：
```bash
git clone [https://github.com/Lee02-Ctrl/LazyMemo.git](https://github.com/Lee02-Ctrl/LazyMemo.git)
cd LazyMemo
```
推荐使用虚拟环境安装依赖：

# 创建并激活虚拟环境  
```
python3 \-m venv .venv  
source .venv/bin/activate

\# 安装依赖  
pip install PyQt6 pynput schedule openai
```
### **3\. 运行**
```
python main.py
```
启动成功后，菜单栏会出现 LazyMemo 的图标，程序进入后台静默运行。

## **⚙️ 配置指南 (Configuration)**

LazyMemo 支持通过 GUI 设置面板修改配置，配置会自动保存到 config.json。

### **🔑 API 设置**

本项目底层使用 OpenAI SDK，理论上支持所有兼容 OpenAI 接口的大模型。

默认针对 **MiniMax (abab6.5s-chat)** 进行了优化，拥有极高的性价比和中文理解能力。你需要去 [MiniMax 开放平台](https://platform.minimaxi.com/) 申请一个 API Key。

### **📄 配置文件示例 (config.json)**

首次运行后会自动生成此文件。你也可以手动创建：

{  
    "api\_key": "sk-your-api-key-here",  
    "model": "abab6.5s-chat",  
    "use\_ai": true,  
    "morning\_time": "09:00",  
    "evening\_time": "21:00",  
    "time\_mapping": {  
        "早上": "09:00",  
        "上午": "09:00",  
        "中午": "12:00",  
        "下午": "15:00",  
        "晚上": "18:00",  
        "傍晚": "18:00",  
        "夜里": "22:00",  
        "凌晨": "00:00"  
    }  
}

**⚠️ 安全提示**：config.json 包含敏感 Key，**请勿上传到 GitHub**。项目自带的 .gitignore 已默认忽略该文件。

## **⌨️ 使用手册 (Usage)**

### **唤醒**

按下全局快捷键 **Option \+ Space** (Alt \+ Space) 呼出输入框。

### **场景演示**

#### **1\. 📅 AI 智能模式 (推荐)**

无需任何指令格式，像和朋友聊天一样输入：

| 输入内容 | 行为结果 |
| :---- | :---- |
| 明天下午三点去见客户 | ✅ 创建提醒事项：**明天 15:00**，标题 "见客户" |
| 今晚记得买牛奶 | ✅ 创建提醒事项：**今天 18:00** (根据你的定义)，标题 "买牛奶" |
| 记录一下：这部电影特效很棒 | 📝 存入 **备忘录**，内容 "这部电影特效很棒" |

#### **2\. ⚡️ 离线模式**

在设置中关闭 AI 开关，或网络不可用时：

* **创建提醒**：  
  输入：明天下午去打球  
  👉 系统自动捕捉关键词 *"明天"* (日期+1) 和 *"下午"* (时间=15:00)。  
* **强制笔记**：  
  输入：备忘录 今天发现了家好吃的店 (或 Memo ...)  
  👉 **注意**：前缀后必须有一个**空格**。内容将直接追加到 macOS 备忘录中。

## **📂 项目结构**

LazyMemo/  
├── main.py              \# 程序主入口，UI 线程与逻辑调度  
├── mac\_reminders.py     \# macOS 底层交互 (AppleScript 封装库)  
├── ai\_engine.py         \# AI 智能处理核心 (MiniMax API)  
├── config.json          \# 用户配置文件 (自动生成，勿传)  
├── .gitignore           \# Git 忽略规则  
└── README.md            \# 说明文档

## **🤝 贡献 (Contributing)**

欢迎提交 Issue 反馈 Bug，或者提交 Pull Request 贡献代码！

1. Fork 本仓库  
2. 新建 Feat\_xxx 分支  
3. 提交代码  
4. 新建 Pull Request

## **📜 版权说明 (License)**

本项目基于 [MIT License](https://www.google.com/search?q=LICENSE) 开源。

Copyright (c) 2026 **Li Yazhe**
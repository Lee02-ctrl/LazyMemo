import subprocess
import datetime
import json
import shutil # 用来检查是否安装了 terminal-notifier


# === 辅助函数：构建日期脚本 ===
def _build_date_script(due_date_str):
    """生成 AppleScript 日期对象"""
    try:
        dt = datetime.datetime.strptime(due_date_str, "%Y-%m-%d %H:%M:%S")
        seconds = dt.hour * 3600 + dt.minute * 60
        return f'''
            set d to current date
            set year of d to {dt.year}
            set month of d to {dt.month}
            set day of d to {dt.day}
            set time of d to {seconds}
            set seconds of d to 0
            set due date to d
        '''
    except:
        return ""


def _run_applescript(script, action_name):
    try:
        res = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"✅ {action_name} 成功")
            return True
        else:
            print(f"❌ {action_name} 失败: {res.stderr}")
            return False
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        return False


# === 1. 新建提醒 ===
def create_reminder(task_data):
    title = task_data.get('title', '新任务')
    notes = task_data.get('notes', '')
    due_date_str = task_data.get('due_date')
    priority = task_data.get('priority', 0)

    apple_priority = 0
    if priority >= 9:
        apple_priority = 1
    elif priority >= 5:
        apple_priority = 5
    elif priority >= 1:
        apple_priority = 9

    date_script = ""
    if due_date_str and due_date_str != "null":
        date_script = _build_date_script(due_date_str)

    script = f'''
    tell application "Reminders"
        if (count of lists) is 0 then error "No list"
        set myList to list 1
        set newRem to make new reminder at end of myList with properties {{name:"{title}", body:"{notes}", priority:{apple_priority}}}
        tell newRem
            {date_script}
        end tell
    end tell
    '''
    return _run_applescript(script, "新建任务")


# === 2. 搜索提醒 ===
def search_reminders(keyword):
    print(f"🔍 正在全局搜索: {keyword}")
    script = f'''
    tell application "Reminders"
        set outputJson to "["
        set isFirst to true

        repeat with aList in lists
            set matchedReminders to (every reminder of aList where completed is false and name contains "{keyword}")
            repeat with rem in matchedReminders
                set remId to id of rem
                set remName to name of rem
                set remBody to body of rem
                if remBody is missing value then set remBody to ""

                if isFirst is false then set outputJson to outputJson & ","
                set isFirst to false

                set outputJson to outputJson & "{{\\"id\\":\\"" & remId & "\\", \\"title\\": \\"" & remName & "\\", \\"notes\\": \\"" & remBody & "\\"}}"
            end repeat
        end repeat

        set outputJson to outputJson & "]"
        return outputJson
    end tell
    '''
    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if result.returncode != 0: return []

        output = result.stdout.strip()
        if not output or output == "[]": return []

        clean_json = output.replace('\n', '\\n').replace('\r', '')
        return json.loads(clean_json)
    except Exception as e:
        print(f"搜索解析出错: {e}")
        return []


# === 3. 更新提醒 (核心修复部分) ===
def update_reminder_by_id(rem_id, update_data):
    notes = update_data.get('notes')
    due_date_str = update_data.get('due_date')
    title = update_data.get('title')

    script_parts = []

    if title:
        script_parts.append(f'set name to "{title}"')

    if notes:
        # === 修复重点 ===
        # AppleScript 逻辑：先检查 currentBody 是否为 missing value
        # 如果是，直接赋值；如果不是，再追加。
        script_parts.append(f'''
            set currentBody to body
            if currentBody is missing value then
                set body to "{notes}"
            else
                set body to currentBody & return & "{notes}"
            end if
        ''')

    if due_date_str and due_date_str != "null":
        date_code = _build_date_script(due_date_str)
        if date_code: script_parts.append(date_code)

    if not script_parts: return True

    full_script = "\n".join(script_parts)
    script = f'''
    tell application "Reminders"
        set rem to reminder id "{rem_id}"
        tell rem
            {full_script}
        end tell
    end tell
    '''
    return _run_applescript(script, "更新任务")


# === 4. 备忘录逻辑 ===
def append_to_note(note_data):
    content = note_data.get('content', '')
    if not content: return False
    date_header = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    html_entry = f"<div><b>{date_header}</b><br>{content}</div><br>"

    script = f'''
    tell application "Notes"
        tell default account
            if not (exists note "LazyMemo") then make new note with properties {{name:"LazyMemo", body:""}}
            set theNote to note "LazyMemo"
            set body of theNote to (body of theNote) & "{html_entry}"
        end tell
    end tell
    '''
    return _run_applescript(script, "备忘录")


# ... (上面的代码保持不变)

# ... (前面的代码保持不变)

# === 5. 获取任务 (稳健版：使用分隔符，防止 JSON 报错) ===
def get_todays_tasks():
    # 1. AppleScript 只负责吐出原始数据，用 "|||" 分隔
    script = '''
    tell application "Reminders"
        set output to ""

        repeat with aList in lists
            set pendingReminders to (every reminder of aList where completed is false)
            repeat with rem in pendingReminders
                set d to due date of rem

                if d is not missing value then
                    set remName to name of rem
                    set remList to name of aList

                    -- 简单的日期拼接 YYYY-MM-DD HH:MM:SS
                    set y to year of d
                    set m to (month of d as integer)
                    set day_val to day of d
                    set t to time of d
                    set hr to t div 3600
                    set min_val to (t mod 3600) div 60

                    set dateStr to (y as string) & "-" & (m as string) & "-" & (day_val as string) & " " & (hr as string) & ":" & (min_val as string) & ":00"

                    -- 关键点：用 ||| 作为分隔符，比拼 JSON 稳定得多
                    set output to output & remName & "|||" & dateStr & "|||" & remList & "\n"
                end if
            end repeat
        end repeat
        return output
    end tell
    '''

    try:
        # 2. 获取原始文本
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        raw_text = result.stdout.strip()

        if not raw_text:
            return "☕️ 今天和未来几天都无事，享受生活吧！"

        # 3. Python 解析文本
        now = datetime.datetime.now()
        today_end = now.replace(hour=23, minute=59, second=59)
        three_days_later = today_end + datetime.timedelta(days=3)

        list_today = []
        list_upcoming = []

        # 按行分割
        lines = raw_text.split('\n')

        for line in lines:
            if "|||" not in line: continue

            # 拆分数据：任务名 ||| 日期 ||| 列表名
            parts = line.split("|||")
            if len(parts) < 3: continue

            title = parts[0].strip()
            date_str = parts[1].strip()
            # list_name = parts[2].strip() # 暂时没用到列表名，备用

            try:
                task_date = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except:
                continue

            # 4. 分类逻辑
            if task_date <= today_end:
                list_today.append(f"• {title}")
            elif task_date <= three_days_later:
                weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                wk = weekday_map[task_date.weekday()]
                list_upcoming.append(f"• {title} ({wk})")

        # 5. 组装最终文案
        final_msg = ""

        if list_today:
            final_msg += "🔥 今天待办：\n" + "\n".join(list_today) + "\n\n"

        if list_upcoming:
            final_msg += "📅 未来 3 天：\n" + "\n".join(list_upcoming)

        if not final_msg:
            return "☕️ 接下来 3 天都没什么急事，心情不错！"

        return final_msg.strip()

    except Exception as e:
        print(f"❌ 数据处理出错: {e}")
        return "⚠️ 获取任务列表失败"


# === 6. 发送通知 (优雅版：使用 terminal-notifier) ===
def send_system_notification(title, message):
    print(f"📣 推送通知: {title}")

    # 检查是否安装了 terminal-notifier
    if shutil.which("terminal-notifier"):
        # 使用第三方工具发送（支持点击、图标、不被屏蔽）
        subprocess.run([
            'terminal-notifier',
            '-title', title,
            '-message', message,
            '-sound', 'default',
            '-appIcon', 'https://cdn-icons-png.flaticon.com/512/2693/2693507.png'  # 给它个图标（可选）
        ])
    else:
        # 【降级方案】如果没有安装 brew，回退到 Finder 发送
        safe_message = message.replace('"', '\\"')
        script = f'''
        tell application "Finder"
            display notification "{safe_message}" with title "{title}" subtitle "LazyMemo" sound name "Glass"
        end tell
        '''
        subprocess.run(['osascript', '-e', script])
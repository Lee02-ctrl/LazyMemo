import sys
import json
import os
import threading
import time
import schedule
import datetime

from PyQt6.QtWidgets import (QApplication, QWidget, QLineEdit, QVBoxLayout,
                             QLabel, QPushButton, QMessageBox, QInputDialog,
                             QCheckBox, QTimeEdit, QGroupBox, QFormLayout,
                             QGridLayout, QScrollArea, QSystemTrayIcon, QMenu,
                             QHBoxLayout, QAbstractSpinBox)  # 引入 QAbstractSpinBox 以便样式控制
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QTime

from pynput import keyboard

# 确保导入了发送通知的函数
from ai_engine import parse_user_input
from mac_reminders import (create_reminder, append_to_note, search_reminders,
                           update_reminder_by_id, get_todays_tasks, send_email_notification)

if getattr(sys, 'frozen', False):
    log_path = os.path.join(os.path.expanduser("~"), "lazymemo_debug.log")
    sys.stdout = open(log_path, "a", buffering=1, encoding='utf-8')
    sys.stderr = open(log_path, "a", buffering=1, encoding='utf-8')
    print(f"\n=== App Started at {datetime.datetime.now()} ===")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if getattr(sys, 'frozen', False):
    CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".lazymemo_config.json")
    BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
else:
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
    BUNDLE_DIR = BASE_DIR


def get_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


# --- 设置窗口 (UI 最终美化版) ---
class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("偏好设置")
        self.resize(480, 680)

        # 🎨 核心改动：QTimeEdit/QAbstractSpinBox 样式优化
        self.setStyleSheet("""
            QWidget {
                background-color: #2E2E2E; color: #E0E0E0;
                font-family: 'SF Pro Text', 'PingFang SC', sans-serif; font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #3E3E3E; border-radius: 10px;
                margin-top: 24px; padding-top: 14px; background-color: #363636;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 0 8px; left: 12px; color: #8E8E93; font-weight: bold; font-size: 12px;
            }
            /* 通用输入框样式 */
            QLineEdit, QTimeEdit, QAbstractSpinBox {
                background-color: #262626; 
                border: 1px solid #454545;
                border-radius: 6px; 
                padding: 6px 10px; 
                color: white; 
                font-size: 13px;
                selection-background-color: #0A84FF; 
            }
            /* 获得焦点时的蓝色高亮 (macOS 风格) */
            QLineEdit:focus, QTimeEdit:focus, QAbstractSpinBox:focus {
                border: 1px solid #0A84FF; 
                background-color: #1F1F1F;
            }
            /* 🔥 关键改动：隐藏 QTimeEdit 右侧那个尖尖的按钮 */
            QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
                width: 0px; 
                height: 0px;
                border: none;
                background: transparent;
            }
            QLabel { color: #CCCCCC; }
            QLabel#HelpText { color: #888888; font-size: 11px; margin-top: 2px; margin-left: 2px;} 
            QPushButton {
                background-color: #007AFF; border-radius: 6px; color: white; 
                font-weight: 500; padding: 8px 16px; font-size: 13px;
            }
            QPushButton:hover { background-color: #0071EB; }
            QPushButton:pressed { background-color: #005BB5; }
        """)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        title_label = QLabel("偏好设置")
        title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: white; margin-bottom: 5px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # === 1. 智能引擎 ===
        mode_group = QGroupBox("智能引擎")
        mode_layout = QVBoxLayout()
        mode_layout.setContentsMargins(16, 24, 16, 16)
        mode_layout.setSpacing(10)

        self.ai_check = QCheckBox("启用 AI 语义分析")
        self.ai_check.setChecked(True)
        self.ai_check.toggled.connect(self.toggle_ai_input)

        hint = QLabel("关闭后将进入「离线模式」，仅通过关键词匹配时间和意图。")
        hint.setObjectName("HelpText")

        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("在此粘贴 MiniMax API Key")
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)

        mode_layout.addWidget(self.ai_check)
        mode_layout.addWidget(hint)
        mode_layout.addWidget(self.api_input)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # === 2. 邮件通知 ===
        email_group = QGroupBox("邮件推送")
        email_main_layout = QVBoxLayout()
        email_main_layout.setContentsMargins(16, 24, 16, 16)
        email_main_layout.setSpacing(12)

        # 第一行：服务器 和 端口
        server_layout = QHBoxLayout()
        server_layout.setSpacing(10)

        self.smtp_server = QLineEdit("smtp.163.com")
        self.smtp_server.setPlaceholderText("SMTP 服务器")

        self.smtp_port = QLineEdit("465")
        self.smtp_port.setPlaceholderText("端口")
        self.smtp_port.setFixedWidth(80)

        server_layout.addWidget(QLabel("服务器:"))
        server_layout.addWidget(self.smtp_server)
        server_layout.addWidget(QLabel("端口:"))
        server_layout.addWidget(self.smtp_port)

        email_main_layout.addLayout(server_layout)

        # 第二行：账号信息
        self.sender_email = QLineEdit()
        self.sender_email.setPlaceholderText("你的邮箱 (例如: user@163.com)")

        email_main_layout.addWidget(QLabel("发件邮箱:"))
        email_main_layout.addWidget(self.sender_email)

        # 第三行：授权码
        self.email_pwd = QLineEdit()
        self.email_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.email_pwd.setPlaceholderText("在此输入 163 邮箱授权码")

        pwd_help = QLabel("⚠️ 注意：必须填写邮箱设置中生成的「授权码」，而非登录密码。")
        pwd_help.setObjectName("HelpText")

        email_main_layout.addWidget(QLabel("授权码:"))
        email_main_layout.addWidget(self.email_pwd)
        email_main_layout.addWidget(pwd_help)

        # 第四行：收件人
        self.receiver_email = QLineEdit()
        self.receiver_email.setPlaceholderText("选填，留空则默认发给自己")

        email_main_layout.addWidget(QLabel("收件人 (可选):"))
        email_main_layout.addWidget(self.receiver_email)

        email_group.setLayout(email_main_layout)
        layout.addWidget(email_group)

        # === 3. 日报时刻 ===
        report_group = QGroupBox("日报时刻")
        report_layout = QGridLayout()
        report_layout.setContentsMargins(16, 24, 16, 16)
        report_layout.setVerticalSpacing(15)
        report_layout.setHorizontalSpacing(15)

        self.morning_edit = QTimeEdit()
        self.morning_edit.setDisplayFormat("HH:mm")
        # 移除上下按钮后，设置对齐方式居中会更好看
        self.morning_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.evening_edit = QTimeEdit()
        self.evening_edit.setDisplayFormat("HH:mm")
        self.evening_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        report_layout.addWidget(QLabel("🌞 早报推送"), 0, 0)
        report_layout.addWidget(self.morning_edit, 0, 1)
        report_layout.addWidget(QLabel("🌙 晚报推送"), 1, 0)
        report_layout.addWidget(self.evening_edit, 1, 1)

        report_group.setLayout(report_layout)
        layout.addWidget(report_group)

        # === 4. 语义时间定义 ===
        time_def_group = QGroupBox("语义时间定义")
        self.time_def_layout = QGridLayout()
        self.time_def_layout.setContentsMargins(16, 24, 16, 16)
        self.time_def_layout.setVerticalSpacing(12)
        self.time_def_layout.setHorizontalSpacing(15)

        self.time_editors = {}
        self.default_keywords = ["早上", "中午", "下午", "晚上", "夜里", "凌晨"]

        row = 0
        col = 0
        for keyword in self.default_keywords:
            lbl = QLabel(keyword)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            editor = QTimeEdit()
            editor.setDisplayFormat("HH:mm")
            editor.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 居中对齐
            self.time_editors[keyword] = editor

            self.time_def_layout.addWidget(lbl, row, col)
            self.time_def_layout.addWidget(editor, row, col + 1)

            col += 2
            if col >= 4:
                col = 0
                row += 1

        time_def_group.setLayout(self.time_def_layout)
        layout.addWidget(time_def_group)

        layout.addStretch()

        save_btn = QPushButton("保存配置")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save_config)
        save_btn.setFixedHeight(36)
        layout.addWidget(save_btn)

        scroll_area.setWidget(content_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

        self.load_current_config()

    def toggle_ai_input(self):
        is_ai = self.ai_check.isChecked()
        self.api_input.setEnabled(is_ai)
        if is_ai:
            self.api_input.setStyleSheet("")
        else:
            self.api_input.setStyleSheet("background-color: transparent; border: 1px dashed #555; color: #666;")

    def load_current_config(self):
        data = get_config()
        self.api_input.setText(data.get("api_key", ""))
        self.ai_check.setChecked(data.get("use_ai", True))
        self.toggle_ai_input()
        m_time = data.get("morning_time", "09:00")
        e_time = data.get("evening_time", "21:00")
        self.morning_edit.setTime(QTime.fromString(m_time, "HH:mm"))
        self.evening_edit.setTime(QTime.fromString(e_time, "HH:mm"))
        mapping = data.get("time_mapping", {})
        for k, editor in self.time_editors.items():
            time_str = mapping.get(k, "12:00")
            editor.setTime(QTime.fromString(time_str, "HH:mm"))

        # 加载邮件配置
        mail_conf = data.get("mail_config", {})
        self.smtp_server.setText(mail_conf.get("smtp_server", "smtp.163.com"))
        self.smtp_port.setText(str(mail_conf.get("smtp_port", "465")))
        self.sender_email.setText(mail_conf.get("sender_email", ""))
        self.email_pwd.setText(mail_conf.get("password", ""))
        self.receiver_email.setText(mail_conf.get("receiver_email", ""))

    def save_config(self):
        api_key_val = self.api_input.text().strip()
        api_key_val = "".join(c for c in api_key_val if 33 <= ord(c) <= 126)

        use_ai = self.ai_check.isChecked()
        m_time = self.morning_edit.time().toString("HH:mm")
        e_time = self.evening_edit.time().toString("HH:mm")

        new_mapping = {}
        for k, editor in self.time_editors.items():
            new_mapping[k] = editor.time().toString("HH:mm")
            if k == "早上": new_mapping["上午"] = new_mapping[k]
            if k == "晚上": new_mapping["傍晚"] = new_mapping[k]

        if use_ai and not api_key_val:
            QMessageBox.warning(self, "提示", "开启 AI 模式需要填写 API Key")
            return

        mail_config = {
            "smtp_server": self.smtp_server.text().strip(),
            "smtp_port": self.smtp_port.text().strip(),
            "sender_email": self.sender_email.text().strip(),
            "password": self.email_pwd.text().strip(),
            "receiver_email": self.receiver_email.text().strip()
        }
        if not mail_config["receiver_email"]:
            mail_config["receiver_email"] = mail_config["sender_email"]

        config = {
            "api_key": api_key_val,
            "model": "abab6.5s-chat",
            "use_ai": use_ai,
            "morning_time": m_time,
            "evening_time": e_time,
            "time_mapping": new_mapping,
            "mail_config": mail_config
        }

        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "已保存", "配置保存成功！")
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")


# --- Worker (保持不变) ---
class Worker(QObject):
    finished = pyqtSignal(str)
    ask_selection = pyqtSignal(list, dict)

    def analyze_offline_time(self, text, config):
        mapping = config.get("time_mapping", {})
        now = datetime.datetime.now()
        target_date = now
        has_time_logic = False

        if "明天" in text:
            target_date += datetime.timedelta(days=1)
            has_time_logic = True
        elif "后天" in text:
            target_date += datetime.timedelta(days=2)
            has_time_logic = True

        found_specific_time = False
        for keyword, time_str in mapping.items():
            if keyword in text:
                try:
                    parts = time_str.split(":")
                    h, m = int(parts[0]), int(parts[1])
                    target_date = target_date.replace(hour=h, minute=m, second=0)
                    found_specific_time = True
                    has_time_logic = True
                    break
                except:
                    continue

        if has_time_logic and not found_specific_time:
            if target_date.date() > now.date():
                target_date = target_date.replace(hour=9, minute=0, second=0)
            else:
                return None

        if has_time_logic:
            return target_date.strftime("%Y-%m-%d %H:%M:%S")
        return None

    def process(self, text):
        config = get_config()
        use_ai = config.get("use_ai", True)

        if not use_ai:
            if text.startswith("备忘录 ") or text.startswith("Memo "):
                content = text.split(" ", 1)[1]
                if content.strip():
                    append_to_note({"content": content})
                    self.finished.emit(f"📝 [离线] 已存入备忘录")
                else:
                    self.finished.emit(f"⚠️ 备忘录内容不能为空")
                return

            due_date = self.analyze_offline_time(text, config)
            task_data = {"title": text, "due_date": due_date}
            success = create_reminder(task_data)
            time_msg = f"\n⏰ {due_date}" if due_date else ""
            self.finished.emit(f"✅ [离线] 提醒已添加{time_msg}" if success else "❌ 添加失败")
            return

        result = parse_user_input(text)
        if result and result.get("error") == "missing_key":
            self.finished.emit("MISSING_KEY")
            return
        if not result:
            self.finished.emit("❌ AI 解析失败")
            return

        print(f"AI结果: {result}")
        item_type = result.get("type", "note")

        if item_type == "update":
            keyword = result.get("search_term", "")
            if not keyword:
                self.finished.emit("❌ 没听说要改哪个任务")
                return
            matches = search_reminders(keyword)
            if len(matches) == 0:
                self.finished.emit(f"❌ 找不到包含 '{keyword}' 的任务")
            elif len(matches) == 1:
                success = update_reminder_by_id(matches[0]['id'], result)
                self.finished.emit("✅ 任务已更新!" if success else "❌ 更新失败")
            else:
                self.ask_selection.emit(matches, result)
        elif item_type == "reminder":
            success = create_reminder(result)
            self.finished.emit("✅ 任务已添加!" if success else "❌ 添加失败")
        else:
            success = append_to_note(result)
            self.finished.emit("📝 笔记已记录!" if success else "❌ 记录失败")


# --- Scheduler (保持不变) ---
class SchedulerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True

    def run(self):
        config = get_config()
        m_time = config.get("morning_time", "09:00")
        e_time = config.get("evening_time", "21:00")
        print(f"⏰ 定时推送服务已启动 (早: {m_time}, 晚: {e_time})...")

        schedule.every().day.at(m_time).do(self.push_morning_briefing)
        schedule.every().day.at(e_time).do(self.push_daily_summary)

        while True:
            schedule.run_pending()
            time.sleep(1)

    def push_morning_briefing(self):
        print("Checking tasks for morning report...")
        message = get_todays_tasks()
        config = get_config()
        if "失败" not in message and "没有任务" not in message:
            send_email_notification("🌞 LazyMemo 早报", message, config.get("mail_config", {}))

    def push_daily_summary(self):
        message = get_todays_tasks()
        config = get_config()
        if "失败" not in message:
            send_email_notification("🌙 LazyMemo 晚间提醒", message, config.get("mail_config", {}))


# --- App (保持不变) ---
class LazyMemoApp(QWidget):
    show_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E1E; color: #FFFFFF;
                border: 2px solid #333333; border-radius: 15px;
                padding: 10px 20px; font-family: 'PingFang SC'; font-size: 18px;
            }
            QInputDialog { background-color: #2E2E2E; color: white; }
            QLabel { color: white; }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("LazyMemo Ready... (Double Tap Option)")
        self.input_field.returnPressed.connect(self.handle_input)
        layout.addWidget(self.input_field)
        self.setLayout(layout)
        self.resize(600, 60)
        self.center_on_screen()

        self.settings_window = None
        self.show_signal.connect(self.show_window)
        self.init_tray_icon()
        self.start_keyboard_listener()

        QTimer.singleShot(500, self.check_first_run)
        self.scheduler = SchedulerThread()
        self.scheduler.start()

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = os.path.join(BUNDLE_DIR, "tray_icon.png")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            pass

        tray_menu = QMenu()
        test_action = QAction("📧 测试发送邮件", self)
        test_action.triggered.connect(self.send_test_notification)
        tray_menu.addAction(test_action)
        tray_menu.addSeparator()

        show_action = QAction("显示/隐藏 LazyMemo", self)
        show_action.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(show_action)

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.open_settings)
        tray_menu.addAction(settings_action)
        tray_menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def send_test_notification(self):
        print("尝试发送测试邮件...")
        config = get_config()
        mail_conf = config.get("mail_config", {})
        if not mail_conf or not mail_conf.get("sender_email"):
            QMessageBox.warning(self, "缺少配置", "请先在设置中填写邮件发送信息！")
            return
        threading.Thread(target=lambda: send_email_notification(
            "LazyMemo 邮件测试",
            "恭喜！邮件配置正确。<br><br>这是一条测试消息。",
            mail_conf
        )).start()
        QMessageBox.information(self, "发送中", "测试邮件正在后台发送，请检查收件箱。")

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visibility()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show_window()

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_field.setFocus()
        self.input_field.clear()

    def check_first_run(self):
        config = get_config()
        if config.get("use_ai", True) and not config.get("api_key"):
            self.open_settings()

    def start_keyboard_listener(self):
        self.last_alt_time = 0

        def on_press(key):
            if key not in [keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r]:
                self.last_alt_time = 0

        def on_release(key):
            if key in [keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r]:
                current_time = time.time()
                if current_time - self.last_alt_time < 0.4:
                    self.show_signal.emit()
                    self.last_alt_time = 0
                else:
                    self.last_alt_time = current_time

        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape: self.hide()

    def center_on_screen(self):
        s = QApplication.primaryScreen().geometry()
        self.move((s.width() - self.width()) // 2, (s.height() // 3) - (self.height() // 2))

    def handle_input(self):
        text = self.input_field.text().strip()
        lower_text = text.lower()
        if not text: return
        if lower_text in ["退出", "exit", "quit"]: QApplication.quit(); return
        if lower_text in ["设置", "设定", "config"]:
            self.open_settings();
            self.input_field.clear();
            return

        self.input_field.clear()
        config = get_config()
        if config.get("use_ai", True):
            self.input_field.setPlaceholderText("Thinking... 🤖")
        else:
            self.input_field.setPlaceholderText("Processing (Offline)... ⚡️")

        self.worker = Worker()
        self.worker.finished.connect(self.on_finished)
        self.worker.ask_selection.connect(self.handle_multiple_matches)
        threading.Thread(target=self.worker.process, args=(text,)).start()

    def handle_multiple_matches(self, matches, update_data):
        items = []
        for i, m in enumerate(matches):
            note_preview = f" ({m['notes'][:10]}...)" if m['notes'] else ""
            items.append(f"{i + 1}. {m['title']}{note_preview}")
        item, ok = QInputDialog.getItem(self, "发现多个任务", "请选择要更新哪一个:", items, 0, False)
        if ok and item:
            index = items.index(item)
            selected_id = matches[index]['id']
            success = update_reminder_by_id(selected_id, update_data)
            self.on_finished("✅ 更新成功!" if success else "❌ 更新失败")
        else:
            self.on_finished("🚫 已取消")

    def on_finished(self, message):
        if message == "MISSING_KEY":
            self.input_field.setPlaceholderText("❌ 请先设置 API Key")
            self.open_settings()
            return
        self.input_field.setPlaceholderText(message)
        QTimer.singleShot(1500, self.hide)

    def open_settings(self):
        if not self.settings_window: self.settings_window = SettingsWindow()
        self.settings_window.show()
        s = QApplication.primaryScreen().geometry()
        self.settings_window.move((s.width() - self.settings_window.width()) // 2,
                                  (s.height() - self.settings_window.height()) // 2)
        self.settings_window.raise_()
        self.settings_window.activateWindow()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = LazyMemoApp()
    print("LazyMemo Running...")
    sys.exit(app.exec())
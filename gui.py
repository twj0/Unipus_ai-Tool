# File: gui.py (The Final Assembly)
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import threading, time, os, traceback
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import browser_handler, ai_handler, config_manager
from page_analyzer import PageAnalyzer
from task_handlers import *

class AutoAnswerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("U-Campus AI Agent - The Final Assembly")
        self.root.geometry("650x850")
        
        self.driver = None
        self.stop_flag = threading.Event()

        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.create_text_boxes(main_frame)
        self.create_controls(main_frame)
        self.create_status_bar()
        
        self.log("欢迎使用终极AI代理！")

    def create_text_boxes(self, parent):
        self.log_text = self.create_labeled_text(parent, "系统日志", height=10)
        self.task_list_text = self.create_labeled_text(parent, "任务详情", height=10)
        self.ai_debug_text = self.create_labeled_text(parent, "AI 交互详情", height=12)

    def create_labeled_text(self, parent, label, height):
        frame = tk.LabelFrame(parent, text=label, padx=5, pady=5)
        frame.pack(fill=tk.X, pady=5)
        text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=height)
        text_widget.pack(fill=tk.BOTH, expand=True)
        return text_widget

    def create_controls(self, parent):
        tk.Label(parent, text="请导航至课程任意任务页，然后点击“开始自动化”", fg="blue").pack(fill=tk.X, pady=5)
        controls_frame = tk.Frame(parent)
        controls_frame.pack(fill=tk.X, pady=10)
        tk.Label(controls_frame, text="AI 模型:").pack(side=tk.LEFT, padx=(0, 5))
        self.selected_model = tk.StringVar()
        self.model_dropdown = ttk.Combobox(controls_frame, textvariable=self.selected_model, state="readonly")
        self.model_dropdown['values'] = list(ai_handler.AI_PROVIDERS.keys())
        self.model_dropdown.current(0)
        self.model_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=5)
        self.connect_button = tk.Button(button_frame, text="连接浏览器", command=self.start_browser_thread)
        self.connect_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.run_button = tk.Button(button_frame, text="开始自动化", command=self.start_automation_thread, state=tk.DISABLED)
        self.run_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.stop_button = tk.Button(button_frame, text="停止", command=self.stop_automation, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
    def create_status_bar(self):
        self.status_label = tk.Label(self.root, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def log(self, message): self.root.after(0, self._log_update, message)
    def _log_update(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.status_label.config(text=message)
        print(message)

    def start_browser_thread(self):
        self.log("正在启动浏览器连接线程..."); self.connect_button.config(state=tk.DISABLED)
        threading.Thread(target=self.connect_browser, daemon=True).start()

    def start_automation_thread(self):
        self.log("开始执行顺序任务循环..."); self.stop_flag.clear()
        self.run_button.config(state=tk.DISABLED); self.stop_button.config(state=tk.NORMAL)
        threading.Thread(target=self.run_automation_loop, daemon=True).start()
        
    def stop_automation(self):
        if not self.stop_flag.is_set(): self.log("正在发送停止信号..."); self.stop_flag.set()
        self.run_button.config(state=tk.NORMAL); self.stop_button.config(state=tk.DISABLED)

    def connect_browser(self):
        try:
            self.driver = browser_handler.connect_or_start_browser(progress_callback=self.log)
            self.log("浏览器连接成功。")
            browser_handler.check_and_navigate(self.driver)
            self.log("已打开目标网站，请登录，然后导航至任意任务页。")
            self.root.after(0, lambda: self.run_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.connect_button.config(text="重新连接", state=tk.NORMAL))
        except Exception as e:
            self.log(f"连接浏览器失败: {e}"); messagebox.showerror("浏览器连接失败", str(e))
            self.root.after(0, lambda: self.connect_button.config(state=tk.NORMAL))

    def run_automation_loop(self):
        if not self.driver: self.root.after(0, self.stop_automation); return
        analyzer = PageAnalyzer(self.driver)

        try:
            self.log("-----------------------------------------")
            self.log("正在获取唯一的任务清单...")
            wait = WebDriverWait(self.driver, 15)
            all_tasks = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.pc-slider-menu-micro")))
            task_names = [t.text for t in all_tasks]
            self.task_list_text.delete(1.0, tk.END)
            self.task_list_text.insert(tk.END, "--- 行动清单 ---\n" + "\n".join(task_names))
            self.log(f"获取到 {len(all_tasks)} 个任务。将从头开始，顺序执行。")

            for i in range(len(all_tasks)):
                if self.stop_flag.is_set(): self.log("检测到停止信号。"); break
                
                # 为避免元素过时，每次循环都重新获取一次任务列表
                current_tasks_in_loop = self.driver.find_elements(By.CSS_SELECTOR, "div.pc-slider-menu-micro")
                if i >= len(current_tasks_in_loop): self.log("任务列表发生变化，无法继续。"); break
                task_to_click = current_tasks_in_loop[i]
                task_name = task_to_click.text.strip()

                self.log(f"---=> 正在执行任务 ({i+1}/{len(all_tasks)}): '{task_name}' <=---")
                self.driver.execute_script("arguments[0].click();", task_to_click)
                time.sleep(3) # 等待页面加载

                # 处理当前页面的所有内容
                try:
                    tabs = self.driver.find_elements(By.CSS_SELECTOR, "div.ant-tabs-tab")
                    if not tabs: tabs = [None]
                except: tabs = [None]

                for j in range(len(tabs)):
                    if self.stop_flag.is_set(): break
                    tab_name = "Main"
                    if tabs[0] is not None:
                        current_tabs_in_loop = self.driver.find_elements(By.CSS_SELECTOR, "div.ant-tabs-tab")
                        if j >= len(current_tabs_in_loop): continue
                        current_tab = current_tabs_in_loop[j]
                        tab_name = current_tab.text.strip()
                        self.log(f"---处理Tab页: '{tab_name}'---")
                        current_tab.click(); time.sleep(2)
                    
                    page_type = analyzer.get_page_type_in_tab()
                    self.log(f"Tab页内内容类型为: {page_type}")
                    
                    handler_map = {
                        "VIDEO": handle_video_page, "VOCABULARY_FLASHCARDS": handle_vocabulary_flashcards,
                        "QUIZ_TRUE_FALSE_NG": handle_quiz_true_false, "QUIZ_FILL_IN_BLANK": handle_quiz_fill_in_blank,
                        "QUIZ_VOCABULARY_CHOICE": handle_quiz_vocabulary_choice, "QUIZ_REWRITE_SENTENCE": handle_quiz_rewrite_sentence,
                        "QUIZ_TRANSLATE": handle_quiz_translate,
                        "READING": handle_skip_page, "REPEATING_AFTER_ME": handle_skip_page, "UNIT_PROJECT": handle_skip_page,
                    }
                    handler_map.get(page_type, handle_unknown_page)(self.driver, self)
                
                if self.stop_flag.is_set(): break
                self.log(f"主任务 '{task_name}' 已处理完毕。")

            self.log("所有任务已按顺序执行完毕。")

        except WebDriverException as e: self.log(f"浏览器错误: {e}")
        except Exception as e: self.log(f"发生未知错误: {e}"); traceback.print_exc()
        
        self.root.after(0, self.stop_automation)
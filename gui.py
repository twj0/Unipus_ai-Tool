# File: gui.py
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import threading
import time
import os

# 导入我们的新模块和更新后的模块
import browser_handler
import ai_handler
import config_manager
from page_analyzer import PageAnalyzer
from task_handlers import handle_video_page, handle_quiz_fill_in_blank, handle_reading_page, handle_unknown_page

# v--vv--vv--vv--vv--vv--vv--v
# --- 补上缺失的Selenium导入 ---
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
# ^--^^--^^--^^--^^--^^--^^--^

class AutoAnswerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("U-Campus AI Assistant v3.0 (WIP)")
        self.root.geometry("650x850")
        
        self.driver = None
        self.stop_flag = threading.Event() # 使用Event来优雅地停止线程

        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.create_text_boxes(main_frame)
        self.create_controls(main_frame)
        self.create_status_bar()
        
        self.log("欢迎使用全能助手！请先连接到浏览器。")

    def create_text_boxes(self, parent):
        self.log_text = self.create_labeled_text(parent, "系统日志", height=10)
        self.task_list_text = self.create_labeled_text(parent, "检测到的任务列表", height=10)
        self.ai_debug_text = self.create_labeled_text(parent, "AI 交互详情", height=12)

    def create_labeled_text(self, parent, label, height):
        frame = tk.LabelFrame(parent, text=label, padx=5, pady=5)
        frame.pack(fill=tk.X, pady=5)
        text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=height)
        text_widget.pack(fill=tk.BOTH, expand=True)
        return text_widget

    def create_controls(self, parent):
        tk.Label(parent, text="请导航至课程的主目录页面后，再点击开始自动化。", fg="blue").pack(fill=tk.X, pady=5)

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

    def log(self, message):
        # 确保在主线程中更新UI
        self.root.after(0, self._log_update, message)
        
    def _log_update(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.status_label.config(text=message)
        print(message) # 在控制台也打印一份，便于调试

    # --- 线程管理 ---
    def start_browser_thread(self):
        self.log("正在启动浏览器连接线程...")
        self.connect_button.config(state=tk.DISABLED)
        threading.Thread(target=self.connect_browser, daemon=True).start()

    def start_automation_thread(self):
        self.log("开始执行全自动任务循环...")
        self.stop_flag.clear() # 重置停止标志
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        threading.Thread(target=self.run_automation_loop, daemon=True).start()
        
    def stop_automation(self):
        self.log("正在发送停止信号...")
        self.stop_flag.set() # 设置停止事件
        self.stop_button.config(state=tk.DISABLED)

    # --- 核心逻辑 ---
    def connect_browser(self):
        try:
            # 使用新的全自动驱动管理器
            self.driver = browser_handler.connect_or_start_chrome(progress_callback=self.log)
            self.log("浏览器连接成功。")
            
            # 更新UI状态
            self.root.after(0, lambda: self.run_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.connect_button.config(text="重新连接", state=tk.NORMAL))

        except Exception as e:
            self.log(f"连接浏览器失败: {e}")
            messagebox.showerror("浏览器连接失败", str(e))
            self.root.after(0, lambda: self.connect_button.config(state=tk.NORMAL))

    def run_automation_loop(self):
        """
        这是新的主自动化循环，是整个智能代理的“大脑”。
        """
        if not self.driver:
            self.log("错误：浏览器未连接。")
            return

        try:
            # 1. 获取任务列表
            self.log("正在分析课程目录，请确保当前在课程主页...")
            
            # 使用显式等待确保菜单加载完成
            wait = WebDriverWait(self.driver, 20)
            task_elements_container = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.slider-menu-container"))
            )
            tasks = task_elements_container.find_elements(By.CSS_SELECTOR, "div.pc-slider-menu-micro")
            
            if not tasks:
                self.log("在当前页面未找到任何课程任务项，请手动导航到课程目录页。")
                return

            self.log(f"成功检测到 {len(tasks)} 个任务项。")
            self.root.after(0, self.task_list_text.delete, '1.0', tk.END)
            for i, task in enumerate(tasks):
                self.root.after(0, self.task_list_text.insert, tk.END, f"{i+1}. {task.text.strip()}\n")
            
            # 2. 循环执行任务
            for i in range(len(tasks)):
                if self.stop_flag.is_set():
                    self.log("检测到停止信号，任务循环终止。")
                    break

                # 重新获取元素以避免StaleElementReferenceException
                current_task_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.pc-slider-menu-micro")
                if i >= len(current_task_elements):
                    self.log("任务列表发生变化，无法继续。")
                    break
                
                task_to_click = current_task_elements[i]
                task_name = task_to_click.text.strip()
                self.log(f"---=> 开始处理任务({i+1}/{len(tasks)}): {task_name} <=---")
                
                task_to_click.click()
                time.sleep(3) # 等待页面跳转

                # 3. 分析页面类型并分发任务
                analyzer = PageAnalyzer(self.driver)
                page_type = analyzer.get_page_type()
                self.log(f"页面分析完成，类型为: {page_type}")

                # 这是任务分发的核心
                if page_type == "VIDEO":
                    handle_video_page(self.driver, self) # 传入self以使用log等方法
                elif page_type == "QUIZ_FILL_IN_BLANK":
                    handle_quiz_fill_in_blank(self.driver, self)
                elif page_type == "READING":
                    handle_reading_page(self.driver, self)
                else: # 包括 QUIZ_MULTIPLE_CHOICE (暂未实现), UNKNOWN 等
                    handle_unknown_page(self.driver, self)

                self.log(f"任务 '{task_name}' 处理完毕。")
                time.sleep(2) # 返回前的短暂等待
                
                # 返回课程目录页面以进行下一个任务
                self.driver.back()
                self.log("已返回课程目录，准备下一个任务。")
                time.sleep(3) # 等待目录页面重新加载稳定

            self.log("所有任务已处理完毕！")

        except Exception as e:
            self.log(f"自动化循环中发生严重错误: {e}")
            import traceback
            traceback.print_exc() # 在控制台打印详细的错误堆栈
            messagebox.showerror("运行时错误", f"自动化流程中断:\n{e}")
        finally:
            self.root.after(0, lambda: self.run_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
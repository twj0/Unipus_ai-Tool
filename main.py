import tkinter as tk
from tkinter import scrolledtext, ttk
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
import requests
import json
import threading
import time
import re
import os
import sys
import configparser

# ================== 配置参数 ==================
# 获取当前运行路径（适用于开发环境和打包后的exe）
if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))

# 读取配置文件
config_path = os.path.join(current_dir, 'config.ini')
config = configparser.ConfigParser()
config.read(config_path, encoding='utf-8')

# 读取配置项
CHROME_DRIVER_PATH = os.path.join(current_dir, config.get('Settings', 'chrome_driver_path'))
DASHSCOPE_API_KEY = config.get('Settings', 'dashscope_api_key')

print(CHROME_DRIVER_PATH)
print(DASHSCOPE_API_KEY)
# 支持流式调用的模型列表
STREAMING_MODELS = [
    "qwen3-235b-a22b"
]

# 模型选项（显示名称 → 实际 model name）
MODEL_OPTIONS = {
    "推理模型 Qwen3": "qwen3-235b-a22b",
    "通义千问 Qwen-Max": "qwen-max",
    "通义千问 Qwen-Plus": "qwen-plus"
}

# 默认使用第一个模型
DEFAULT_MODEL = list(MODEL_OPTIONS.values())[0]

# ================== 创建 GUI 主窗口 ==================
class AutoAnswerGUI:
    def __init__(self, root):
        """初始化主界面组件"""
        self.root = root
        self.root.title("英语填空题自动答题助手 v1.0")
        self.root.resizable(False, False)
        self.root.geometry("600x800")
        
        # 配置网格布局权重
        for i in range(8):
            self.root.grid_rowconfigure(i, weight=1 if i in [0, 1, 2, 3, 4] else 0)
        for i in range(2):
            self.root.grid_columnconfigure(i, weight=1)

        # 创建界面组件
        self.log_text = self.create_text_box("运行日志", row=0, height=10)
        self.question_text = self.create_text_box("题目内容", row=1, height=8)
        self.prompt_text = self.create_text_box("发送给 AI 的 Prompt", row=2, height=12)
        self.content_text = self.create_text_box("AI 返回的 content", row=3, height=6)
        self.reasoning_text = self.create_text_box("AI 返回的 reasoning", row=4, height=6)

        # 模型选择下拉框
        self.selected_model = tk.StringVar()
        self.model_dropdown = ttk.Combobox(root, textvariable=self.selected_model)
        self.model_dropdown['values'] = list(MODEL_OPTIONS.keys())
        self.model_dropdown.current(0)
        self.model_dropdown.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        # 按钮布局
        button_frame = tk.Frame(root)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10, sticky="ew")
        
        left_spacer = tk.Frame(button_frame, width=50)
        left_spacer.pack(side="left", expand=True)
        
        self.start_browser_button = tk.Button(button_frame, text="启动程序", command=self.start_browser_only, width=20)
        self.start_browser_button.pack(side="left", padx=5)
        
        self.auto_answer_button = tk.Button(button_frame, text="自动答题", command=self.start_auto_answer, width=20)
        self.auto_answer_button.pack(side="left", padx=5)
        
        self.clear_button = tk.Button(button_frame, text="清除所有填空", command=self.clear_all_inputs, width=20)
        self.clear_button.pack(side="left", padx=5)
        
        right_spacer = tk.Frame(button_frame, width=100)
        right_spacer.pack(side="left", expand=True)

        # 版本信息
        version_label = tk.Label(root, text="v1.0 | By Wuuz", anchor="center")
        version_label.grid(row=7, column=0, columnspan=2, pady=5)

    def create_text_box(self, label_text, row, height=5):
        """创建带标签的文本框组件"""
        frame = tk.Frame(self.root)
        frame.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        
        label = tk.Label(frame, text=label_text, anchor="w")
        label.pack(fill="x")
        
        text_box = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=height, width=100)
        text_box.pack(fill="both", expand=True)
        return text_box

    def log(self, message):
        """日志输出方法"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def get_selected_model_name(self):
        """获取选中的模型名称"""
        display_name = self.selected_model.get()
        return MODEL_OPTIONS[display_name]

    def start_browser_only(self):
        """启动浏览器连接线程"""
        self.log("正在连接或启动浏览器...")
        threading.Thread(target=self.connect_browser).start()

    def connect_browser(self):
        """浏览器连接核心逻辑"""
        try:
            driver = connect_or_start_chrome()
            current_url = driver.current_url
            
            def is_valid_target_url(url, prefixes):
                for prefix in prefixes:
                    if url == prefix or url.startswith(prefix + "/") or url.startswith(prefix + "?") or url.startswith(prefix + "#"):
                        return True
                return False
            
            valid_prefixes = ["https://uai.unipus.cn",   "https://ucloud.unipus.cn",   "https://ucontent.unipus.cn"]  
            is_valid_url = is_valid_target_url(current_url, valid_prefixes)
            
            if is_valid_url:
                self.log(f"已连接到目标网站")
            else:
                target_url = "https://ucloud.unipus.cn/"  
                self.log(f"当前页面不是目标网站，正在跳转至 {target_url}")
                driver.get(target_url)
                time.sleep(2)
                new_url = driver.current_url
                self.log(f"页面已跳转至：{new_url}")
                
            self.driver = driver
            
        except Exception as e:
            self.log(f"连接浏览器失败：{e}")

    def start_auto_answer(self):
        """启动自动答题线程"""
        self.log("开始自动答题流程...")
        if not hasattr(self, 'driver'):
            self.log("请先点击【启动程序】连接浏览器！")
            return
        threading.Thread(target=self.run_auto_answer).start()

    def run_auto_answer(self):
        """自动答题主流程"""
        self.log("开始执行任务...")
        if not hasattr(self, 'driver'):
            self.log("请先点击【启动程序】连接浏览器！")
            return
            
        driver = self.driver
        
        # 提取题目数据
        data = extract_questions_from_page(driver)
        self.log("提取题目内容完成")
        
        # 清洗题目内容
        cleaned_questions = [re.sub(r"^\d+\.\s*", "", q).strip() for q in data["questions"]]
        question_display = "\n".join([f"{i+1}. {cleaned_questions[i]}" for i in range(len(cleaned_questions))])
        
        # 更新题目显示区域
        self.question_text.delete(1.0, tk.END)
        self.question_text.insert(tk.END, question_display)
        
        # 判断题型
        question_type = determine_question_type(data["instruction"])
        self.log(f"当前题型：{question_type}")
        
        if question_type=="unknown":
            self.log("题型未知，中止post")
            return
            
        # 获取空格数量
        total_questions = len(data["questions"])
        blank_counts = extract_blank_counts(driver, total_questions)
        
        # 构造Prompt
        prompt = build_prompt(data["instruction"], cleaned_questions, data["options"], blank_counts=blank_counts)
        self.prompt_text.delete(1.0, tk.END)
        self.prompt_text.insert(tk.END, prompt)
        
        # 调用AI模型
        selected_model_id = self.get_selected_model_name()
        self.log(f"正在调用模型：{selected_model_id}")
        ai_response = call_ai(prompt, selected_model_id)
        
        # 解析答案
        answers = parse_ai_answer(ai_response)
        self.log(f"解析出的答案结构：{answers}")
        
        if not answers:
            self.log("未解析到有效答案，停止填写流程")
            return
            
        # 显示AI返回结果
        try:
            result_json = json.loads(ai_response) if isinstance(ai_response, str) and ai_response.startswith("{") else {}
            content = result_json.get('output', {}).get('text', '') 
            reasoning = "" 
            self.content_text.delete(1.0, tk.END)
            self.content_text.insert(tk.END, content)
            self.reasoning_text.delete(1.0, tk.END)
            self.reasoning_text.insert(tk.END, reasoning)
            self.log("AI 返回结果已更新到界面")
        except Exception as e:
            self.log(f"解析 AI 返回失败：{e}")
            
        # 填写答案到网页
        self.log("填写答案到网页...")
        fill_answers_to_webpage(driver, answers, question_type=question_type)
        self.log("自动答题已完成！")

    def clear_all_inputs(self):
        """清除网页中的填空内容"""
        self.log("正在清除网页中的填空内容...")
        try:
            driver = self.driver
            data = extract_questions_from_page(driver)
            total_questions = len(data["questions"])
            
            for index in range(total_questions):
                input_xpath_base = f'/html/body/div[3]/div[1]/div[1]/section/section/main/div/div/div/div[3]/div/div[2]/div/div/p[{index + 1}]'
                p_element = driver.find_element(By.XPATH, input_xpath_base)
                inputs = p_element.find_elements(By.TAG_NAME, 'input')
                for input_box in inputs:
                    input_box.clear()
                    
            self.log("所有填空内容已清除")
            
        except Exception as e:
            self.log(f"清除填空失败：{e}")

# ================== Selenium 浏览器连接函数 ==================
def connect_or_start_chrome():
    """连接或启动Chrome浏览器"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    service = Service(CHROME_DRIVER_PATH)
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except WebDriverException:
        new_options = Options()
        new_options.add_argument("--remote-debugging-port=9222")
        new_options.add_argument("--user-data-dir=./chrome-profile")
        driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=new_options)
        return driver

# ================== 提取题目内容 ==================
def extract_questions_from_page(driver):
    """从网页提取题目内容（指令、问题、选项）"""
    data = {"instruction": "", "questions": [], "options": []}
    
    try:
        instruction_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH,
                '/html/body/div[3]/div[1]/div[1]/section/section/main/div/div/div/div[1]/div/div/p'))
        )
        data["instruction"] = instruction_element.text.strip()
    except Exception as e:
        pass
        
    try:
        question_elements = driver.find_elements(By.XPATH,
            '/html/body/div[3]/div[1]/div[1]/section/section/main/div/div/div/div[3]/div/div[2]/div/div/p')
        data["questions"] = [q.text.strip() for q in question_elements]
    except Exception as e:
        pass
        
    try:
        script = """
        const options = [];
        const elements = document.querySelectorAll('div.option');
        for (const el of elements) {
            let text = el.textContent.trim();
            if (!text) text = el.innerText.trim();
            if (text) options.push(text);
        }
        return options;
        """
        data["options"] = driver.execute_script(script)
    except Exception as e:
        pass
        
    return data

# ================== 题型判断与处理 ==================
def determine_question_type(instruction):
    """判断题目类型（单空题/多空题）"""
    single_blank_keyword = "Fill in the blanks with the words given below. Change the form where necessary. Each word can be used only once."
    multi_blanks_keyword = "Fill in the blanks by selecting suitable words from the word bank. You may not use any of the words more than once."
    
    if single_blank_keyword in instruction:
        return "single_blank_per_question"
    elif multi_blanks_keyword in instruction:
        return "multiple_blanks_per_question"
    else:
        return "unknown"

def get_blanks_count_for_question(driver, question_index):
    """获取单个题目的空格数量"""
    try:
        p_xpath = f'/html/body/div[3]/div[1]/div[1]/section/section/main/div/div/div/div[3]/div/div[2]/div/div/p[{question_index + 1}]'
        p_element = driver.find_element(By.XPATH, p_xpath)
        return len(p_element.find_elements(By.TAG_NAME, 'input'))
    except Exception as e:
        return 0

def extract_blank_counts(driver, total_questions):
    """批量获取所有题目的空格数量"""
    return [get_blanks_count_for_question(driver, i) for i in range(total_questions)]

# ================== AI 交互处理 ==================
def build_prompt(instruction, questions, options, blank_counts=None):
    """构建发送给AI的提示词"""
    cleaned_questions = [re.sub(r"^\d+\.\s*", "", q).strip() for q in questions]
    questions_block = "\n".join([f"{i+1}. {cleaned_questions[i]}" for i in range(len(cleaned_questions))])
    options_block = ", ".join(options)
    
    prompt = f"""
你是一个英语填空题解答助手。我会给你一段题目内容，请你根据提供的可选单词，填写每个空格中最合适的词。
题目内容如下：
{questions_block}
可选单词如下：
{options_block}
"""
    if blank_counts:
        prompt += "\n请根据以下空格数量填写答案：\n"
        for i, count in enumerate(blank_counts):
            prompt += f"第 {i+1} 题有 {count} 个空格\n"
            
    prompt += "\n请严格按照以下格式输出答案，不要添加任何额外解释或内容：\n答案：\n"
    
    for i in range(len(questions)):
        if blank_counts and blank_counts[i] > 0:
            placeholder = "|".join(["word/phrase"] * blank_counts[i])
            prompt += f"{i+1}. {placeholder}\n"
        else:
            prompt += f"{i+1}. word\n"
            
    return prompt

def call_ai(prompt, selected_model_id):
    """调用AI接口进行推理"""
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "AnswerBot/1.0"
    }
    
    payload = {
        "model": selected_model_id,
        "input": {"prompt": prompt},
        "parameters": {"enable_thinking": False, "result_format": "text"}
    }
    
    stream = selected_model_id in STREAMING_MODELS
    if stream:
        payload["parameters"]["stream"] = True
        
    try:
        response = requests.post(
            url="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",  
            headers=headers,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            timeout=30
        )
        return response.text
    except Exception as e:
        return f'{{"error": "{str(e)}"}}'

def parse_ai_answer(ai_response):
    """解析AI返回的JSON格式答案"""
    try:
        result = json.loads(ai_response) if isinstance(ai_response, str) and ai_response.startswith("{") else {}
        answer_text = ""
        
        if 'output' in result:
            answer_text = result['output'].get('text', '').strip()
        elif 'choices' in result:
            answer_text = result['choices'][0]['message'].get('content', '').strip()
            
        if not answer_text:
            return []
            
        if "答案：" in answer_text:
            answer_text = answer_text.split("答案：", 1)[1].strip()
            
        lines = answer_text.splitlines()
        answers = []
        
        for line in lines:
            line = line.strip()
            if line.startswith(tuple(f"{i+1}." for i in range(20))):
                try:
                    content = line.split(".", 1)[1].strip()
                    multi_answers = [ans.strip() for ans in content.split("|")]
                    answers.append(multi_answers)
                except Exception as e:
                    continue
                    
        return answers
        
    except Exception as e:
        print(f"解析 AI 回答失败：{e}")
        return []

# ================== 答案填写逻辑 ==================
def fill_answers_to_webpage(driver, answers, question_type="single_blank_per_question"):
    """将答案填写到网页对应输入框"""
    if not answers:
        print("没有可填写的答案")
        return
        
    if question_type == "single_blank_per_question":
        for index, answer in enumerate(answers):
            input_xpath = f'/html/body/div[3]/div[1]/div[1]/section/section/main/div/div/div/div[3]/div/div[2]/div/div/p[{index + 1}]//input'
            try:
                input_box = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, input_xpath))
                )
                input_box.clear()
                if answer and isinstance(answer, list) and len(answer) > 0:
                    input_box.send_keys(answer[0])
            except Exception as e:
                print(f"第 {index + 1} 题填写失败：{e} | XPath: {input_xpath}")
                
    elif question_type == "multiple_blanks_per_question":
        for index, answer in enumerate(answers):
            p_xpath = f'/html/body/div[3]/div[1]/div[1]/section/section/main/div/div/div/div[3]/div/div[2]/div/div/p[{index + 1}]'
            try:
                p_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, p_xpath))
                )
                inputs = p_element.find_elements(By.XPATH, './/span//input')
                
                if index >= len(answers) or not answers[index]:
                    continue
                    
                for i, input_box in enumerate(inputs):
                    input_box.clear()
                    if i < len(answers[index]):
                        input_box.send_keys(answers[index][i])
                        
            except Exception as e:
                print(f"第 {index+1} 题填写失败：{e}")

# ================== 程序入口 ==================
if __name__ == "__main__":
    root = tk.Tk()
    app = AutoAnswerGUI(root)
    root.mainloop()
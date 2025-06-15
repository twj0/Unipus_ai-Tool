# File: browser_handler.py (Corrected Version)
import socket, time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
from driver_manager import WebDriverManager

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def connect_or_start_browser(progress_callback=print):
    manager = WebDriverManager(progress_callback=progress_callback)
    browser_type, driver_path = manager.check_and_get_driver()

    if browser_type == 'chrome':
        options = ChromeOptions()
        service = ChromeService(driver_path)
        driver_class = webdriver.Chrome
    elif browser_type == 'edge':
        options = EdgeOptions()
        service = EdgeService(driver_path)
        driver_class = webdriver.Edge
    else:
        raise RuntimeError("不支持的浏览器类型")
    
    progress_callback(f"正在使用 {browser_type.capitalize()} 浏览器...")

    if is_port_in_use(9222):
        progress_callback("检测到调试端口9222已占用，尝试连接...")
        try:
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = driver_class(service=service, options=options)
            progress_callback("成功连接到现有浏览器！")
            return driver
        except Exception as e:
            progress_callback(f"连接失败: {e}。将启动新实例。")

    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = driver_class(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    progress_callback("新的浏览器实例已成功启动！")
    return driver

# v--vv--vv--vv--vv--vv--vv--v
# --- 这是修正后的干净版本 ---
def check_and_navigate(driver, target_url="https://ucloud.unipus.cn/"):
    """检查司机是否在目标网站上，如果不在，则进行导航。"""
    valid_prefixes = ["https://uai.unipus.cn", "https://ucloud.unipus.cn", "https://ucontent.unipus.cn"]
    current_url = driver.current_url
    
    if not any(current_url.startswith(prefix) for prefix in valid_prefixes):
        print(f"当前页面不是目标网站，正在导航至 {target_url}")
        driver.get(target_url)
        time.sleep(3) # 等待可能的重定向
        print(f"已导航至: {driver.current_url}")
# ^--^^--^^--^^--^^--^^--^^--^

def extract_questions_from_page(driver):
    """从网页中提取指令、问题和选项。"""
    data = {"instruction": "", "questions": [], "options": []}
    wait = WebDriverWait(driver, 10)
    try:
        instruction_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.instruction p, div.direction-text p')))
        data["instruction"] = instruction_element.text.strip()
    except TimeoutException: pass
    try:
        question_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.questions-wrapper, div.ques-wrapper')))
        data["questions"] = [q.text.strip() for q in question_container.find_elements(By.TAG_NAME, 'p') if q.text.strip()]
    except TimeoutException: pass
    try:
        option_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.word-bank div.option, div.word-bank-item')))
        data["options"] = [opt.text.strip() for opt in option_elements if opt.text.strip()]
    except TimeoutException: pass
    return data

def get_blank_counts(driver, question_count: int) -> list:
    """获取每个问题的输入框数量。"""
    counts = []
    try:
        question_paragraphs = driver.find_elements(By.XPATH, '//div[contains(@class, "questions-wrapper")]//p | //div[contains(@class, "ques-wrapper")]//p')
        if len(question_paragraphs) < question_count: return [1] * question_count
        for i in range(question_count):
            counts.append(len(question_paragraphs[i].find_elements(By.TAG_NAME, 'input')))
    except Exception: return [1] * question_count # 出错时默认返回1
    return counts
    
def fill_answers_to_webpage(driver, answers: list):
    """将提取的答案填写到网页的输入字段中。"""
    if not answers: return
    try:
        question_paragraphs = driver.find_elements(By.XPATH, '//div[contains(@class, "questions-wrapper")]//p | //div[contains(@class, "ques-wrapper")]//p')
        for i, answer_group in enumerate(answers):
            if i >= len(question_paragraphs): break
            inputs = question_paragraphs[i].find_elements(By.TAG_NAME, 'input')
            for j, input_box in enumerate(inputs):
                if j < len(answer_group):
                    input_box.clear(); input_box.send_keys(answer_group[j])
    except Exception as e: print(f"填写答案时出错: {e}")

def clear_all_inputs(driver):
    """清除问题区域中的所有输入字段。"""
    try:
        all_inputs = driver.find_elements(By.XPATH, '//div[contains(@class, "questions-wrapper")]//input | //div[contains(@class, "ques-wrapper")]//input')
        for input_box in all_inputs: input_box.clear()
        print(f"清除了 {len(all_inputs)} 个输入字段。")
    except Exception as e: print(f"清除输入框时出错: {e}")
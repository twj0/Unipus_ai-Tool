# File: browser_handler.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
import time

# 导入我们全新的、强大的驱动管理器！
from driver_manager import ChromeDriverManager

def connect_or_start_chrome(progress_callback=print):
    """
    使用全自动的驱动管理器来连接或启动Chrome浏览器。
    不再需要手动提供driver_path。
    """
    manager = ChromeDriverManager(progress_callback=progress_callback)
    try:
        # 让管理器检查并返回一个保证可用的驱动路径
        driver_path = manager.check_and_get_driver()
        service = Service(driver_path)

        # 尝试连接到一个已在运行的调试实例
        try:
            progress_callback("正在尝试连接到已存在的Chrome调试实例...")
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            progress_callback("成功连接到现有浏览器！")
            return driver
        except WebDriverException:
            progress_callback("未找到调试实例，将启动一个全新的Chrome浏览器...")
            new_options = Options()
            new_options.add_argument("--remote-debugging-port=9222")
            # 添加一些反检测的选项
            new_options.add_argument("--disable-blink-features=AutomationControlled")
            new_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            new_options.add_experimental_option('useAutomationExtension', False)
            
            driver = webdriver.Chrome(service=service, options=new_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            progress_callback("新的Chrome实例已成功启动！")
            return driver

    except Exception as e:
        progress_callback(f"启动浏览器时发生严重错误: {e}")
        # 在GUI中，我们应该用messagebox来显示这个错误
        raise e


def check_and_navigate(driver, target_url="https://ucloud.unipus.cn/"):
    """检查司机是否在目标网站上，如果不在，则进行导航。"""
    valid_prefixes = ["https://uai.unipus.cn", "https://ucloud.unipus.cn", "https://ucontent.unipus.cn"]
    current_url = driver.current_url
    
    is_valid = any(current_url.startswith(prefix) for prefix in valid_prefixes)
    
    if is_valid:
        print(f"已在有效页面: {current_url}")
        return True
    else:
        print(f"当前页面不是目标网站，正在导航至 {target_url}")
        driver.get(target_url)
        time.sleep(3) # 等待可能的重定向
        print(f"已导航至: {driver.current_url}")
        return False

def extract_questions_from_page(driver):
    """从网页中提取指令、问题和选项。"""
    data = {"instruction": "", "questions": [], "options": []}
    wait = WebDriverWait(driver, 10)
    
    try:
        # 注意：这些CSS选择器是猜测值，可能需要调整
        instruction_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.instruction p, div.direction-text p')))
        data["instruction"] = instruction_element.text.strip()
    except TimeoutException:
        print("无法找到指令元素。")

    try:
        question_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.questions-wrapper, div.ques-wrapper')))
        question_elements = question_container.find_elements(By.TAG_NAME, 'p')
        data["questions"] = [q.text.strip() for q in question_elements if q.text.strip()]
    except TimeoutException:
        print("无法找到问题元素。")

    try:
        option_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.word-bank div.option, div.word-bank-item')))
        data["options"] = [opt.text.strip() for opt in option_elements if opt.text.strip()]
    except TimeoutException:
        print("无法找到选项元素。")
        
    return data

def get_blank_counts(driver, question_count: int) -> list:
    """获取每个问题的输入框数量。"""
    counts = []
    question_paragraphs = driver.find_elements(By.XPATH, '//div[contains(@class, "questions-wrapper")]//p | //div[contains(@class, "ques-wrapper")]//p')

    if len(question_paragraphs) < question_count:
        return [1] * question_count

    for i in range(question_count):
        p_element = question_paragraphs[i]
        inputs = p_element.find_elements(By.TAG_NAME, 'input')
        counts.append(len(inputs))
    return counts
    
def fill_answers_to_webpage(driver, answers: list):
    """将提取的答案填写到网页的输入字段中。"""
    if not answers:
        print("没有可填写的答案。")
        return
        
    question_paragraphs = driver.find_elements(By.XPATH, '//div[contains(@class, "questions-wrapper")]//p | //div[contains(@class, "ques-wrapper")]//p')

    for i, answer_group in enumerate(answers):
        if i >= len(question_paragraphs):
            break
            
        p_element = question_paragraphs[i]
        inputs = p_element.find_elements(By.TAG_NAME, 'input')
        
        for j, input_box in enumerate(inputs):
            if j < len(answer_group):
                try:
                    input_box.clear()
                    input_box.send_keys(answer_group[j])
                except Exception as e:
                    print(f"填写Q{i+1}的第{j+1}个空格时出错: {e}")

def clear_all_inputs(driver):
    """清除问题区域中的所有输入字段。"""
    all_inputs = driver.find_elements(By.XPATH, '//div[contains(@class, "questions-wrapper")]//input | //div[contains(@class, "ques-wrapper")]//input')
    for input_box in all_inputs:
        try:
            input_box.clear()
        except Exception as e:
            print(f"无法清除输入框: {e}")
    print(f"清除了 {len(all_inputs)} 个输入字段。")
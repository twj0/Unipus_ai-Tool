# File: browser_handler.py
import socket, time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from driver_manager import ChromeDriverManager

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def connect_or_start_chrome(progress_callback=print):
    manager = ChromeDriverManager(progress_callback=progress_callback)
    try:
        driver_path = manager.check_and_get_driver(); service = Service(driver_path)
        if is_port_in_use(9222):
            progress_callback("检测到调试端口9222，正在尝试连接...")
            try:
                chrome_options = Options(); chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
                driver = webdriver.Chrome(service=service, options=chrome_options); progress_callback("成功连接到现有浏览器！"); return driver
            except Exception as e: progress_callback(f"连接失败: {e}")
        
        progress_callback("未找到调试实例，将启动一个全新的Chrome浏览器...")
        new_options = Options()
        new_options.add_argument("--remote-debugging-port=9222"); new_options.add_argument("--disable-blink-features=AutomationControlled")
        new_options.add_experimental_option("excludeSwitches", ["enable-automation"]); new_options.add_experimental_option('useAutomationExtension', False)
        driver = webdriver.Chrome(service=service, options=new_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        progress_callback("新的Chrome实例已成功启动！"); return driver
    except Exception as e: progress_callback(f"启动浏览器时发生严重错误: {e}"); raise e

def check_and_navigate(driver, target_url="https://ucloud.unipus.cn/"):
    valid_prefixes = ["https://uai.unipus.cn", "https://ucloud.unipus.cn", "https://ucontent.unipus.cn"]
    current_url = driver.current_url
    if not any(current_url.startswith(prefix) for prefix in valid_prefixes):
        driver.get(target_url); time.sleep(3)
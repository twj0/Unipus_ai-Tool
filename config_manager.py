# File: config_manager.py
import configparser
import os
import sys
import tkinter.messagebox

def get_current_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

CURRENT_DIR = get_current_dir()
CONFIG_PATH = os.path.join(CURRENT_DIR, 'config.ini')

def create_default_config():
    config = configparser.ConfigParser()
    config['Paths'] = {
        'chrome_driver_path': 'drivers\\chromedriver.exe'
    }
    config['API_Keys'] = {
        'dashscope_api_key': 'YOUR_DASHSCOPE_API_KEY_HERE',
        'gemini_api_key': 'YOUR_GEMINI_API_KEY_HERE',
        'deepseek_api_key': 'YOUR_DEEPSEEK_API_KEY_HERE'
    }
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        config.write(f)
    tkinter.messagebox.showwarning(
        "配置已生成",
        f"config.ini 已在以下路径创建：\n{CONFIG_PATH}\n\n请打开它，填入你的API密钥。"
    )

def get_config():
    if not os.path.exists(CONFIG_PATH):
        create_default_config()
    
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH, encoding='utf-8')
    return config

config = get_config()

def get_driver_path():
    path = config.get('Paths', 'chrome_driver_path', fallback='drivers\\chromedriver.exe')
    if not os.path.isabs(path):
        return os.path.join(CURRENT_DIR, path)
    return path

def get_api_key(provider_name: str):
    return config.get('API_Keys', f"{provider_name.lower()}_api_key", fallback='')
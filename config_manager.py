# File: config_manager.py (Final Version)
import configparser, os, sys, tkinter.messagebox

def get_current_dir():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    else: return os.path.dirname(os.path.abspath(__file__))

CURRENT_DIR = get_current_dir()
CONFIG_PATH = os.path.join(CURRENT_DIR, 'config.ini')

def create_default_config():
    config = configparser.ConfigParser()
    config['Paths'] = {'chrome_executable_path': ''}
    config['API_Keys'] = {
        'dashscope_api_key': 'YOUR_DASHSCOPE_API_KEY_HERE',
        'gemini_api_key': 'YOUR_GEMINI_API_KEY_HERE',
        'deepseek_api_key': 'YOUR_DEEPSEEK_API_KEY_HERE',
        'zhipuai_api_key': 'YOUR_ZHIPUAI_API_KEY_HERE',
        'groq_api_key': 'YOUR_GROQ_API_KEY_HERE' # <-- The new key for Groq
    }
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f: config.write(f)
    tkinter.messagebox.showwarning("Configuration Created", f"config.ini已创建，请在其中填入你的API密钥。")

def get_config():
    if not os.path.exists(CONFIG_PATH): create_default_config()
    config = configparser.ConfigParser(); config.read(CONFIG_PATH, encoding='utf-8')
    return config

config = get_config()
def get_chrome_exe_path(): return config.get('Paths', 'chrome_executable_path', fallback='').strip()
def get_api_key(p: str): return config.get('API_Keys', f"{p.lower()}_api_key", fallback='')
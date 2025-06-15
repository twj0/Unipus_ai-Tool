# File: config_manager.py
import configparser
import os
import sys
import tkinter.messagebox

def get_current_dir():
    """Gets the directory of the script or the executable."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

# --- Global Configuration ---
CURRENT_DIR = get_current_dir()
CONFIG_PATH = os.path.join(CURRENT_DIR, 'config.ini')

# --- Functions ---
def create_default_config():
    """Creates a default config.ini file if it doesn't exist."""
    config = configparser.ConfigParser()
    config['Paths'] = {
        'chrome_driver_path': 'chromedriver.exe'
    }
    config['API_Keys'] = {
        'dashscope_api_key': 'YOUR_DASHSCOPE_API_KEY_HERE',
        'gemini_api_key': 'YOUR_GEMINI_API_KEY_HERE',
        'deepseek_api_key': 'YOUR_DEEPSEEK_API_KEY_HERE'
    }
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        config.write(f)
    tkinter.messagebox.showwarning(
        "Configuration Created",
        f"config.ini has been created at:\n{CONFIG_PATH}\n\nPlease edit it to add your ChromeDriver path and API keys."
    )

def get_config():
    """Reads and returns the configuration object."""
    if not os.path.exists(CONFIG_PATH):
        create_default_config()
    
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH, encoding='utf-8')
    return config

# --- Initial Load ---
config = get_config()

# --- Helper Getters ---
def get_driver_path():
    path = config.get('Paths', 'chrome_driver_path', fallback='chromedriver.exe')
    # If the path is not absolute, assume it's relative to the current directory
    if not os.path.isabs(path):
        return os.path.join(CURRENT_DIR, path)
    return path

def get_api_key(provider_name: str):
    """Gets the API key for a given provider (e.g., 'dashscope', 'gemini')."""
    key_name = f"{provider_name.lower()}_api_key"
    return config.get('API_Keys', key_name, fallback='')
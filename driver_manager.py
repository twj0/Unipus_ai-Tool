# File: driver_manager.py
import os, sys, platform, subprocess, zipfile, requests, logging, shutil, winreg
import config_manager

class WebDriverManager:
    def __init__(self, progress_callback=print):
        self.progress_callback = progress_callback
        self.driver_dir = os.path.join(os.getcwd(), "drivers")
        os.makedirs(self.driver_dir, exist_ok=True)

    def _get_browser_version(self, browser_name: str):
        """统一的浏览器版本检测器。"""
        manual_path = ""
        if browser_name == 'chrome':
            manual_path = config_manager.get_chrome_exe_path()
            reg_path = r"Software\Google\Chrome\BLBeacon"
            ps_command = r'powershell -command "(Get-Item (Get-ItemProperty -Path Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe).\'(default)\').VersionInfo.ProductVersion"'
        elif browser_name == 'edge':
            reg_path = r"Software\Microsoft\Edge\BLBeacon"
            ps_command = r'powershell -command "(Get-ItemProperty -Path Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe).version"'
        else:
            raise ValueError("不支持的浏览器名称")

        # 1. 手动路径优先
        if manual_path and os.path.exists(manual_path):
            try:
                cmd = f'"{manual_path}" --version'
                version = subprocess.run(cmd, capture_output=True, text=True, shell=True, check=True).stdout.strip().split()[-1]
                if version: return version
            except Exception: pass
        
        # 2. PowerShell / 注册表
        if platform.system() == "Windows":
            try: return subprocess.run(ps_command, capture_output=True, text=True, shell=True, check=True).stdout.strip()
            except Exception: pass
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
                    return winreg.QueryValueEx(key, "version")[0]
            except Exception: pass
        return None

    def _get_driver_info(self, browser_name: str, browser_version: str):
        """获取特定浏览器的驱动下载URL和驱动名称。"""
        if browser_name == 'chrome':
            api_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
            driver_platform = 'win64'
            driver_filename = 'chromedriver.exe'
        elif browser_name == 'edge':
            # Edge有自己的版本API
            api_url = f"https://msedgedriver.azureedge.net/LATEST_STABLE"
            # 对于Edge，我们通常直接用主版本号或稳定版号
            browser_version = requests.get(api_url).text.strip()
            api_url = f"https://msedgedriver.azureedge.net/{browser_version}/edgedriver_win64.zip"
            return api_url, "msedgedriver.exe"
        else:
            raise ValueError("不支持的浏览器名称")

        response = requests.get(api_url, timeout=30); response.raise_for_status()
        data = response.json()
        major_ver = browser_version.split('.')[0]

        for ver_info in reversed(data['versions']):
            if ver_info['version'].split('.')[0] == major_ver:
                for download in ver_info['downloads']['chromedriver']:
                    if download['platform'] == driver_platform:
                        return download['url'], driver_filename
        raise RuntimeError(f"无法为 {browser_name} v{browser_version} 找到匹配的驱动。")


    def check_and_get_driver(self):
        """主函数：智能尝试Chrome，失败则自动切换到Edge。"""
        # --- A计划: 尝试Chrome ---
        self.progress_callback("正在检测Chrome浏览器...")
        chrome_version = self._get_browser_version('chrome')
        if chrome_version:
            self.progress_callback(f"检测到Chrome版本: {chrome_version}")
            download_url, driver_filename = self._get_driver_info('chrome', chrome_version)
            driver_path = os.path.join(self.driver_dir, driver_filename)
            self._download_and_install(download_url, driver_path, driver_filename)
            return 'chrome', driver_path

        # --- B计划: 切换到Edge ---
        self.progress_callback("警告: 未能自动检测到Chrome。正在切换到Microsoft Edge作为备用方案...")
        edge_version = self._get_browser_version('edge')
        if edge_version:
            self.progress_callback(f"检测到Edge版本: {edge_version}")
            download_url, driver_filename = self._get_driver_info('edge', edge_version)
            driver_path = os.path.join(self.driver_dir, driver_filename)
            self._download_and_install(download_url, driver_path, driver_filename)
            return 'edge', driver_path
            
        raise RuntimeError("致命错误: 未能找到任何可用的浏览器 (Chrome或Edge)。请手动安装其中之一。")

    def _download_and_install(self, url, driver_path, executable_name):
        """统一的下载和安装流程。"""
        if os.path.exists(driver_path):
             self.progress_callback("驱动已存在，跳过下载。"); return
             
        self.progress_callback(f"正在下载 {executable_name}...")
        zip_path = os.path.join(self.driver_dir, "driver.zip")
        response = requests.get(url, stream=True, timeout=60); response.raise_for_status()
        with open(zip_path, 'wb') as f: f.write(response.content)

        self.progress_callback("正在解压...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                if member.filename.endswith(executable_name) and not member.is_dir():
                    with zip_ref.open(member) as source, open(driver_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                    break
        os.remove(zip_path)
        self.progress_callback(f"{executable_name} 已成功安装！")
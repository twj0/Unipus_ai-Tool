# File: driver_manager.py
import os
import sys
import platform
import subprocess
import zipfile
import requests
import logging

class ChromeDriverManager:
    """
    一个全自动的Chrome WebDriver管理器。
    - 自动检测本地Chrome版本。
    - 自动从官方源下载匹配的ChromeDriver。
    - 自动管理驱动文件。
    实现了真正的开箱即用。
    """
    def __init__(self, progress_callback=print):
        self.progress_callback = progress_callback
        self.driver_dir = os.path.join(os.getcwd(), "drivers")
        os.makedirs(self.driver_dir, exist_ok=True)
        self.driver_path = os.path.join(self.driver_dir, "chromedriver.exe" if platform.system() == "Windows" else "chromedriver")

    def get_chrome_version(self):
        """获取本地Chrome浏览器的版本号。"""
        system = platform.system()
        if system == "Windows":
            try:
                # 优先使用 PowerShell，更稳定
                cmd = r'powershell -command "(Get-Item (Get-ItemProperty -Path Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe).\'(default)\').VersionInfo.ProductVersion"'
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True, check=True)
                version = result.stdout.strip()
                if version:
                    return version
            except Exception as e:
                logging.warning(f"通过PowerShell获取版本失败: {e}，尝试其他方法...")
                # 备用方法：直接访问注册表
                try:
                    import winreg
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon") as key:
                        version, _ = winreg.QueryValueEx(key, "version")
                        return version
                except Exception:
                    logging.warning("通过注册表获取版本也失败了。")
        elif system == "Linux":
            try:
                result = subprocess.run(["google-chrome", "--version"], capture_output=True, text=True, check=True)
                return result.stdout.strip().split()[-1]
            except Exception as e:
                logging.error(f"在Linux上获取Chrome版本失败: {e}")
        elif system == "Darwin": # macOS
            try:
                result = subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"], capture_output=True, text=True, check=True)
                return result.stdout.strip().split()[-1]
            except Exception as e:
                logging.error(f"在macOS上获取Chrome版本失败: {e}")

        raise RuntimeError("无法自动检测到任何已安装的Chrome浏览器版本。")

    def get_driver_version(self):
        """获取本地已存在的ChromeDriver版本。"""
        if not os.path.exists(self.driver_path):
            return None
        try:
            result = subprocess.run([self.driver_path, "--version"], capture_output=True, text=True, check=True)
            return result.stdout.strip().split(' ')[1]
        except Exception:
            return None

    def _get_driver_download_url(self, browser_version):
        """从官方JSON端点获取正确的ChromeDriver下载URL。"""
        self.progress_callback("正在从官方服务器查询匹配的驱动版本...")
        # 新的官方JSON API
        api_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()

        # 我们需要找到与浏览器主版本号匹配的、最新的一个驱动版本
        major_browser_ver = browser_version.split('.')[0]
        
        best_match = None
        for version_info in reversed(data['versions']): # 从新到旧查找
            driver_ver = version_info['version']
            if driver_ver.split('.')[0] == major_browser_ver:
                 for download in version_info['downloads']['chromedriver']:
                     # 确定平台
                     if platform.system() == "Windows" and download['platform'] == 'win64':
                         return download['url']
                     elif platform.system() == "Linux" and download['platform'] == 'linux64':
                         return download['url']
                     elif platform.system() == "Darwin" and download['platform'] in ['mac-x64', 'mac-arm64']:
                         return download['url']
        
        raise RuntimeError(f"无法为您的Chrome版本 {browser_version} 找到匹配的ChromeDriver。")


    def download_and_unzip_driver(self, url):
        """下载并解压ChromeDriver。"""
        self.progress_callback(f"正在下载驱动...")
        zip_path = os.path.join(self.driver_dir, "chromedriver.zip")
        
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        self.progress_callback("下载完成，正在解压...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 在zip包中寻找正确的chromedriver可执行文件
            for member in zip_ref.namelist():
                if 'chromedriver.exe' in member or member.endswith('chromedriver'):
                    zip_ref.extract(member, self.driver_dir)
                    # 将解压出的文件移动到最终位置
                    extracted_path = os.path.join(self.driver_dir, member)
                    os.rename(extracted_path, self.driver_path)
                    # 清理可能产生的空文件夹
                    if os.path.isdir(os.path.dirname(extracted_path)) and not os.listdir(os.path.dirname(extracted_path)):
                         os.rmdir(os.path.dirname(extracted_path))
                    break

        os.remove(zip_path)
        if platform.system() != "Windows":
            os.chmod(self.driver_path, 0o755) # 赋予执行权限
        self.progress_callback("驱动已成功安装！")


    def check_and_get_driver(self):
        """
        主函数，检查并返回可用的ChromeDriver路径。
        如果需要，会自动下载和更新。
        """
        self.progress_callback("正在检查ChromeDriver...")
        browser_version = self.get_chrome_version()
        driver_version = self.get_driver_version()

        self.progress_callback(f"检测到Chrome浏览器版本: {browser_version}")
        if driver_version:
            self.progress_callback(f"本地驱动版本: {driver_version}")

        if driver_version and driver_version.split('.')[0] == browser_version.split('.')[0]:
            self.progress_callback("驱动版本与浏览器主版本匹配，无需更新。")
            return self.driver_path
        
        self.progress_callback("驱动版本不匹配或不存在，开始自动更新...")
        download_url = self._get_driver_download_url(browser_version)
        self.download_and_unzip_driver(download_url)
        
        return self.driver_path
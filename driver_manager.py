# File: driver_manager.py
import os, sys, platform, subprocess, zipfile, requests, logging, shutil

class ChromeDriverManager:
    def __init__(self, progress_callback=print):
        self.progress_callback = progress_callback
        self.driver_dir = os.path.join(os.getcwd(), "drivers")
        os.makedirs(self.driver_dir, exist_ok=True)
        self.driver_path = os.path.join(self.driver_dir, "chromedriver.exe" if platform.system() == "Windows" else "chromedriver")

    def get_chrome_version(self):
        system = platform.system()
        try:
            if system == "Windows":
                cmd = r'powershell -command "(Get-Item (Get-ItemProperty -Path Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe).\'(default)\').VersionInfo.ProductVersion"'
                return subprocess.run(cmd, capture_output=True, text=True, shell=True, check=True).stdout.strip()
            elif system == "Linux":
                return subprocess.run(["google-chrome", "--version"], capture_output=True, text=True, check=True).stdout.strip().split()[-1]
            elif system == "Darwin":
                return subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"], capture_output=True, text=True, check=True).stdout.strip().split()[-1]
        except Exception:
            raise RuntimeError("无法自动检测到任何已安装的Chrome浏览器版本。")

    def get_driver_version(self):
        if not os.path.exists(self.driver_path): return None
        try: return subprocess.run([self.driver_path, "--version"], capture_output=True, text=True, check=True).stdout.strip().split(' ')[1]
        except Exception: return None

    def _get_driver_download_url(self, browser_version):
        self.progress_callback("正在从官方服务器查询匹配的驱动版本...")
        api_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
        response = requests.get(api_url, timeout=30); response.raise_for_status()
        data = response.json(); major_browser_ver = browser_version.split('.')[0]
        for version_info in reversed(data['versions']):
            if version_info['version'].split('.')[0] == major_browser_ver:
                for download in version_info['downloads']['chromedriver']:
                    if platform.system() == "Windows" and download['platform'] == 'win64': return download['url']
                    elif platform.system() == "Linux" and download['platform'] == 'linux64': return download['url']
                    elif platform.system() == "Darwin" and download['platform'] in ['mac-x64', 'mac-arm64']: return download['url']
        raise RuntimeError(f"无法为您的Chrome版本 {browser_version} 找到匹配的ChromeDriver。")

    def download_and_unzip_driver(self, url):
        self.progress_callback("正在下载驱动..."); zip_path = os.path.join(self.driver_dir, "chromedriver.zip")
        response = requests.get(url, stream=True, timeout=60); response.raise_for_status()
        with open(zip_path, 'wb') as f: f.write(response.content)
        self.progress_callback("下载完成，正在解压...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            executable_name = "chromedriver.exe" if platform.system() == "Windows" else "chromedriver"
            driver_file_info = next((f for f in zip_ref.infolist() if f.filename.endswith(executable_name) and not f.is_dir()), None)
            if not driver_file_info: raise RuntimeError(f"在下载的zip文件中未找到'{executable_name}'")
            with zip_ref.open(driver_file_info) as source, open(self.driver_path, "wb") as target:
                shutil.copyfileobj(source, target)
        os.remove(zip_path)
        if platform.system() != "Windows": os.chmod(self.driver_path, 0o755)
        self.progress_callback("驱动已成功安装！")

    def check_and_get_driver(self):
        if os.path.isdir(os.path.join(self.driver_dir, "chromedriver-win64")):
            shutil.rmtree(os.path.join(self.driver_dir, "chromedriver-win64"))
        self.progress_callback("正在检查ChromeDriver...")
        browser_version = self.get_chrome_version(); driver_version = self.get_driver_version()
        self.progress_callback(f"检测到Chrome版本: {browser_version}")
        if driver_version: self.progress_callback(f"本地驱动版本: {driver_version}")
        if driver_version and driver_version.split('.')[0] == browser_version.split('.')[0]:
            self.progress_callback("驱动版本匹配，无需更新。"); return self.driver_path
        self.progress_callback("驱动版本不匹配或不存在，开始自动更新...")
        download_url = self._get_driver_download_url(browser_version)
        self.download_and_unzip_driver(download_url); return self.driver_path
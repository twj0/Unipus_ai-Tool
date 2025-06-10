# Uai Tool - 英语填空题自动答题工具

---

## 简介

本工具为基于 Python 的自动化答题程序，可自动完成 UniCloud 平台 (https://ucloud.unipus.cn) 的英语填空题作业。通过 Selenium 浏览器自动化技术与通义千问 AI 模型结合，实现题目解析、答案生成及网页自动填写全流程自动化。

## 功能特性

- 浏览器自动化控制
- 网页题目内容智能解析
- 支持单空题/多空题两种题型识别
- 通义千问 AI 模型集成（Qwen 系列）
- 答案自动填充与日志跟踪

## 技术依赖

- Python 3.8+
- Selenium 4.0+
- Requests 2.28+
- Tkinter 8.6
- 配置管理：configparser

---

## 使用说明

### 1. 环境准备
```bash
pip install -r requirements.txt
```

### 2. 驱动配置
1. **下载驱动**  
   下载与 Chrome 浏览器版本匹配的 [ChromeDriver](https://sites.google.com/chromium.org/driver/)  

2. **文件存放**  
   将 `chromedriver.exe` 及其依赖文件（如 `chromedriver.exe`、`LICENSE.chromedriver` 等）直接放置在项目根目录下

3. **配置文件设置**  
   在根目录的 `config.ini` 中配置驱动路径：
   ```ini
   [Settings]
   chrome_driver_path = chromedriver.exe  # 根目录下的驱动文件
   dashscope_api_key = YOUR_API_KEY_HERE  # AI服务API密钥
   ```

### 3. 程序启动
```bash
python main.py
```

## 配置文件说明

### config.ini

```ini
[Settings]
chrome_driver_path = chromedriver.exe  # 根目录下的驱动文件
dashscope_api_key = YOUR_API_KEY_HERE  # AI服务API密钥
```

## 程序操作流程
1. **启动程序**  
   - 点击"启动程序"按钮  
   - 程序会自动连接调试模式浏览器（需提前启动带调试端口的 Chrome）  
   - 自动跳转至目标学习平台（默认：https://ucloud.unipus.cn）

2. **打开填空题界面**  
   - 在浏览器中手动导航至具体的填空题作业页面  
   - 确保题目内容完整加载（出现题目文本和输入框）  
   - *注意：程序不会自动识别题目页面，需用户主动打开目标界面*

3. **自动答题**  
   - 点击"自动答题"按钮  
   - 程序将执行以下操作：  
     a. 提取当前页面题目内容（指令、问题、选项）  
     b. 调用 AI 模型生成答案  
     c. 将答案自动填充到网页输入框  
   - *首次使用建议观察日志输出，确认题目解析是否正确*

4. **重复操作**  
   - 若需完成其他题目页面：  
     a. 在浏览器中打开新的填空题界面  
     b. 重复点击"自动答题"按钮  
   - *每次答题前需确保浏览器停留在目标题目页面*

   **清除填写内容**  
   
   - 点击"清除所有填空"按钮  
   - 可快速清空当前页面所有输入框内容  
   - *仅清除通过本程序填写的内容，不影响手动输入*

## 注意事项
1. 浏览器驱动需与 Chrome 版本严格匹配
2. API 密钥需配置有效值方可正常使用
3. 网页结构变更可能导致定位失败
4. 建议在调试模式浏览器(9222端口)下运行
5. 程序不会自动提交答案，需手动点击网页提交按钮

## 开源协议
本项目采用 MIT License，详细许可条款请见 LICENSE 文件
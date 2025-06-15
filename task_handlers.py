# File: task_handlers.py
import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# 导入我们的AI和浏览器交互模块
import ai_handler
import browser_handler
import config_manager

# 注意：为了进行类型提示而不产生循环导入，我们使用字符串形式
# from gui import AutoAnswerGUI # 这会产生循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from gui import AutoAnswerGUI


def handle_video_page(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理视频播放页面：实现倍速播放并等待其结束。"""
    gui.log("任务：视频播放处理器已启动。")
    try:
        # 1. 等待视频元素加载完成
        wait = WebDriverWait(driver, 15)
        video_element = wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "video"))
        )
        gui.log("成功定位到视频元素。")

        # 2. 注入JavaScript来控制播放
        # 设置16倍速，静音（避免爆音），然后点击播放
        driver.execute_script(
            "arguments[0].playbackRate = 16; arguments[0].muted = true; arguments[0].play();",
            video_element
        )
        gui.log("成功注入脚本：视频已设置为16倍速并开始播放。")

        # 3. 监控视频播放进度直到结束
        while not gui.stop_flag.is_set():
            time.sleep(2) # 每2秒检查一次状态
            # 通过JS获取视频的当前时间和总时长
            progress = driver.execute_script(
                "return { currentTime: arguments[0].currentTime, duration: arguments[0].duration, ended: arguments[0].ended };",
                video_element
            )
            
            # 如果视频数据有效
            if progress and progress['duration']:
                current_time = progress['currentTime']
                duration = progress['duration']
                is_ended = progress['ended']

                gui.log(f"视频进度: {int(current_time)} / {int(duration)} 秒")

                # 如果视频播放完毕，则跳出循环
                if is_ended or current_time >= duration - 1:
                    gui.log("视频播放完毕。")
                    break
            else:
                gui.log("等待视频元数据加载...")

    except TimeoutException:
        gui.log("错误：在页面上未找到视频元素。")
    except Exception as e:
        gui.log(f"处理视频时发生未知错误: {e}")


def handle_quiz_fill_in_blank(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理选词填空题：调用AI并自动填写答案。"""
    gui.log("任务：AI填空题处理器已启动。")
    try:
        # 这一部分逻辑是从旧版本中迁移并优化而来的
        gui.log("正在从页面提取题目信息...")
        page_data = browser_handler.extract_questions_from_page(driver)
        if not page_data.get("questions"):
            gui.log("警告：未能提取到题目，可能页面结构已改变。")
            return

        # 在AI调试窗口显示题目
        gui.ai_debug_text.delete(1.0, tk.END)
        gui.ai_debug_text.insert(tk.END, "--- 提取到的问题 ---\n" + "\n".join(page_data['questions']))
        
        blank_counts = browser_handler.get_blank_counts(driver, len(page_data['questions']))
        
        prompt = ai_handler.build_prompt(**page_data, blank_counts=blank_counts)
        gui.ai_debug_text.insert(tk.END, "\n\n--- 发送给AI的Prompt ---\n" + prompt)
        
        model_name = gui.selected_model.get()
        provider_key_name = model_name.split(" ")[0].lower()
        api_key = config_manager.get_api_key(provider_key_name)
        
        if not api_key or "YOUR_" in api_key:
            error_msg = f"错误：{model_name}的API Key未在config.ini中设置。"
            gui.log(error_msg)
            messagebox.showerror("API Key Error", error_msg)
            return

        gui.log(f"正在调用 {model_name} 模型进行推理...")
        provider = ai_handler.get_ai_provider(model_name, api_key)
        ai_response = provider.call_ai(prompt)
        gui.ai_debug_text.insert(tk.END, "\n\n--- AI返回的原始回答 ---\n" + ai_response)
        
        answers = ai_handler.parse_ai_response(ai_response)
        if not answers:
            gui.log("警告：未能从AI的回答中解析出有效答案。")
            return
            
        gui.log(f"成功解析出答案，准备填写: {answers}")
        browser_handler.fill_answers_to_webpage(driver, answers)
        gui.log("答案已成功填写到网页！")

    except Exception as e:
        gui.log(f"处理填空题时发生未知错误: {e}")


def handle_reading_page(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理阅读页面：滚动到底部并点击下一页。"""
    gui.log("任务：阅读页面处理器已启动。")
    try:
        gui.log("正在模拟滚动页面...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        gui.log("寻找“下一页”或类似按钮...")
        # 优先寻找包含特定文字的按钮
        next_button_xpath = "//button[contains(span, '下一页') or contains(text(), 'Next') or contains(span, 'I have read')]"
        wait = WebDriverWait(driver, 10)
        next_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, next_button_xpath))
        )
        next_button.click()
        gui.log("已点击“下一页”按钮。")
        
    except TimeoutException:
        gui.log("警告：未找到“下一页”按钮，可能已经是最后一页。")
    except Exception as e:
        gui.log(f"处理阅读页面时发生错误: {e}")


def handle_unknown_page(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理未知类型的页面：记录信息并等待。"""
    gui.log("任务：未知页面处理器已启动。")
    gui.log("警告：当前页面类型无法自动识别，或暂不支持自动化处理（如选择题、拖拽题等）。")
    gui.log("将在5秒后继续尝试下一个任务。")
    
    # 检查是否有提交按钮，以防万一
    try:
        submit_button = driver.find_element(By.XPATH, "//button[contains(span, '提交')]")
        if submit_button.is_displayed():
            gui.log("检测到“提交”按钮，建议手动操作此题目。")
    except:
        pass # 找不到提交按钮很正常
        
    time.sleep(5)
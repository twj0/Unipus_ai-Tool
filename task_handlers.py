# File: task_handlers.py (The Final Assembly)
import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import tkinter as tk
from tkinter import messagebox
import ai_handler
import browser_handler
import config_manager
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from gui import AutoAnswerGUI

def call_ai(gui: 'AutoAnswerGUI', prompt: str):
    """一个统一的AI调用辅助函数，包含完整的UI更新和错误处理。"""
    model_name = gui.selected_model.get()
    api_key = config_manager.get_api_key(model_name.split(" ")[0].lower())
    if not api_key or "YOUR_" in api_key:
        messagebox.showerror("API Key Error", f"错误：{model_name}的API Key未在config.ini中设置。")
        return None
        
    # 在GUI中显示Prompt
    gui.ai_debug_text.delete(1.0, tk.END)
    gui.ai_debug_text.insert(tk.END, f"--- 发送给AI的Prompt ---\n{prompt}")
    
    # 调用AI并获取回复
    provider = ai_handler.get_ai_provider(model_name, api_key)
    response = provider.call_ai(prompt).strip()
    
    # 在GUI中显示回复
    gui.ai_debug_text.insert(tk.END, f"\n\n--- AI返回的原始回答 ---\n{response}")
    return response

def handle_skip_page(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """通用跳过处理器，用于处理阅读、跟读、项目作业等。"""
    gui.log("任务：此页面类型被设定为自动跳过。")
    time.sleep(2) # 短暂等待，模拟操作

def handle_video_page(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理视频播放页面：尽力而为，如果找不到就快速跳过。"""
    gui.log("任务：视频播放处理器已启动。")
    iframe_found = False
    try:
        # 使用较短的等待时间，快速判断是否存在iframe
        wait = WebDriverWait(driver, 5)
        iframe_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        driver.switch_to.frame(iframe_element)
        iframe_found = True
        gui.log("成功切换到iframe中。")

        wait_inside_iframe = WebDriverWait(driver, 5)
        video_element = wait_inside_iframe.until(EC.presence_of_element_located((By.TAG_NAME, "video")))
        gui.log("在iframe内成功定位到视频元素。")

        # 注入脚本并播放
        driver.execute_script("arguments[0].playbackRate = 16; arguments[0].muted = true; arguments[0].play();", video_element)
        
        # 循环检查视频是否结束，设置一个合理的总超时
        start_time = time.time()
        while time.time() - start_time < 180: # 最多等待3分钟
            if gui.stop_flag.is_set(): break
            time.sleep(2)
            try:
                progress = driver.execute_script("return { currentTime: arguments[0].currentTime, duration: arguments[0].duration, ended: arguments[0].ended };", video_element)
                if progress and progress['ended']:
                    gui.log("视频播放完毕。"); break
                # 如果视频因未知原因卡住，当前时间等于总时间也算结束
                if progress and progress['duration'] and abs(progress['currentTime'] - progress['duration']) < 1:
                    gui.log("视频播放到达末尾。"); break
            except Exception:
                gui.log("视频元素状态已更新或丢失，判定为播放结束。")
                break
        
    except TimeoutException:
        gui.log("警告：在指定时间内未找到视频相关元素，将跳过此视频任务。")
    except Exception as e:
        gui.log(f"处理视频时发生未知错误: {e}")
    finally:
        if iframe_found:
            driver.switch_to.default_content()
            gui.log("已从iframe切回主页面。")

def handle_vocabulary_flashcards(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理单词卡片学习页面：快速翻完所有卡片。"""
    gui.log("任务：单词卡片处理器已启动。")
    try:
        wait = WebDriverWait(driver, 10)
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='下一条']/parent::button")))
        progress_text = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.page-number, span.pager-num"))).text
        current, total = [int(x.strip()) for x in progress_text.split('/')]
        gui.log(f"检测到总共有 {total} 个单词卡片。")

        for i in range(current, total):
            if gui.stop_flag.is_set(): gui.log("操作被用户停止。"); return
            next_button.click()
            gui.log(f"正在翻动卡片: {i + 1} / {total}")
            time.sleep(0.5)
        gui.log("所有单词卡片已学习完毕。")
    except Exception as e:
        gui.log(f"处理单词卡片时出错: {e}")

def handle_quiz_true_false(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """使用AI处理判断题（True/False/Not Given）。"""
    gui.log("任务：AI判断题处理器已启动。")
    try:
        questions_container = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.question-list, div.ques-list")))
        questions = questions_container.find_elements(By.CSS_SELECTOR, "div.question-item, div.ques-item")
        text_for_ai = "".join([f"Question {i+1}: {q.text.splitlines()[0]}\n" for i, q in enumerate(questions)])
        prompt = f"You are an English reading comprehension expert. For the following statements, decide if they are True, False, or Not Given based on the article. Respond ONLY with the letter (A for True, B for False, C for Not Given) for each question, each on a new line.\n\n{text_for_ai}"
        ai_response = call_ai(gui, prompt)
        if not ai_response: return
        answers = ai_response.split('\n')
        for i, ans in enumerate(answers):
            if i < len(questions):
                option_letter = ans.strip().upper()
                questions[i].find_element(By.XPATH, f".//span[contains(text(), '{option_letter}')]").click()
                time.sleep(0.5)
        driver.find_element(By.XPATH, "//button[contains(span, '提交')]").click()
        gui.log("判断题已提交。")
    except Exception as e: gui.log(f"处理判断题时出错: {e}")

def handle_quiz_fill_in_blank(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理选词填空题。"""
    gui.log("任务：AI选词填空处理器已启动。")
    try:
        page_data = browser_handler.extract_questions_from_page(driver)
        if not page_data.get("questions"): gui.log("警告：未能提取到题目。"); return
        blank_counts = browser_handler.get_blank_counts(driver, len(page_data['questions']))
        prompt = ai_handler.build_prompt(**page_data, blank_counts=blank_counts)
        ai_response = call_ai(gui, prompt)
        if not ai_response: return
        answers = ai_handler.parse_ai_response(ai_response)
        if not answers: gui.log("警告：未能解析出有效答案。"); return
        gui.log(f"成功解析出答案，准备填写: {answers}")
        browser_handler.fill_answers_to_webpage(driver, answers)
        gui.log("答案已成功填写到网页！")
        # 选词填空通常没有提交按钮，是即时判断的
    except Exception as e: gui.log(f"处理选词填空时出错: {e}")

def handle_quiz_vocabulary_choice(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理词义辨析（多选题）。"""
    gui.log("任务：AI词义辨析处理器已启动。")
    try:
        questions = driver.find_elements(By.CSS_SELECTOR, "div.question-item, div.ques-item")
        text_for_ai = "".join([f"Question {i+1}: {q.text}\n" for i, q in enumerate(questions)])
        prompt = f"You are an English vocabulary expert. For the following questions, choose the correct option (A or B) that best explains the italicized word. Respond ONLY with the letter (A or B) for each question, each on a new line.\n\n{text_for_ai}"
        ai_response = call_ai(gui, prompt)
        if not ai_response: return
        answers = ai_response.split('\n')
        for i, ans in enumerate(answers):
            if i < len(questions):
                option_letter = ans.strip().upper()
                questions[i].find_element(By.XPATH, f".//span[contains(text(), '{option_letter}')]").click()
                time.sleep(0.5)
        driver.find_element(By.XPATH, "//button[contains(span, '提交')]").click()
        gui.log("词义辨析题已提交。")
    except Exception as e: gui.log(f"处理词义辨析时出错: {e}")

def handle_quiz_rewrite_sentence(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理句子改写题。"""
    gui.log("任务：AI句子改写处理器已启动。")
    try:
        questions = driver.find_elements(By.CSS_SELECTOR, "div.question-item, div.ques-item")
        text_for_ai = "".join([f"Original: {q.find_element(By.CSS_SELECTOR, 'div.stem').text}\n" for q in questions])
        prompt = f"You are an expert in English grammar. Rewrite the following sentences to correct the errors, focusing on parallel structure. Provide ONLY the corrected sentence for each item, each on a new line.\n\n{text_for_ai}"
        ai_response = call_ai(gui, prompt)
        if not ai_response: return
        answers = ai_response.split('\n')
        for i, ans in enumerate(answers):
            if i < len(questions):
                textarea = questions[i].find_element(By.TAG_NAME, "textarea")
                textarea.send_keys(ans.strip())
        driver.find_element(By.XPATH, "//button[contains(span, '提交')]").click()
        gui.log("句子改写题已提交。")
    except Exception as e: gui.log(f"处理句子改写时出错: {e}")

def handle_quiz_translate(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理英译汉。"""
    gui.log("任务：AI翻译处理器已启动。")
    try:
        original_text = driver.find_element(By.CSS_SELECTOR, "div.ql-editor, div.translate-area").text
        prompt = f"Please translate the following English paragraph into Chinese. Provide ONLY the Chinese translation.\n\n{original_text}"
        ai_response = call_ai(gui, prompt)
        if not ai_response: return
        editor = driver.find_element(By.CSS_SELECTOR, "div.ql-editor")
        driver.execute_script("arguments[0].innerHTML = arguments[1];", editor, ai_response.replace('\n', '<br>'))
        driver.find_element(By.XPATH, "//button[contains(span, '提交')]").click()
        gui.log("翻译题已提交。")
    except Exception as e: gui.log(f"处理翻译题时出错: {e}")

def handle_unknown_page(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理未知类型的页面。"""
    gui.log("警告：当前页面类型无法自动识别，将等待5秒后尝试进入下一个主任务。")
    time.sleep(5)
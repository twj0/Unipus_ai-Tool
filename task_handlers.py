# File: task_handlers.py
import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import tkinter as tk
from tkinter import messagebox
import ai_handler
import config_manager
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from gui import AutoAnswerGUI

def call_ai(gui: 'AutoAnswerGUI', prompt: str):
    """一个统一的AI调用辅助函数。"""
    model_name = gui.selected_model.get()
    api_key = config_manager.get_api_key(model_name.split(" ")[0].lower())
    if not api_key or "YOUR_" in api_key:
        messagebox.showerror("API Key Error", f"错误：{model_name}的API Key未在config.ini中设置。")
        return None
    
    gui.ai_debug_text.delete(1.0, tk.END)
    gui.ai_debug_text.insert(tk.END, f"--- 发送给AI的Prompt ---\n{prompt}")
    
    provider = ai_handler.get_ai_provider(model_name, api_key)
    response = provider.call_ai(prompt).strip()
    
    gui.ai_debug_text.insert(tk.END, f"\n\n--- AI返回的原始回答 ---\n{response}")
    return response

def handle_skip_page(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """通用跳过处理器。"""
    gui.log("任务：此类型被设定为自动跳过。")
    time.sleep(2)

def handle_reading_page(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理纯阅读页面：直接跳过。"""
    gui.log("任务：纯阅读页面，自动跳过。")
    time.sleep(2)

def handle_unknown_page(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理未知类型的页面：记录信息并等待。"""
    gui.log("任务：未知页面类型，自动跳过。")
    time.sleep(2)

def handle_video_page(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理视频播放页面：能够进入iframe，实现倍速播放并等待其结束。"""
    gui.log("任务：视频播放处理器已启动。")
    iframe_found = False
    try:
        wait = WebDriverWait(driver, 10)
        iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        driver.switch_to.frame(iframe)
        iframe_found = True
        gui.log("成功切换到iframe中。")
        
        wait_in_iframe = WebDriverWait(driver, 15)
        video = wait_in_iframe.until(EC.presence_of_element_located((By.TAG_NAME, "video")))
        gui.log("在iframe内成功定位到视频。")
        
        driver.execute_script("arguments[0].playbackRate=16; arguments[0].muted=true; arguments[0].play();", video)
        gui.log("视频已16倍速静音播放。")
        
        while not gui.stop_flag.is_set():
            time.sleep(2)
            progress = driver.execute_script("return{c:arguments[0].currentTime,d:arguments[0].duration,e:arguments[0].ended};", video)
            if progress and progress.get('d') and progress['d'] > 0:
                if progress['e'] or abs(progress['c'] - progress['d']) < 1:
                    gui.log("视频播放完毕。")
                    break
                gui.log(f"视频进度: {int(progress['c'])}/{int(progress['d'])}秒")
            else:
                gui.log("等待视频元数据加载...")
    except TimeoutException:
        gui.log("警告：在页面上或iframe内未找到视频相关元素。此任务可能无需播放或已完成。")
    except Exception as e:
        gui.log(f"处理视频时出错: {e}")
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
        total_cards = int(progress_text.split('/')[-1].strip())
        gui.log(f"检测到总共有 {total_cards} 个单词卡片。")
        for i in range(1, total_cards):
            if gui.stop_flag.is_set(): gui.log("操作被用户停止。"); return
            next_button.click()
            gui.log(f"正在翻动卡片: {i + 1} / {total_cards}")
            time.sleep(0.5)
        gui.log("所有单词卡片已学习完毕。")
    except Exception as e:
        gui.log(f"处理单词卡片时出错: {e}")

def handle_quiz_true_false(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """使用AI处理判断题（True/False/Not Given）。"""
    gui.log("任务：AI判断题处理器已启动。")
    try:
        questions = driver.find_elements(By.CSS_SELECTOR, "div.question-item, div.ques-item")
        text_for_ai = "".join([f"{i+1}. {q.find_element(By.CSS_SELECTOR, 'div.question-title, div.ques-title').text}\n" for i, q in enumerate(questions)])
        prompt = f"You are an English reading comprehension expert. Based on the preceding article, determine whether the following statements are True, False or Not Given. Respond ONLY with 'T', 'F', or 'N' for Not Given for each statement, each on a new line.\n\n{text_for_ai}"
        ai_response = call_ai(gui, prompt)
        if not ai_response: return
        answers = ai_response.split('\n')
        for i, ans in enumerate(answers):
            if i < len(questions):
                ans_upper = ans.strip().upper()
                option_letter = 'C' if 'N' in ans_upper else ('A' if 'T' in ans_upper else 'B')
                questions[i].find_element(By.XPATH, f".//span[contains(text(), '{option_letter}')]").click()
                time.sleep(0.5)
        driver.find_element(By.XPATH, "//button[contains(span, '提交')] | //button[text()='Submit']").click()
        gui.log("判断题已提交。")
    except Exception as e:
        gui.log(f"处理判断题时出错: {e}")

def handle_quiz_fill_in_blank(driver: WebDriver, gui: 'AutoAnswerGUI'):
    """处理选词填空题。"""
    gui.log("任务：AI选词填空处理器已启动。")
    # This is a placeholder for the complex logic required
    gui.log("选词填空题逻辑暂未完全实现，将跳过。")
    time.sleep(2)

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
        gui.log("词义辨辨析题已提交。")
    except Exception as e:
        gui.log(f"处理词义辨析时出错: {e}")

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
    except Exception as e:
        gui.log(f"处理句子改写时出错: {e}")

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
    except Exception as e:
        gui.log(f"处理翻译题时出错: {e}")
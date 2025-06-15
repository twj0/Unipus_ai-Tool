# File: browser_handler.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
import time

def connect_or_start_chrome(driver_path: str):
    """Connects to a debugging Chrome instance or starts a new one."""
    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Successfully connected to existing Chrome browser.")
        return driver
    except WebDriverException:
        print("No existing browser found. Starting a new Chrome instance...")
        new_options = Options()
        new_options.add_argument("--remote-debugging-port=9222")
        
        # new_options.add_argument("--user-data-dir=./chrome-profile") # Persists login sessions
        
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=new_options)
        print("New Chrome instance started.")
        return driver

def check_and_navigate(driver, target_url="https://ucloud.unipus.cn/"):
    """Checks if the driver is on the target website and navigates if not."""
    valid_prefixes = ["https://uai.unipus.cn", "https://ucloud.unipus.cn", "https://ucontent.unipus.cn"]
    current_url = driver.current_url
    
    is_valid = any(current_url.startswith(prefix) for prefix in valid_prefixes)
    
    if is_valid:
        print(f"Already on a valid page: {current_url}")
        return True
    else:
        print(f"Current page is not the target website. Navigating to {target_url}")
        driver.get(target_url)
        time.sleep(3) # Wait for potential redirects
        print(f"Navigated to: {driver.current_url}")
        return False

def extract_questions_from_page(driver):
    """Extracts instruction, questions, and options from the webpage."""
    data = {"instruction": "", "questions": [], "options": []}
    wait = WebDriverWait(driver, 10)
    
    try:
        # Note: These CSS selectors are guesses and may need to be adjusted
        instruction_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.instruction p, div.direction-text p')))
        data["instruction"] = instruction_element.text.strip()
    except TimeoutException:
        print("Could not find instruction element.")

    try:
        question_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.questions-wrapper, div.ques-wrapper')))
        question_elements = question_container.find_elements(By.TAG_NAME, 'p')
        data["questions"] = [q.text.strip() for q in question_elements if q.text.strip()]
    except TimeoutException:
        print("Could not find question elements.")

    try:
        option_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.word-bank div.option, div.word-bank-item')))
        data["options"] = [opt.text.strip() for opt in option_elements if opt.text.strip()]
    except TimeoutException:
        print("Could not find option elements.")
        
    return data

def get_blank_counts(driver, question_count: int) -> list:
    """Gets the number of input blanks for each question."""
    counts = []
    question_paragraphs = driver.find_elements(By.XPATH, '//div[contains(@class, "questions-wrapper")]//p | //div[contains(@class, "ques-wrapper")]//p')

    if len(question_paragraphs) < question_count:
        return [1] * question_count

    for i in range(question_count):
        p_element = question_paragraphs[i]
        inputs = p_element.find_elements(By.TAG_NAME, 'input')
        counts.append(len(inputs))
    return counts
    
def fill_answers_to_webpage(driver, answers: list):
    """Fills the extracted answers into the webpage's input fields."""
    if not answers:
        print("No answers to fill.")
        return
        
    question_paragraphs = driver.find_elements(By.XPATH, '//div[contains(@class, "questions-wrapper")]//p | //div[contains(@class, "ques-wrapper")]//p')

    for i, answer_group in enumerate(answers):
        if i >= len(question_paragraphs):
            break
            
        p_element = question_paragraphs[i]
        inputs = p_element.find_elements(By.TAG_NAME, 'input')
        
        for j, input_box in enumerate(inputs):
            if j < len(answer_group):
                try:
                    input_box.clear()
                    input_box.send_keys(answer_group[j])
                except Exception as e:
                    print(f"Error filling input for Q{i+1}, Blank {j+1}: {e}")

def clear_all_inputs(driver):
    """Clears all input fields in the questions area."""
    all_inputs = driver.find_elements(By.XPATH, '//div[contains(@class, "questions-wrapper")]//input | //div[contains(@class, "ques-wrapper")]//input')
    for input_box in all_inputs:
        try:
            input_box.clear()
        except Exception as e:
            print(f"Could not clear an input box: {e}")
    print(f"Cleared {len(all_inputs)} input fields.")
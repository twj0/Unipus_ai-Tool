# File: page_analyzer.py
import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

class PageAnalyzer:
    def __init__(self, driver: WebDriver): self.driver = driver
    def _element_exists(self, by, value):
        try: self.driver.find_element(by, value); return True
        except NoSuchElementException: return False

    def get_page_type_in_tab(self) -> str:
        time.sleep(1)
        if self._element_exists(By.TAG_NAME, "video"): return "VIDEO"
        if self._element_exists(By.CSS_SELECTOR, "div.word-card, div.word-detail-container"): return "VOCABULARY_FLASHCARDS"
        if self._element_exists(By.XPATH, "//*[contains(text(), 'True') and contains(text(), 'False')]"): return "QUIZ_TRUE_FALSE_NG"
        if self._element_exists(By.CSS_SELECTOR, "div.word-bank, div.word-bank-item"): return "QUIZ_FILL_IN_BLANK"
        if self._element_exists(By.XPATH, "//*[contains(text(), 'Choose the appropriate meanings')]"): return "QUIZ_VOCABULARY_CHOICE"
        if self._element_exists(By.XPATH, "//*[contains(text(), 'Rewrite the sentences')]"): return "QUIZ_REWRITE_SENTENCE"
        if self._element_exists(By.XPATH, "//*[contains(text(), 'Translate the following paragraph')]"): return "QUIZ_TRANSLATE"
        if self._element_exists(By.XPATH, "//*[contains(text(), 'Read aloud')]"): return "REPEATING_AFTER_ME"
        if self._element_exists(By.XPATH, "//*[contains(text(), 'Reading in detail')]"): return "READING"
        if self._element_exists(By.XPATH, "//*[contains(text(), 'Unit project')]"): return "UNIT_PROJECT"
        return "UNKNOWN"
# File: page_analyzer.py
import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

class PageAnalyzer:
    """
    分析当前浏览器页面，以确定其内容类型。
    这是智能代理的“眼睛”，负责告诉“大脑”它看到了什么。
    """
    def __init__(self, driver: WebDriver):
        self.driver = driver

    def _element_exists(self, by: By, value: str) -> bool:
        """一个安全的辅助函数，用于检查元素是否存在，避免抛出异常。"""
        try:
            self.driver.find_element(by, value)
            return True
        except NoSuchElementException:
            return False

    def get_page_type(self) -> str:
        """
        分析当前页面并返回其类型。
        这是核心的识别函数。
        返回:
            一个表示页面类型的字符串，如 "VIDEO", "QUIZ_FILL_IN_BLANK" 等。
        """
        # 为了应对动态加载的页面，我们给予短暂的等待时间
        time.sleep(2)

        # 规则1: 是否为视频页面？ (最高优先级)
        # 视频页面最明确的标志就是 <video> 标签。
        if self._element_exists(By.TAG_NAME, "video"):
            return "VIDEO"

        # 规则2: 是否为“选词填空”题？
        # 这种题型有非常明确的标志：一个词库 (word-bank)。
        if self._element_exists(By.CSS_SELECTOR, "div.word-bank, div.word-bank-item"):
            return "QUIZ_FILL_IN_BLANK"

        # 规则 3: 是否为“选择题”？
        # 选择题的标志是存在单选框或复选框，并且在题干区域内。
        if self._element_exists(By.CSS_SELECTOR, 'div.ques-wrapper input[type="radio"], div.ques-wrapper input[type="checkbox"]'):
            return "QUIZ_MULTIPLE_CHOICE"
            
        # 规则 4: 是否为课程目录页面？
        # 课程目录有其独特的菜单项class。
        if self._element_exists(By.CSS_SELECTOR, "div.pc-slider-menu-micro"):
            return "COURSE_DIRECTORY"

        # 规则 5: 是否为阅读或普通内容页面？(较低优先级)
        # 如果以上都不是，但页面上有“下一页”按钮，我们假定它是一个阅读页面。
        if self._element_exists(By.XPATH, "//button[contains(span, '下一页')] | //button[contains(text(), 'Next')]"):
            return "READING"
            
        # 如果所有规则都不匹配，返回未知
        return "UNKNOWN"
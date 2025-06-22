import time
from selenium import webdriver
from contextlib import contextmanager
from selenium.webdriver.common.by import By
from core.config import settings

XPATH = By.XPATH
TAG_NAME = By.TAG_NAME

options = webdriver.ChromeOptions()
options.add_argument("--headless")


@contextmanager
def get_driver(debug=False):
    if debug:
        driver = webdriver.Chrome()
    else:
        if settings.CRAWLER_MODE == "prod":
            driver = webdriver.Remote(
                command_executor="http://selenium:4444/wd/hub", options=options
            )
        elif settings.CRAWLER_MODE == "dev":
            driver = webdriver.Chrome(options=options)
    try:
        yield driver
    finally:
        driver.quit()
        time.sleep(1)

import csv
import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

class VakParser:
    def __init__(self, url="https://vak.gisnauka.ru/adverts-list/advert", max_pages=3):
        self.url = url
        self.max_pages = max_pages

    def _init_driver(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        selenium_url = os.getenv("SELENIUM_REMOTE_URL", "http://localhost:4444")
        return webdriver.Remote(command_executor=f"{selenium_url}/wd/hub", options=options)

    def _wait_for_table_rows(self, driver, timeout=30):
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "tbody.ant-table-tbody tr.ant-table-row"))
            )
            return True
        except TimeoutException:
            print("table rows not loaded")
            return False

    def _wait_for_detail_page(self, driver, timeout=30):
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".card-block-content .info-row"))
            )
            return True
        except TimeoutException:
            print("detail page content not loaded")
            return False

    def _get_text_safe(self, driver, label_text, container_selector=".info-row", max_retries=5, delay=0.5):
        for attempt in range(max_retries):
            rows = driver.find_elements(By.CSS_SELECTOR, container_selector)
            for row in rows:
                try:
                    label_elem = row.find_element(By.CSS_SELECTOR, ".info-label")
                    if label_text in label_elem.text:
                        value_elem = row.find_element(By.CSS_SELECTOR, ".info-value")
                        return value_elem.text.strip()
                except NoSuchElementException:
                    continue
            if attempt < max_retries - 1:
                time.sleep(delay)
        return ""

    def _get_link_safe(self, driver, label_text, container_selector=".info-row", max_retries=5, delay=0.5):
        for attempt in range(max_retries):
            rows = driver.find_elements(By.CSS_SELECTOR, container_selector)
            for row in rows:
                try:
                    label_elem = row.find_element(By.CSS_SELECTOR, ".info-label")
                    if label_text in label_elem.text:
                        links = row.find_elements(By.CSS_SELECTOR, ".info-value a")
                        if links:
                            return links[0].get_attribute("href")
                except NoSuchElementException:
                    continue
            if attempt < max_retries - 1:
                time.sleep(delay)
        return ""

    def _wait_for_pagination(self, driver, timeout=30):
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.ant-pagination"))
            )
            return True
        except TimeoutException:
            print("pagination not loaded")
            return False

    def _go_to_page_number(self, driver, target_page):
        if not self._wait_for_pagination(driver):
            return False
        try:
            page_link = driver.find_element(By.CSS_SELECTOR, f"li.ant-pagination-item[title='{target_page}']")
        except NoSuchElementException:
            try:
                page_link = driver.find_element(By.CSS_SELECTOR, f"li.ant-pagination-item-{target_page}")
            except NoSuchElementException:
                try:
                    page_link = driver.find_element(By.XPATH, f"//li[contains(@class, 'ant-pagination-item') and .//a[text()='{target_page}']]")
                except NoSuchElementException:
                    print(f"failed to find pagination element for page {target_page}")
                    return False
        try:
            if "ant-pagination-item-active" in page_link.get_attribute("class"):
                return True
            page_link.click()
            WebDriverWait(driver, 10).until(
                EC.text_to_be_present_in_element((By.CSS_SELECTOR, "li.ant-pagination-item-active"), str(target_page))
            )
            return True
        except Exception as e:
            print(f"failed to click page {target_page}: {e}")
            return False

    def _process_detail_page(self, driver, detail_url, applicant_name, defense_date_list):
        driver.get(detail_url)
        if not self._wait_for_detail_page(driver):
            print(f"detail page failed: {detail_url}")
            return None
        result = {
            "vak_url": detail_url,
            "title": self._get_text_safe(driver, "Тема диссертации"),
            "type": self._get_text_safe(driver, "Тип диссертации"),
            "science_branch": self._get_text_safe(driver, "Отрасль науки"),
            "defense_date": self._get_text_safe(driver, "Дата защиты диссертации"),
            "primary_published_at": self._get_text_safe(driver, "Дата первичной публикации объявления"),
            "last_edited_at": self._get_text_safe(driver, "Дата редакции объявления"),
            "specialty_code": self._get_text_safe(driver, "Шифр научной специальности"),
            "defense_council_code": self._get_text_safe(driver, "Шифр диссертационного совета"),
            "defense_organization_name": self._get_text_safe(driver, "Наименование организации места защиты"),
            "organization_address": self._get_text_safe(driver, "Адрес организации"),
            "organization_phone_number": self._get_text_safe(driver, "Телефон организации"),
            "organization_advert_url": self._get_link_safe(driver, "Интернет-адрес объявления на сайте организации"),
            "applicant_name": applicant_name,
            "defense_date_list": defense_date_list
        }
        return result

    def _process_page(self, page_number):
        driver = None
        page_data = []
        try:
            driver = self._init_driver()
            print(f"processing page {page_number}")
            driver.get(self.url)
            if not self._wait_for_table_rows(driver):
                print(f"failed to load list on initial page for page {page_number}")
                return page_data
            if page_number > 1:
                if not self._go_to_page_number(driver, page_number):
                    print(f"failed to navigate to page {page_number}")
                    return page_data
                if not self._wait_for_table_rows(driver):
                    print(f"table rows not loaded after navigation to page {page_number}")
                    return page_data
            links_info = []
            rows = driver.find_elements(By.CSS_SELECTOR, "tbody.ant-table-tbody tr.ant-table-row")
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 4:
                    date = cells[1].text.strip()
                    fio = cells[2].text.strip()
                    try:
                        title_elem = cells[3].find_element(By.TAG_NAME, "a")
                        link = title_elem.get_attribute("href")
                    except NoSuchElementException:
                        link = ""
                    if link:
                        links_info.append((link, fio, date))
            for link, fio, date in links_info:
                detail = self._process_detail_page(driver, link, fio, date)
                if detail:
                    page_data.append(detail)
                driver.back()
                self._wait_for_table_rows(driver)
            print(f"page {page_number} completed, collected {len(page_data)} detailed records")
        except Exception as e:
            print(f"error on page {page_number}: {e}")
        finally:
            if driver:
                driver.quit()
        return page_data

    def parse(self):
        all_details = []
        for page_num in range(1, self.max_pages + 1):
            records = self._process_page(page_num)
            all_details.extend(records)
            print(f"page {page_num} contributed {len(records)} records")
        return all_details

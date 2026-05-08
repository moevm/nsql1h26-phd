import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

URL = "https://vak.gisnauka.ru/adverts-list/advert"
OUTPUT_CSV = "output/dissertations.csv"
MAX_PAGES = 3
THREADS = 10

def init_driver():
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
    driver = webdriver.Remote(command_executor=f"{selenium_url}/wd/hub", options=options)
    return driver

def wait_for_table_rows(driver, timeout=30):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tbody.ant-table-tbody tr.ant-table-row"))
        )
        return True
    except TimeoutException:
        print("Table rows not loaded")
        return False

def wait_for_detail_page(driver, timeout=30):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".card-block-content .info-row"))
        )
        return True
    except TimeoutException:
        print("Detail page content not loaded")
        return False

def get_text_safe(driver, label_text, container_selector=".info-row", max_retries=5, delay=0.5):
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

def get_link_safe(driver, label_text, container_selector=".info-row", max_retries=5, delay=0.5):
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

def process_detail_page(driver, detail_url, applicant_name, defense_date_list):
    driver.get(detail_url)
    if not wait_for_detail_page(driver):
        print(f"Detail page failed: {detail_url}")
        return None
    result = {}
    result["vak_url"] = detail_url
    result["title"] = get_text_safe(driver, "Тема диссертации")
    result["type"] = get_text_safe(driver, "Тип диссертации")
    result["science_branch"] = get_text_safe(driver, "Отрасль науки")
    result["defense_date"] = get_text_safe(driver, "Дата защиты диссертации")
    result["primary_published_at"] = get_text_safe(driver, "Дата первичной публикации объявления")
    result["last_edited_at"] = get_text_safe(driver, "Дата редакции объявления")
    result["specialty_code"] = get_text_safe(driver, "Шифр научной специальности")
    result["defense_council_code"] = get_text_safe(driver, "Шифр диссертационного совета")
    result["defence_organization_name"] = get_text_safe(driver, "Наименование организации места защиты")
    result["organization_address"] = get_text_safe(driver, "Адрес организации")
    result["organization_phone_number"] = get_text_safe(driver, "Телефон организации")
    result["organization_advert_url"] = get_link_safe(driver, "Интернет-адрес объявления на сайте организации")
    result["applicant_name"] = applicant_name
    result["defense_date_list"] = defense_date_list
    return result

def process_page(page_number):
    driver = None
    page_data = []
    try:
        driver = init_driver()
        page_url = f"{URL}?page={page_number}"
        print(f"Processing page {page_number}: {page_url}")
        driver.get(page_url)
        if not wait_for_table_rows(driver):
            print(f"Failed to load list on page {page_number}")
            return page_data

        links_info = []
        rows = driver.find_elements(By.CSS_SELECTOR, "tbody.ant-table-tbody tr.ant-table-row")
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 4:
                number = cells[0].text.strip()
                date = cells[1].text.strip()
                fio = cells[2].text.strip()
                try:
                    title_elem = cells[3].find_element(By.TAG_NAME, "a")
                    title = title_elem.text.strip()
                    link = title_elem.get_attribute("href")
                except NoSuchElementException:
                    title = cells[3].text.strip()
                    link = ""

                if link:
                    links_info.append((link, fio, date))
                else:
                    print(f"No detail link for {fio}, skipping")

        for link, fio, date in links_info:
            detail = process_detail_page(driver, link, fio, date)
            if detail:
                page_data.append(detail)
            driver.back()
            wait_for_table_rows(driver)

        print(f"Page {page_number} completed, collected {len(page_data)} detailed records")
    except Exception as e:
        print(f"Error on page {page_number}: {e}")
    finally:
        if driver:
            driver.quit()
    return page_data

def parse():
    all_details = []
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {executor.submit(process_page, page_num): page_num for page_num in range(1, MAX_PAGES + 1)}
        for future in as_completed(futures):
            page_num = futures[future]
            try:
                records = future.result()
                all_details.extend(records)
                print(f"Page {page_num} contributed {len(records)} records")
            except Exception as e:
                print(f"Page {page_num} generated an exception: {e}")

    if all_details:
        os.makedirs("output", exist_ok=True)
        fieldnames = [
            "vak_url", "title", "type", "science_branch", "defense_date",
            "primary_published_at", "last_edited_at", "specialty_code",
            "defense_council_code", "defence_organization_name",
            "organization_address", "organization_phone_number",
            "organization_advert_url", "applicant_name", "defense_date_list"
        ]
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_details)
        print(f"Saved {len(all_details)} records to {OUTPUT_CSV}")
    else:
        print("No data collected")


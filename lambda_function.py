import time
import json
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import boto3
import requests

def lambda_handler(event, context):
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.binary_location = "/opt/chrome/chrome"
    chrome_options.add_argument("--headless")  # Headless 모드
    chrome_options.add_argument("--no-sandbox")  # Sandbox 비활성화 (필수)
    chrome_options.add_argument("--disable-dev-shm-usage")  # /dev/shm 사용 비활성화
    chrome_options.add_argument("--disable-gpu")  # GPU 비활성화
    chrome_options.add_argument("--window-size=1280x1696")  # 화면 크기 설정
    chrome_options.add_argument("--single-process")  # 싱글 프로세스 모드
    chrome_options.add_argument("--disable-software-rasterizer")  # 소프트웨어 래스터라이저 비활성화
    chrome_options.add_argument("--disable-extensions")  # 확장 프로그램 비활성화
    chrome_options.add_argument("--remote-debugging-port=9222")  # 디버깅 포트 설정
    print("Chrome 옵션 설정 완료")  # 추가된 디버깅 메시지

    # ChromeDriver 설정
    service = Service(executable_path="/opt/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("ChromeDriver 시작 완료")  # 추가된 디버깅 메시지

    # 무신사 코디 페이지로 이동
    driver.get("https://www.musinsa.com/app/stylecontents/lists?sortType=RECENT&contentsTypes=CODI_SHOP")

    # 페이지 필터 버튼 클릭
    filter_buttons = [
        '/html/body/div[1]/div[4]/div[1]/div/div/button[1]',
        '/html/body/div[1]/div[4]/div[1]/div/div/button[2]',
        '/html/body/div[1]/div[4]/div[1]/div/div/button[3]'
    ]

    # 첫 번째 필터 처리
    click_buttons(driver, filter_buttons[:2])
    time.sleep(3)
    process_links(driver, "MAN")

    # 무신사 코디 페이지로 이동
    driver.get("https://www.musinsa.com/app/stylecontents/lists?sortType=RECENT&contentsTypes=CODI_SHOP")
    print("무신사 코디 페이지로 이동완료")

    # 잠시 대기하여 페이지가 로드될 시간을 줌
    time.sleep(5)

    # 두 번째 필터 처리
    click_buttons(driver, filter_buttons[1:])
    time.sleep(3)
    process_links(driver, "WOMAN")

    # 웹 드라이버 종료
    driver.quit()

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

def click_buttons(driver, buttons):
    """주어진 필터 버튼들을 클릭하는 함수"""
    for button in buttons:
        try:
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, button))
            )
            element.click()
        except NoSuchElementException:
            print(f"요소를 찾을 수 없습니다: {button}")
            continue

def process_links(driver, category):
    """페이지에서 코디 이미지 링크를 추출하고 S3에 저장하는 함수"""
    html_content = driver.page_source
    soup = BeautifulSoup(html_content, 'html.parser')
    codi_elements = soup.select('div.sc-nemxqz-2.gxBJhv img')

    # 스킴이 누락된 경우 https 추가
    codi_element_list = []
    for element in codi_elements:
        src = element.get('src')
        if src.startswith('//'):
            src = 'https:' + src
        codi_element_list.append(src)

    print(f"{category} 코디 이미지 링크 리스트:", codi_element_list)

    # S3에 저장
    bucket_name = 'mojji-bucket'
    save_image_to_s3(codi_element_list, category, bucket_name)

def save_image_to_s3(image_urls, category, bucket_name):
    """이미지 URL 리스트를 S3에 저장하는 함수"""
    s3 = boto3.client('s3')

    # 저장 경로 설정
    s3_base_path = f"main/static/img/codishop/{category}/"

    for idx, image_url in enumerate(image_urls):
        try:
            # 이미지 다운로드
            response = requests.get(image_url)
            if response.status_code == 200:
                # 이미지 데이터를 바이너리로 읽음
                image_data = response.content

                # S3에 저장할 파일 경로 (Key)
                file_name = f"{s3_base_path}CODI_SHOP_{category}_{idx+1}.jpg"
                print(f"S3에 저장할 파일 경로: {file_name}")

                # S3에 파일 업로드
                s3.put_object(Bucket=bucket_name, Key=file_name, Body=image_data)
                print(f"이미지가 S3에 업로드되었습니다: {file_name}")
            else:
                print(f"이미지 다운로드 실패: {image_url}")
        except Exception as e:
            print(f"이미지를 S3에 저장하는 중 오류 발생: {e}")
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
import requests
import os
import json
import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

def find_naver_campaign_links_ppom(naver_id, base_url_ppom, visited_urls_file='visited_urls.txt'):
    # 방문한 URL 파일에서 읽기
    try:
        with open(visited_urls_file, 'r') as file:
            visited_urls = set(file.read().splitlines())
    except FileNotFoundError:
        visited_urls = set()

    # 기본 URL에 대한 요청
    response = requests.get(base_url_ppom)
    soup = BeautifulSoup(response.text, 'html.parser')

    # 'list_subject' 클래스를 가진 span 요소 찾기 및 'a' 태그 추출
    list_subject_links = soup.find_all('a', class_='list_b_01n')
    naver_links = []
    for span in list_subject_links:
        if '네이버' in span.text:
            naver_links.append(span['href'])
            # sendSlack(span['href'])
            # print(span.text)

    # 캠페인 링크를 저장할 리스트 초기화
    campaign_links = []

    # 각 네이버 링크 확인
    for link in naver_links:
        full_link = urljoin(base_url_ppom, link)

        if full_link in visited_urls:
            # print("이미 방문: %s" % full_link)
            continue  # 이미 방문한 링크는 건너뛰기

        res = requests.get(full_link)
        inner_soup = BeautifulSoup(res.text, 'html.parser')

        # 캠페인 URL로 시작하는 링크 찾기
        for a_tag in inner_soup.find_all('a', href=True):
            if "https://campaign2-api.naver.com" in a_tag.text:
                campaign_links.append(a_tag['href'])

        # 방문한 링크 추가
        visited_urls.add(full_link)

        # 방문한 URL 파일에 저장
        # with open(visited_urls_file, 'w') as file:
        #     for url in visited_urls:
        #         file.write(url + '\n')

    # 중복 제거 
    my_set = set(campaign_links)
    campaign_links = list(my_set)

    return campaign_links


def sendSlack(message, link, token):
    url = "https://slack.com/api/chat.postMessage"

    payload = json.dumps({
        "channel": "C06BKCE6UJF",
        "text": message,
        "attachments": [
            {
                "text": link,
                "color": "#3AA3E3",
                "attachment_type": "default"
            }
        ]
    })

    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.text


# The base URL to start with
base_url = "https://www.clien.net/service/board/jirum"
base_url_ppom = "https://m.ppomppu.co.kr/new/bbs_list.php?id=coupon"

input_id = os.getenv("NAVERUSERNAME","ID is null")
input_pw = os.getenv("NAVERPASSWORD","PASSWORD is null")
send_slack = os.getenv("SENDSLACK","SENDSLACK is null")
slack_token = os.getenv("SLACKTOKEN","SLACKTOKEN is null")

current_time = datetime.datetime.now()

campaign_links = find_naver_campaign_links_ppom(input_id, base_url_ppom)
if(campaign_links == []):
    print("모든 링크 방문")
    if send_slack == "True":
        print(sendSlack("모든 링크 방문", " ", slack_token))
else: 
    # 크롬 드라이버 옵션 설정
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('headless') # headless mode

    # 새로운 창 생성
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get('https://nid.naver.com/nidlogin.login')

    # 현재 열려 있는 창 가져오기
    current_window_handle = driver.current_window_handle

    # <a href class='MyView-module__link_login___HpHMW'> 일때 해당 링크 클릭
    # driver.find_element(By.XPATH, "//a[@class='MyView-module__link_login___HpHMW']").click()

    # 새롭게 생성된 탭의 핸들을 찾습니다
    # 만일 새로운 탭이 없을경우 기존 탭을 사용합니다.
    new_window_handle = None
    for handle in driver.window_handles:
        if handle != current_window_handle:
            new_window_handle = handle
            break
        else:
            new_window_handle = handle

    # 새로운 탭을 driver2로 지정합니다
    driver.switch_to.window(new_window_handle)
    driver2 = driver

    driver2.save_screenshot("1.png")

    username = driver2.find_element(By.NAME, 'id')
    pw = driver2.find_element(By.NAME, 'pw')

    # ID input 클릭
    username.click()
    # js를 사용해서 붙여넣기 발동 <- 왜 일부러 이러냐면 pypyautogui랑 pyperclip를 사용해서 복붙 기능을 했는데 운영체제때문에 안되서 이렇게 한거다.
    driver2.execute_script("arguments[0].value = arguments[1]", username, input_id)
    time.sleep(1)

    driver2.save_screenshot("2.png")

    pw.click()
    driver2.execute_script("arguments[0].value = arguments[1]", pw, input_pw)
    time.sleep(1)

    driver2.save_screenshot("3.png")

    #입력을 완료하면 로그인 버튼 클릭
    driver2.find_element(By.CLASS_NAME, "btn_login").click()
    time.sleep(1)

    driver2.save_screenshot("4.png")
    
    for link in campaign_links:
        print(link) # for debugging
        # Send a request to the base URL
        driver2.get(link)
        
        try:
            result = driver2.switch_to.alert
            print(result.text)
            
            if send_slack == "True":
                if "원이" in result.text:
                    
                    # 가격 추출
                    start = result.text.find("원이")
                    priceString = result.text[start - 3:start]
                    price = "".join(filter(str.isdigit, priceString))
                    
                    sendSlack("<!channel> 네이버 폐지 줍기 성공 - " + price + "원", link, slack_token)
            
            result.accept()
        except:
            print("no alert")
            # pageSource = driver2.page_source
            # print(pageSource)        
        time.sleep(1)

    time.sleep(10)
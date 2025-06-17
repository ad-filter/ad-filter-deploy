# 2 crawler.py : 대상 네이버 블로그 글 크롤링
import re, html, datetime
from bs4 import BeautifulSoup  # 웹페이지
from selenium.webdriver.support.ui import WebDriverWait  # 요소 대기
from selenium.webdriver.support import expected_conditions as EC  # 조건 대기s
from selenium.webdriver.common.by import By  # 요소 선택
import cv2  # openCV
import numpy as np
import requests  # http request
from PIL import Image  # Python Imaging Library
from io import BytesIO  # response 값은 바이너리 값이므로
from paddleocr import PaddleOCR  # OCR
from urllib.parse import urlparse, parse_qs  # URL 파싱
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import re, time
from bs4 import BeautifulSoup  # 웹페이지 파싱
from selenium.webdriver.common.by import By  # 요소 선택
import requests  # HTTP 요청


# iframe 전환
def try_switch_to_frame(driver, frame_id):
    try:
        iframe = driver.find_element(By.ID, frame_id)
        driver.switch_to.frame(iframe)
        print(f"[DEBUG] iframe 전환 성공: {frame_id}")
        return True
    except Exception as e:
        print(f"[DEBUG] iframe 전환 실패: {frame_id} - {e}")
        return False

# PaddleOCR 모델 초기화
ocr = PaddleOCR(use_angle_cls=True, lang="korean")

# OCR을 위한 형식 변환 (PIL.Image → OpenCV BGR 이미지)
def format_image_for_ocr(pil_image):
    # 이미지의 모든 색상을 RGB로 바꿈 (OpenCV를 위한 전처리)
    rgb_image = pil_image.convert("RGB")
    # opencv는 NumPy배열(높이,너비,채널 수 3차원 배열) 형태로 처리
    np_image = np.array(rgb_image)
    # cvtColor: opencv가 해석할 수 있도록 rgb -> bgr 포맷으로 변화
    bgr_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
    return bgr_image

# 이미지에서 OCR 텍스트 추출 (PaddleOCR)
def extract_text_from_image(url):
    try:
        # 1. URL이 '//'로 시작하면 'https:' 붙이기
        if url.startswith("//"):
            url = "https:" + url

        # 2. 'src=' 파라미터에 진짜 이미지가 들어있다면 그걸로 다시 설정
        if "src=" in url:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            real_url = query_params.get("src", [None])[0]
            if real_url:
                url = real_url

        response = requests.get(url, timeout=5)
        pil_img = Image.open(BytesIO(response.content))

        # OCR
        opencv_img = format_image_for_ocr(pil_img)  # 형식 변환
        result = ocr.ocr(opencv_img, cls=True)  # 이미지 -> 텍스트 추출
        if not result:  # None 또는 빈 결과
            return "N/A"

        texts = []
        # 결과에서 텍스트 추출
        for line in result:
            # line은 [[box, (text, confidence)], ...] 형태
            # box는 좌표 정보, text는 인식된 텍스트, confidence는 신뢰도
            if line:  # line 자체가 None인 경우도 대비
                for box, (text, confidence) in line:
                    # 신뢰도가 0.5 이상인 경우만 추출
                    if confidence >= 0.5:
                        texts.append(text)
        return " ".join(texts) if texts else "N/A"

    except Exception as e:
        print(f"❌ OCR 실패: {e}, {url}")
        return "N/A"

# 본문에서 해시태그 추출 및 제거
def extract_and_remove_hashtags(text: str):
    # 해시태그 추출: #으로 시작하고 한글/영문/숫자 포함 (띄어쓰기 또는 특수문자 전까지)
    hashtags = re.findall(r"#\w+", text)

    if not hashtags:
        str_hashtags = "N/A"
    else:
        str_hashtags = " ".join(hashtags)
        print("[DEBUG] 해시태그:", str_hashtags)

    # 해시태그 제거
    text_without_hashtags = re.sub(r"#\w+", "", text)

    # 앞뒤 공백 및 연속된 줄바꿈 정리
    text_without_hashtags = re.sub(r"\n{2,}", "\n", text_without_hashtags).strip()

    return str_hashtags, text_without_hashtags


# 공백, 줄바꿈 제거
def final_whitespace_cleanup(text):
    text = re.sub(r"[ \t]+", " ", text)  # 다중 공백 → 1칸
    text = re.sub(r"\n{2,}", "\n", text)  # 다중 줄바꿈 → 1줄
    text = text.strip()
    return text


# 평균, 최소, 최대 글자 수
def extract_line_length_stats(text):
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    lengths = [len(line) for line in lines]
    if not lengths:
        return {
            "line_count": 0,
            "avg_line_length": 0,
            "min_line_length": 0,
            "max_line_length": 0,
            "short_line_ratio": 0.0,
        }
    short_lines = [l for l in lengths if l <= 10]
    return {
        "line_count": len(lines),
        "avg_line_length": sum(lengths) / len(lengths),
        "min_line_length": min(lengths),
        "max_line_length": max(lengths),
        "short_line_ratio": len(short_lines) / len(lines),
    }


# 작성일이 24시간 내일 경우, 현재 시각을 확인하고 일자(YYYYMMDD)로 바꿔 출력
def calculate_date(text):
    date_str = text.get_text(strip=True)
    current = datetime.datetime.now()
    time_units = {
        "시간 전": "hours",
        "분 전": "minutes",
        "초 전": "seconds",
    }
    for keyword, unit in time_units.items():
        if keyword in date_str:
            value = int(re.sub(keyword, "", date_str))
            delta = datetime.timedelta(**{unit: value})
            edit_date = current - delta
            return edit_date.strftime("%Y%m%d")
        else:
            date_list = re.sub(r"\d{1,2}:\d{2}", "", date_str).split(". ")
            edit_date = "".join(
                ["0" + num if len(num) == 1 else num for num in date_list]
            )
            return edit_date


# 깨끗한 본문 텍스트 추출 (html 스타일 태그로 인한 불필요한 줄바꿈 제거)
def get_clean_text(content):
    # <br>은 줄바꿈으로 대체
    for br in content.find_all("br"):
        br.replace_with("\n")

    # 의미 있는 블록 단위 태그 앞뒤에 줄바꿈 삽입
    block_tags = ["p", "div", "blockquote", "li", "dd", "dt", "tr"]
    for tag in content.find_all(block_tags):
        tag.insert_before("\n")
        tag.insert_after("\n")

    # 인라인 스타일 태그는 제거
    for tag in content.select("span, b, i, u, em, strong"):
        tag.unwrap()

    # 텍스트 추출 (태그 제거 후)
    raw_text = content.get_text()
    # 공백, 중복 줄바꿈 정리
    cleaned = re.sub(r"[ \t]+", " ", raw_text)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    return cleaned.strip()


# `일정` 블록에서 제목, 날짜만 남기고 나머지는 제거
def handle_schedule_blocks(content, soup):
    schedule_blocks = content.select("div.se-component.se-schedule")
    for schedule in schedule_blocks:
        try:
            title_el = schedule.select_one("strong.se-schedule-title-text")
            title = title_el.get_text(strip=True) if title_el else ""

            date_el = schedule.select_one("p.se-schedule-duration")
            date = date_el.get_text(strip=True) if date_el else ""

            # 정리된 텍스트 구성
            schedule_text = f"[일정] {title} {date}"

            # 새 태그로 교체
            new_tag = soup.new_tag("p")
            new_tag.string = schedule_text
            schedule.replace_with(new_tag)

            print("[DEBUG] 일정:", title, date)

        except Exception as e:
            print(f"❌ 일정 처리 실패: {e}")
            schedule.decompose()  # 오류 시 해당 일정 제거


# `첨부 파일` 블록에서 제목.확장자만 남기고 나머지는 제거
def handle_file_blocks(content, soup):
    file_blocks = content.select("div.se-component.se-file")
    for file_block in file_blocks:
        try:
            name_el = file_block.select_one("span.se-file-name")
            ext_el = file_block.select_one("span.se-file-extension")

            name = name_el.get_text(strip=True) if name_el else ""
            ext = ext_el.get_text(strip=True) if ext_el else ""

            filename = f"[첨부파일] {name}{ext}"

            new_tag = soup.new_tag("p")
            new_tag.string = filename
            file_block.replace_with(new_tag)

            print("[DEBUG] 첨부파일:", filename)

        except Exception as e:
            print(f"❌ 첨부파일 처리 실패: {e}")
            file_block.decompose()


# `글감` 블록에서 제목만 남기고 나머지는 제거 -> 링크로 카운트
def handle_material_blocks(content, soup):
    count = 0
    material_blocks = content.select("div.se-component.se-material")
    for block in material_blocks:
        try:
            # 기본 방법: a 태그의 title 속성
            title = ""
            link_el = block.select_one("a[title]")
            if link_el and "title" in link_el.attrs:
                title = link_el["title"].strip()

            # 대체 방법: strong.se-material-title 같은 구조에서 텍스트 추출
            if not title:
                title_el = block.select_one(".se-material-title")
                if title_el:
                    title = title_el.get_text(strip=True)

            final_text = f"[글감] {title if title else '제목없음'}"

            # 텍스트만 삽입
            block.replace_with(soup.new_string(final_text))
            count += 1

            print("[DEBUG] 글감:", title)
        except Exception as e:
            print(f"❌ 글감 처리 실패: {e}")
            block.decompose()
    print("[DEBUG] 글감 개수:", count)
    return count


# `지도` 블록에서 제목만 남기고 나머지는 제거
def handle_map_blocks(content, soup):
    map_blocks = content.select("div.se-component.se-placesMap")
    for block in map_blocks:
        try:
            # 지도 제목: strong.se-map-title
            title_el = block.select_one("strong.se-map-title")
            title = title_el.get_text(strip=True) if title_el else "제목없음"

            # 텍스트 구성
            map_text = f"[지도] {title}"

            # 새 p 태그로 교체
            new_tag = soup.new_tag("p")
            new_tag.string = map_text
            block.replace_with(new_tag)

            print("[DEBUG] 지도:", title)
        except Exception as e:
            print(f"❌ 지도 처리 실패: {e}")
            block.decompose()


# 블로그 포스트 추출
def get_blog_post(driver):
    # 현재 페이지 파싱
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 제목, 작성일, 본문
    title = soup.select_one("h3.se_textarea, .pcol1")
    date = soup.select_one(".se_publishDate")
    content = soup.select_one("div.se-main-container, #postViewArea")
    post_count = soup.select_one(".num.cm-col1")

    # 작성일, 전체 글 수 데이터 수정
    date = calculate_date(date)
    post_count = re.sub(
        r"[\(\)]", "", post_count.get_text(strip=True) if post_count else "N/A"
    )

    link_count = 0
    # open graph 처리 -> 링크 개수 센 다음 제거
    og_blocks = content.select("div.se-component.se-oglink")
    link_count += len(og_blocks)
    print("[DEBUG] open graph 링크 개수:", link_count)
    for og in og_blocks:
        print("[DEBUG] open graph 링크:", og.get_text(strip=True))
        og.decompose()

    # 본문 글이 아닌 데이터 삭제
    for selector in [
        'div.se-component[class*="se-video"]',  # 영상 재생 안내문 포함
        "div.se-component.se-video",  # 직접 첨부 동영상
        "div.se-imageGroup-navigation",  # 슬라이드 이미지의 노이즈
    ]:
        for tag in content.select(selector):
            tag.decompose()

    # 본문 중 특수 블록 처리
    handle_map_blocks(content, soup)  # 지도 블록
    handle_schedule_blocks(content, soup)  # 일정 블록
    handle_file_blocks(content, soup)  # 첨부파일 블록
    link_count += handle_material_blocks(content, soup)  # 글감 블록

    # 본문(content) 정제
    clean_text = get_clean_text(content)
    clean_text = html.unescape(clean_text)
    clean_text = final_whitespace_cleanup(clean_text)
    tags, clean_text = extract_and_remove_hashtags(clean_text)

    # 본문 내 링크 개수 (https)
    link_count += len(re.findall(r"https?://\S+", clean_text))
    print("[DEBUG] 본문 내 링크의 총 개수:", link_count)
    clean_text = re.sub(r"https?://\S+", "", clean_text)

    # 본문 내 이미지 추출
    images = content.select("img") if content else []
    image_urls = [img.get("src") for img in images if img.get("src")]

    # 댓글 수
    try:
        comment_count_el = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "em#commentCount"))
        )
        comment_count = comment_count_el.text.strip()
        if (comment_count is None) or (comment_count == ""):
            comment_count = "0"
    except:
        comment_count = "0"
    print("[DEBUG] 댓글 수:", comment_count)

    return {
        "post_title": title.get_text(strip=True) if title else "N/A",
        "post_date": date if date else "N/A",
        "post_content": clean_text,
        "post_tags": tags,
        "post_image_urls": image_urls,
        "post_comment_count": comment_count,
        "link_count": link_count,
        "post_count": post_count,
    }

# 블로그 개설일 추출
def get_blog_creation_date_from_blog_home(driver, blog_id):
    driver.get(f"https://blog.naver.com/profile/history.naver?blogId={blog_id}")
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # "블로그 시작" 문구가 포함된 td 찾기
    start_td = soup.find("td", string=lambda t: t and "블로그" in t and "시작" in t)

    creation_date = "N/A"
    if start_td:
        # 바로 이전 형제 태그(tr)의 날짜 추출
        prev_tr = start_td.find_parent("tr").find_previous_sibling("tr")
        if prev_tr:
            date_td = prev_tr.find("td")
            if date_td:
                creation_date = date_td.get_text(strip=True)
                # 날짜 형식 변환 (YYYYMMDD)
                match = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", creation_date)
                if match:
                    year, month, day = match.groups()
                    creation_date = f"{int(year):04d}{int(month):02d}{int(day):02d}"
    print("[DEBUG] 개설일:", creation_date)
    return creation_date


# 블로그 정보 추출
def get_blog_info(driver, blog_id):
    # 1. 블로그 홈 접속
    driver.get(f"https://blog.naver.com/{blog_id}")
    time.sleep(2)

    # 2. iframe 전환
    if not try_switch_to_frame(driver, "mainFrame"):
        print("[DEBUG] iframe 전환 실패")

    # 3. 블로그 개설일 추출
    driver.switch_to.default_content()
    creation_date = get_blog_creation_date_from_blog_home(driver, blog_id)

    return {
        "blog_author": blog_id,
        "blog_creation_date": creation_date,
    }

#-----------------------------------------------------------------------------------------------
# 크롤링 통합
def crawl(post_url, driver) :
    url=post_url
    if not url.startswith("http"):
        print(f"❌ 잘못된 URL 형식: {url}")
        
    try:
        driver.get(url)
        time.sleep(2)
        driver.switch_to.default_content()
        try:
            driver.switch_to.frame("mainFrame")
        except:
           pass
        
        content = get_blog_post(driver)
        ocr_first = (
           extract_text_from_image(content["post_image_urls"][0])
           if content["post_image_urls"]
           else "N/A"
       )
        ocr_last = (
           extract_text_from_image(content["post_image_urls"][-1])
           if len(content["post_image_urls"]) > 1
           else "N/A"
       )
        content.pop("post_image_urls", None) # post_image_urls 항목 제외 -> ai 모델 입력값으로 사용되지 않음
        blog_id = url.split("/")[3]
        info = get_blog_info(driver, blog_id)
        stats = extract_line_length_stats(content["post_content"])
        results={
               "post_url": url,
               **content,
               "post_first_image_ocr": ocr_first,
               "post_last_image_ocr": ocr_last,
               **info,
               **stats,
           }
        return results
    except Exception as e:
       print(f"❌ 에러 발생: {e}")
       return {
                "post_url": url,
               **content,
               "post_first_image_ocr": ocr_first,
               "post_last_image_ocr": ocr_last,
               **info,
               **stats
       }

# 1 main.py: 프론트 요청 처리, 반환

from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from fastapi.middleware.cors import CORSMiddleware
import traceback
from crawler import crawl
from preprocessor import preprocess_for_model
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from joblib import load    # 모델

model, threshold = load("final_model.joblib")

app = FastAPI()

CHROME_DRIVER_PATH = ChromeDriverManager().install()
# 크롬 웹드라이버 설치
def create_driver() :
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--log-level=3")
    return webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=options)

# CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 입력 데이터 모델
class CrawlRequest(BaseModel):
    url: str

# 요청/응답 로깅용 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    print(f"\n📥 요청: {request.method} {request.url}")
    print(f"📦 요청 내용: {body.decode('utf-8')}")
    try:
        response = await call_next(request)
    except Exception as e:
        print(f" 예외 발생: {str(e)}")
        traceback.print_exc()
        raise e
    print(f" 응답 상태: {response.status_code}")
    return response

@app.post("/predict")
def crawl_url(data: CrawlRequest):
    print(f"\n수신된 URL: {data.url}")
    try:
        # 1. 크롤링 함수 호출
        driver=create_driver()
        result = crawl(data.url, driver)
        driver.quit()

        # 2. 전처리
        X_input = preprocess_for_model(result)

        # 3. AI 판별
        # 모델과 threshold 불러오기
        prob = model.predict_proba(X_input)[:, 1][0]
        is_ad = bool(prob > threshold)
        
        print(f"광고일 확률: {prob:.4f}, 광고 여부: {' 🚨광고' if is_ad else '✅일반'}")

        return {
            "is_ad": is_ad
        }

    except Exception as e:
        print("🚨 오류 발생:", str(e))
        traceback.print_exc()
        return {
            "is_ad": None,
            "error": str(e)
        }
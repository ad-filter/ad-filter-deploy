# 3 preprocessor.py: 크롤링한 데이터 전처리

import pandas as pd
from datetime import datetime

def preprocess_for_model(crawl_result: dict) -> pd.DataFrame:
    # 기본 복사
    data = crawl_result.copy()

    # 결합 텍스트 컬럼
    for field in ['post_title', 'post_content', 'post_tags']:
        data[field] = data.get(field, '') or ''
    data['content_combined'] = f"{data['post_title']} {data['post_content']} {data['post_tags']}"

    for field in ['post_first_image_ocr', 'post_last_image_ocr']:
        data[field] = data.get(field, '') or ''
    data['ocr_combined'] = f"{data['post_first_image_ocr']} {data['post_last_image_ocr']}"

    # 수치형 결측치 보정
    numeric_fields = [
        'post_comment_count', 'link_count', 'post_count',
        'line_count', 'avg_line_length', 'min_line_length',
        'max_line_length', 'short_line_ratio'
    ]
    for field in numeric_fields:
        val = data.get(field, 0)
        data[field] = float(val) if val not in ["N/A", "", None] else 0.0

    # 날짜 → 연도 추출
    def extract_year(date_str):
        try:
            if isinstance(date_str, int):
                date_str = str(date_str)
            dt = datetime.strptime(date_str, '%Y%m%d')
            return dt.year
        except:
            return 2020  # 평균값 또는 default 연도

    data['creation_date'] = extract_year(data.get('blog_creation_date'))
    data['post_date'] = extract_year(data.get('post_date'))

    # 최종 입력 컬럼 순서
    input_data = {
        'content_combined': data['content_combined'],
        'ocr_combined': data['ocr_combined'],
        'post_comment_count': data['post_comment_count'],
        'link_count': data['link_count'],
        'post_count': data['post_count'],
        'line_count': data['line_count'],
        'avg_line_length': data['avg_line_length'],
        'min_line_length': data['min_line_length'],
        'max_line_length': data['max_line_length'],
        'short_line_ratio': data['short_line_ratio'],
        'creation_date': data['creation_date'],
        'post_date': data['post_date']
    }

    return pd.DataFrame([input_data])


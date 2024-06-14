import pandas as pd
import requests
import json

# Papago 번역 함수
def papago_translation(text, source_lang='en', target_lang='ko'):
    url = "https://naveropenapi.apigw.ntruss.com/nmt/v1/translation"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": "API-KEY-ID",
        "X-NCP-APIGW-API-KEY": "API-KEY",
        "Content-Type": "application/json"
    }
    data = {
        "source": source_lang,
        "target": target_lang,
        "text": text
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        translated_text = response.json()['message']['result']['translatedText']
        # 번역 결과가 '사람인'인 경우 '사람'으로 반환
        if translated_text.strip() == '사람인':
            translated_text = '사람'
        # 번역 결과가 '바디_부분'인 경우 '신체부위'로 반환
        if translated_text.strip() == '바디_부분':
            translated_text = '신체부위'
        # 번역 결과가 '개'인 경우 '강아지'로 반환
        if translated_text.strip() == '개':
            translated_text = '강아지'
        # 번역 결과가 '베이킹_굿즈'인 경우 '빵'으로 반환
        if translated_text.strip() == '베이킹_굿즈':
            translated_text = '빵'
        # 번역 결과가 '마실것'인 경우 '음료'로 반환
        if translated_text.strip() == '마실것':     
            translated_text = '음료'
        # 번역 결과가 '못'인 경우 '손톱'로 반환
        if translated_text.strip() == '못':
            translated_text = '손톱'
        # 번역 결과가 '플라워'인 경우 '꽃'으로 반환
        if translated_text.strip() == '플라워':
            translated_text = '꽃'
        # 번역 결과가 '선셋'인 경우 '일몰'로 반환
        if translated_text.strip() == '선셋':
            translated_text = '일몰'
        # 번역 결과가 '선라이즈'인 경우 '일출'로 반환
        if translated_text.strip() == '선라이즈':
            translated_text = '일출'

        return translated_text
    else:
        return "번역에 실패했습니다. 오류 코드: {}".format(response.status_code)

#csv 번역 함수
def translate_csv(CSV_PATH):
    print("번역 시작")
 
    target_column_name = "Entity2"
    relationship_column_name = "Relationship"

    df = pd.read_csv(CSV_PATH)

    # 각 행에 대해 번역 수행
    for index, row in df.iterrows():
        # 열의 인덱스를 찾음
        target_column_index = df.columns.get_loc(target_column_name)
        relationship_column_index = df.columns.get_loc(relationship_column_name)

        #relationship_column이 "텍스트"일 때만 번역을 스킵
        if row[relationship_column_name] == "텍스트":
            continue  # 번역을 스킵하고 다음 행으로 넘어감
        else:
            # target_column 컬럼의 값이 영어인 경우에만 번역 수행
            if isinstance(row[target_column_name], str) and row[target_column_name].strip() != "" and row[target_column_name].isascii():
                #첫 글자를 대문자로 변경
                row[target_column_name] = row[target_column_name].capitalize()
                # 번역 실행
                translated_text = papago_translation(row[target_column_name])
                # 마침표 제거
                translated_text = translated_text.rstrip('.')
                # 공백 제거
                translated_text = translated_text.replace(" ","")
                # 번역 결과를 해당 컬럼에 할당
                df.at[index, target_column_name] = translated_text

            # relationship 컬럼의 값이 영어인 경우에만 번역 수행
            if isinstance(row[relationship_column_name], str) and row[relationship_column_name].strip() != "" and row[relationship_column_name].isascii():
                #첫 글자를 대문자로 변경
                row[relationship_column_name] = row[relationship_column_name].capitalize()
                # 번역 실행
                translated_relation = papago_translation(row[relationship_column_name])
                # 마침표 제거
                translated_relation = translated_relation.rstrip('.')
                # 공백 제거
                translated_relation = translated_relation.replace(" ","")
                # 번역 결과를 해당 컬럼에 할당
                df.at[index, relationship_column_name] = translated_relation

    # 번역이 완료된 데이터프레임을 새로운 CSV 파일로 저장
    df.to_csv(CSV_PATH, index=False)
    print("번역 완료")


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
            
                # 번역 결과를 해당 컬럼에 할당
                df.at[index, target_column_name] = translated_text

            # relationship 컬럼의 값이 영어인 경우에만 번역 수행
            if isinstance(row[relationship_column_name], str) and row[relationship_column_name].strip() != "" and row[relationship_column_name].isascii():
              
                # 번역 결과를 해당 컬럼에 할당
                df.at[index, relationship_column_name] = translated_relation

    # 번역이 완료된 데이터프레임을 새로운 CSV 파일로 저장
    df.to_csv(CSV_PATH, index=False)
    print("번역 완료")


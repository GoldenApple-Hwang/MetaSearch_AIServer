import requests

#neo4j 서버에 csv 요청
def request_csv_neo4jServer(database,csv_file_path):
    # 저장되어야하는 csv 파일 경로
    #csv_path = f'./{database}/CSV/' 

    #neo4j 서버의 url
    neo4j_url = f'http://113.198.85.4/neo4jserver/csv'

    # 전송할 데이터베이스 이름
    database_name = {'dbName':database}

    #JSON 형태로 데이터베이스 이름을 POST 방식으로 전송
    response = requests.post(neo4j_url,json=database_name)

    #서버 응답 확인
    if response.status_code == 200:
        #서버로부터 받은 CSV 파일 저장
        with open(csv_file_path, "wb") as file:
            file.write(response.content)
            print('Successfully saved the CSV file.')
        return True
    else:
        print('Failed to receive the CSV file.')
        return False
    

# neo4j 서버에 csv 전송
def send_neo4jServer(csv_file_path):
    neo4j_url = 'http://113.198.85.4/aiserver/uploadcsv'  # Node.js 서버의 엔드포인트
    files = {'csvfile': open(csv_file_path, 'rb')}  # 'example.csv'는 전송하고자 하는 파일명
    response = requests.post(neo4j_url, files=files) # node.js에 파일 전송
    print(response.text)  # 서버의 응답 출력
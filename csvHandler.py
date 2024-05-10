import serverConnectionHandler
import csv
import pandas as pd
import os

# csv 파일에 파일이름 들어간 행 삭제하는 함수
def delete_csv_file_info(csv_file_path,filename):
    #csv 파일을 dataframe으로 불러옴
    csv_dataframe = pd.read_csv(csv_file_path)

    #'Entity1' 컬럼에서 filename과 같은 값을 가진 행을 모두 삭제
    csv_dataframe = csv_dataframe[csv_dataframe['Entity1'] != filename]

    #변경된 DataFrame을 다시 CSV 파일로 저장
    csv_dataframe.to_csv(csv_file_path,index=False)


# csv 파일 '인물' 속성에 대한 속성값 변경
def replace_names_in_csv_pandas(csv_file_path, old_name, new_name):
    # CSV 파일 읽기
    df = pd.read_csv(csv_file_path, encoding='utf-8')
    
    # 데이터프레임 내에서 old_name을 new_name으로 변경
    df.replace(old_name, new_name, inplace=True)
    
    # 변경된 데이터프레임을 CSV 파일로 다시 쓰기
    df.to_csv(csv_file_path, index=False, encoding='utf-8')


# 해당 경로에 csv 파일이 존재하는지 확인하는 함수
def isExitCSV(FOLDER_NAME,csv_file_path):

    #csv_file_path에 파일 없으면
    if not os.path.exists(csv_file_path):
        print(f"파일이 존재하지 않습니다. {csv_file_path}")

        # neo4j 서버에 요청
        isCSVFile = serverConnectionHandler.request_csv_neo4jServer(FOLDER_NAME,csv_file_path) 

        # 요청했는데 없으면 새로 만듦
        # isCSVFile false;
        if not isCSVFile: # neo4j 서버에서 csv 파일을 가져오지 못한다면 

            # 새 파일 생성
            with open(csv_file_path, 'w', newline='') as csv_file:  
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(["Entity1", "Relationship", "Entity2"])  # 헤더 추가
        # isCSVFile ture면 요청하여 받아온 것
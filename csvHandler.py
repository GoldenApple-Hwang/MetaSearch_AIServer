import serverConnectionHandler
import csv
import pandas as pd

# csv 파일에 파일이름 들어간 행 삭제
def delete_csv_file_info(csv_file_path,filename):
    global lock
    with lock:
        #csv 파일을 dataframe으로 불러옴
        csv_dataframe = pd.read_csv(csv_file_path)

        #'Entity1' 컬럼에서 filename과 같은 값을 가진 행을 모두 삭제
        csv_dataframe = csv_dataframe[csv_dataframe['Entity1'] != filename]

        #변경된 DataFrame을 다시 CSV 파일로 저장
        csv_dataframe.to_csv(csv_file_path,index=False)


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
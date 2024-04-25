from flask import Flask, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from io import BytesIO
import base64
from PIL import Image
import pandas as pd
#from image_anaylze import * 
from image_analyze.extract_face import compareFace
from image_analyze.lastGVapiLockVersion import image_analysis
#from image_anaylze import extract_face
#from image_anaylze import lastGVapiLockVersion
#from extract_face import compareFace
#from lastGVapiLockVersion import image_analysis
import csv
import threading
from functools import wraps
from metadata import meta_run
import json
from circle2search import detect_and_draw_objects_in_radius
import requests

app = Flask(__name__)

lock = threading.Lock()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'HEIC'}
def synchronized(lock):
    """데코레이터를 위한 synchronized 함수"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/android/upload_add', methods=['POST'])
#@synchronized(lock)
def upload_image():
    source, endIndicator = request_info(request)
    FOLDER_NAME = source # 만들어야하는 폴더 이름 ex) People
    app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME #현재 폴더 경로

    extract_face_list = [] #추출된 얼굴 이미지 경로를 담는 리스트
    isFaceExit = False #추출된 얼굴 이미지가 있었는지 판단

    #DB이름과 동일한 폴더가 생성되어있는지 확인 필요        
    if not os.path.exists("./"+FOLDER_NAME):
        os.makedirs("./"+FOLDER_NAME)
        print(FOLDER_NAME+"폴더 만듦")


    #CSV폴더가 있는지 확인하고 없으면 CSV폴더 만들어주기 -> 함수로 뽑는 게 좋을 것 같음 
    try:
       csv_directory = os.path.join(app.config['UPLOAD_FOLDER'],"CSV")
       if not os.path.exists(csv_directory):
           os.makedirs(csv_directory) #폴더 생성
           print('CSV 폴더를 생성함')
    except Exception as e:
           print(f'폴더 생성 중 오류가 발생함 : {str(e)}')

    #csv 파일 저장 경로, 파일 이름
    csv_file_path = os.path.join(csv_directory, FOLDER_NAME+".csv")

   #request_csv_neo4jServer(FOLDER_NAME) # neo4j 서버에 csv 파일 요청

    # # 현재 csv_file_path에 해당 csv 파일이 존재하지 않는 경우,
    # if not os.path.exists(csv_file_path):
    #      with lock:  # Lock을 획득하여 해당 블록을 동기화
    #         with open(csv_file_path, 'w', newline='') as csv_file:  # 새 파일 생성
    #             csv_writer = csv.writer(csv_file)
    #             csv_writer.writerow(["Entity1", "Relationship", "Entity2"])  # 헤더 추가
    # else: 
    #     # csv_file_path에 해당 csv 파일이 존재하는 경우

    # neo4j 서버에 csv 파일 요청 및 저장    
    isCSVFile = request_csv_neo4jServer(FOLDER_NAME,csv_file_path) 

    if not isCSVFile: #neo4j 서버에서 csv 파일을 가져오지 못한다면 
        with lock:  # Lock을 획득하여 해당 블록을 동기화
            with open(csv_file_path, 'w', newline='') as csv_file:  # 새 파일 생성
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(["Entity1", "Relationship", "Entity2"])  # 헤더 추가



    if 'addImage' in request.files: # 추가된 이미지에 대한 분석 요청
        #print('image로 뽑힌 것 ')
        print("add에 들어옴")
        file = request.files['addImage']

        if file:
            # 파일이 존재하지 않거나, 허용되지 않는 확장자의 경우
            if file.filename == '' or not allowed_file(file.filename):
                return 'No selected file or invalid file format', 400
            else :
                filename = secure_filename(file.filename)  # 파일 이름 보안 검증

            # db 폴더 내 이미지 저장 폴더 존재 x 경우 폴더 생성 + 해당 폴더에 이미지 저장
            save_path = make_save_path_folder(file,app.config['UPLOAD_FOLDER'], 'gallery', filename)
            print("save_path : "+save_path)

            #메타데이터 분석
            meta_run(filename,save_path,csv_file_path)
            
            # 이미지 분석 코드 호출해야함
            extract_face_list = image_analysis(app.config['UPLOAD_FOLDER'],filename, save_path,csv_file_path)
            print("추출된 이미지 결과 받음")

            if extract_face_list: #추출된 얼굴이 있을 경우, isExit 
                isFaceExit = True


            print("endIndicator는 : ",endIndicator)
            
            # 마지막 요청 웹 서버에 변경된 csv 파일 전송
            if endIndicator == 'true':
                #send_webServer(csv_file_path)
                print("마지막 요청")

            response = make_image_json(extract_face_list,"add",isFaceExit)
            return jsonify(response), 200
                
        else:
            'No file part', 400


@app.route('/android/upload_delete', methods=['POST'])
#@synchronized(lock)
def upload_delete_image():
    
    source, endIndicator = request_info(request)
    FOLDER_NAME = source # 만들어야하는 폴더 이름 ex) People
    app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME #현재 폴더 경로

    extract_face_list = [] #추출된 얼굴 이미지 경로를 담는 리스트
    isFaceExit = False #추출된 얼굴 이미지가 있었는지 판단


    csv_directory = os.path.join(app.config['UPLOAD_FOLDER'],"CSV") # csv 경로 생성
    csv_file_path = os.path.join(csv_directory, FOLDER_NAME+".csv") #csv 파일 전체 경로

    if 'deleteImage' in request.files:
        print("delete에 들어옴")
        file = request.files['deleteImage']

        if file:
            filename = secure_filename(file.filename) # 파일 이름 보안 검증
            print("deleteImage에서의 filename : "+filename)

            # 얼굴 폴더 내에 해당 삭제 이미지 이름이 들어있는 것이 있다면 해당 이미지 삭제하는 코드 작성 필요
            # 만약 있었다면 해당 경로를 얼굴 추출에다가 담아야함 -> 안드로이드에서 해당 경로에 있는 얼굴들을 sqlite에서 삭제필요함
            directory = os.path.join(app.config['UPLOAD_FOLDER'],"faces") #얼굴 이미지가 저장되어있는 폴더

            if not os.path.exists(directory): # faces가 들어있지 않을 수 있으므로, 
                os.makedirs(directory) #폴더 생성

            search_name = os.path.splitext(filename)[0] #추출된 얼굴 이미지에 분석된 이미지의 이름을 추가하기 위한 변수
            print("검색하고자 하는 이미지 이름 : "+search_name)

            # 해당 폴더 내의 모든 파일과 폴더에 대해 반복
            for imageName in os.listdir(directory):
                print("imageName : "+imageName)
                image_path = os.path.join(directory, imageName)
                print("iamge_path :"+image_path)
                if search_name in imageName:
                    extract_face_list.append(imageName) # 안드로이드에게 해당 이름을 가진 이미지를 sqlite에서 없애라고 말해야함
                    #해당 폴더에서 얼굴 사진 삭제 필요
                    # 파일 삭제
                    os.remove(image_path)
                    print(f"Found '{search_name}' in file: {imageName}")
                    break #찾으면 종료함
                    
            # 해당 이름이 들어간 데이터를 csv 파일에서 삭제함
            delete_csv_file_info(csv_file_path,filename) 

            # 웹 서버에게 변경된 csv 파일 전송
            if endIndicator == 'true':
                send_neo4jServer(csv_file_path)
                print("마지막 요청")


            if extract_face_list: #추출된 얼굴이 있을 경우, isExit 
                isFaceExit = True

            response = make_image_json(extract_face_list,"delete",isFaceExit)
            return jsonify(response), 200 #json 응답 전송

        else:
            'No file part', 400

# 삭제 요청: csv 파일에 파일이름 들어간 행 삭제
def delete_csv_file_info(csv_file_path,filename):
    global lock
    with lock:
        #csv 파일을 dataframe으로 불러옴
        csv_dataframe = pd.read_csv(csv_file_path)

        #'Entity1' 컬럼에서 filename과 같은 값을 가진 행을 모두 삭제
        csv_dataframe = csv_dataframe[csv_dataframe['Entity1'] != filename]

        #변경된 DataFrame을 다시 CSV 파일로 저장
        csv_dataframe.to_csv(csv_file_path,index=False)


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
        with open(csv_file_path, 'wb') as file:
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


# 데이터베이스 이미지 요청
@app.route('/android/upload_database', methods=['POST'])
#@synchronized(lock)
def upload_database_image():
    source,endIndicator = request_info(request)

    FOLDER_NAME = source # 만들어야하는 폴더 이름 ex) People
    app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME #현재 폴더 경로

    if 'faceImage' in request.files: #얼굴 이미지 사진이 도착한 경우
        print("database에 들어옴") 
        file = request.files['faceImage']
        if file:  # 파일이 존재하는지 확인
            filename = secure_filename(file.filename)
            # 파일 저장 경로 설정
            save_path = make_save_path_folder(file,app.config['UPLOAD_FOLDER'], "faces", filename)
    
            
            return 'Database image upload 완료', 200 
        else:
            return 'No database image provided', 400
    else:
        return 'No file part', 400
    

#원 그리기 요청
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'searchImage' not in request.files:
        return jsonify({'error': 'No image part'}), 400
    file = request.files['searchImage']
    circles = request.form['circles']
    print(circles)
    source = request.form.get('source') #DB 이름

    FOLDER_NAME = source # 만들어야하는 폴더 이름 ex) People
    app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME #현재 폴더 경로


    #DB이름과 동일한 폴더가 생성되어있는지 확인 필요        
    if not os.path.exists("./"+FOLDER_NAME):
        os.makedirs("./"+FOLDER_NAME)
        print(FOLDER_NAME+"폴더 만듦")


    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and circles:
        filename = secure_filename(file.filename)
        save_path = make_save_path_folder(file,app.config['UPLOAD_FOLDER'], "search", filename)
        #image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        circles_data = json.loads(circles)

        # 원 데이터 처리
        object_names_list = process_circles(app.config['UPLOAD_FOLDER'],save_path,circles_data)

        if object_names_list:#추출된 이름이 있으면 json으로 전달
            return jsonify({'message': 'File and circles uploaded successfully', 'detected_objects': object_names_list}), 200
        else:
            return jsonify({'message': 'File and circles uploaded successfully'}), 200
    return jsonify({'error': 'Invalid request'}), 400


# 요청으로 온 원 데이터 처리
def process_circles(db_link,save_path, circles_data):
    object_names_list = []
    for circle in circles_data:
        print("매개변수로 전달되는 이미지 경로 :"+save_path)
        object = detect_and_draw_objects_in_radius(db_link,save_path, circle['centerX'], circle['centerY'], circle['radius'])
        if object:
            # 반환된 객체 정보 리스트에서 이름만 추출
            print('추출 이름')
            print(object.name)
            if object.name:
                object_names_list.append(object.name)     
    return object_names_list

    
# 파일 이름에서 확장자를 추출하고, 소문자로 변환하는 함수
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def request_info(request): #request 제공하는 info 추출
    source = request.form.get('source') #DB 이름
    endIndicator = request.form.get('endIndicator')

    return source, endIndicator


# db폴더 경로 내 gallery 폴더 생성 + 해당 이미지 저장    
def make_save_path_folder(file,folderPath, folderName, filename):
      save_path = os.path.join(folderPath,folderName , filename)
      # 필요한 경우 폴더 생성
      os.makedirs(os.path.dirname(save_path), exist_ok=True)

      file.save(save_path) #파일 저장
      return save_path #저장 위치 반환


def make_image_json(image_lists,actionType,isFaceExit): 
    #actionType:
    # add이면 이미지 경로가 저장되어있고, delete이면 바이트 배열이 필요없음 -> None 저장
    # isExit: 
    # 추출된 얼굴이 존재하는지에 따라서 json파일을 다르게 보내야하므로 이를 구분하는 변수이다. true와 false로 구분된다.
    images_response = [] 
    if not image_lists: #추출된 얼굴이 없는 경우
        images_response.append({
               'isFaceExit' : isFaceExit
           })
        response = {
            'images': images_response
        }
    else: # 추출된 얼굴이 있는 경우
        for image_path in image_lists:
            if actionType == 'add':
                 with open(image_path, "rb") as img_file:
                     image_bytes = img_file.read()
                     encoded_image = base64.b64encode(image_bytes).decode('utf-8')  # 바이트 배열을 base64로 인코딩하여 문자열로 변환
            else:
                 encoded_image = None
            images_response.append({
                'imageName': os.path.basename(image_path),
                'imageBytes': encoded_image,
                'isFaceExit' : isFaceExit
            })

        response = {
            'images': images_response
        }

    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

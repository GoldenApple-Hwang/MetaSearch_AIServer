from flask import Flask, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from io import BytesIO
import base64
from PIL import Image
import pandas as pd 
from image_analyze.GVapi import image_analysis
from metadata.extract_metadata import meta_run
from image_analyze.ntrans import translate_csv
import serverConnectionHandler
import csvHandler
import csv
import threading
from functools import wraps
import json
from image_analyze.focusingsearch import detect_and_draw_objects_in_radius
import requests
import shutil
import re
import time

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

@app.route('/android/upload_finish', methods=['POST'])
def upload_finish():
    print("마지막 요청 들어옴")

    # 응답을 위한 배열
    images_response = []

    isFaceExit = False

    # 폴더 이름 받아옴 # 데이터베이스 row 개수 받아옴
    dbName = request.form.get('dbName')
    rowCount = request.form.get('rowCount')
    isAdd = request.form.get('isAdd')

    #print("rowCount = "+rowCount)
    rowCount = int(rowCount)
    FOLDER_NAME = dbName # 만들어야하는 폴더 이름 ex) People
    app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME #현재 폴더 경로

    # newFaces 폴더 경로
    newFaces_directory = os.path.join(app.config['UPLOAD_FOLDER'],"newFaces")
    print(f'마지막 요청에서의 newFaces 폴더 경로 :${newFaces_directory}')

    # csv 폴더 경로
    csv_directory = os.path.join(app.config['UPLOAD_FOLDER'],"CSV")

    # csv 파일 경로
    csv_file_path = os.path.join(csv_directory, FOLDER_NAME+".csv")

    # faces 폴더 경로
    faces_directory = os.path.join(app.config['UPLOAD_FOLDER'],"faces")

    # temp 폴더 경로
    temp_directory = os.path.join(app.config['UPLOAD_FOLDER'],"temp")

    # gallery 폴더 경로
    gallery_directory = os.path.join(app.config['UPLOAD_FOLDER'],"gallery")

    # 해당 경로의 파일이 존재하는지 파악 / 삭제 이미지 요청만 있다면 해당 폴더와는 관련이 없음
    if os.path.exists(newFaces_directory):
        isFaceExit = True
        # 내부에 파일을 순회하며 csv 작성
        for faceImage in os.listdir(newFaces_directory):
            rowCount+=1 # 하나 증가
            # csv에서 해당 faceImage 이름으로 된 곳을 다 변경함
            newFaceName = f'인물{rowCount}'

            # #  (newfaces 폴더 내에서) 파일 이름 변경을 위해 전체 경로 지정 #faceImage는 old 이름 
            newFaces_filePath = os.path.join(newFaces_directory, faceImage)
            # newFaces_newFilePath = os.path.join(newFaces_directory, f'인물{rowCount}')

            # (faces 폴더 내에서) 파일 이름 변경을 위해 전체 경로 지정
            faces_oldFilePath = os.path.join(faces_directory,faceImage)
            #faces_newFilePath = os.path.join(faces_directory,f'인물{rowCount}.jpg') #원래 '인물1'이었다면 '인물1.jpg'로 저장하도록 변경함
            faces_newFilePath = os.path.join(faces_directory,f'person{rowCount}.jpg') #원래 '인물1'이었다면 'person1.jpg'로 저장하도록 변경함

            # 파일 이름 변경
            os.rename(faces_oldFilePath, faces_newFilePath)

            base_face_name = faceImage
            # 파일 이름에서 확장자를 제거한 부분 => face_1
            base_face_name = os.path.splitext(base_face_name)[0]

            # csv에서 해당 이름 변경
            csvHandler.replace_names_in_csv_pandas(csv_file_path,base_face_name,newFaceName)

             # 해당 얼굴 이미지 파일 읽음
            with open(newFaces_filePath, "rb") as img_file:
                    image_bytes = img_file.read()
                    encoded_image = base64.b64encode(image_bytes).decode('utf-8')  # 바이트 배열을 base64로 인코딩하여 문자열로 변환

            images_response.append({
                # 이미지 이름
                'imageName': newFaceName, # ex) 클라이언트에게 인물1이라는 이름을 보냄

                # 이미지 바이트 or None
                'imageBytes': encoded_image,

                # 얼굴 추출 여부
                'isFaceExit' : isFaceExit
            })
    # 최종 csv 파일 번역
   # if isAdd == "true":
    translate_csv(csv_file_path) 

    # 최종 csv파일 neo4j 전송
    serverConnectionHandler.send_neo4jServer(csv_file_path)

    # 사용자의 폴더 내 csv, faces, temp, gallery 모두 비움
    
    # csv 폴더 내 파일 삭제
    delete_files(csv_directory)

    # temp 폴더 내 파일 삭제
    delete_files(temp_directory)

    # gallery 폴더 내 파일 삭제
    delete_files(gallery_directory)

    delete_files(newFaces_directory)
    print("newFaces 폴더 삭제함")


    # newFaces 폴더를 삭제
    if not isFaceExit:
        # 추출된 얼굴이 없을 경우
        images_response.append({
                # 얼굴 추출 여부
                'isFaceExit' : isFaceExit
            })
        
    # 응답 메시지 작성
    response = {
            'images': images_response
        }

    return jsonify(response), 200

# first 요청으로 face DB가 존재하면 삭제되도록 함
# @app.route('/android/upload_first', methods=['POST'])
# def upload_first():
#     dbName = request.form.get('dbName')

#     # 만들어야하는 폴더 이름 ex) People
#     FOLDER_NAME = dbName

#     #현재 폴더 경로
#     app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME 

#     faces_db_path = app.config['UPLOAD_FOLDER']+"/faces"

#     if os.path.exists(faces_db_path):
#         shutil.rmtree(faces_db_path)
        
#         print("first upload _ faces 폴더 삭제함")

#     return 'complete first request',200

# 사용자가 인물을 삭제할 시에 서버에서도 faceDB 내에 존재하는 얼굴을 삭제하도록 함
@app.route('/android/delete_person',methods=['POST'])
def delete_person():
    dbName = request.form.get('dbName') # DB 이름
    personName = request.form.get('deletePerson') # 삭제된 인물 이름

    # DB 폴더 이름
    FOLDER_NAME = dbName

    #현재 폴더 경로
    app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME

    number = re.sub(r'\D', '', personName) # 숫자 추출
    personName = f"person{number}" # 인물숫자 -> person숫자

    faces_db_path = app.config['UPLOAD_FOLDER']+"/faces"

    # 만약 해당 DB 폴더에 faces 폴더가 존재한다면
    if os.path.exists(faces_db_path):
        # 폴더 내 모든 파일 및 디렉터리 순회
        for filename in os.listdir(faces_db_path):
            file_path = os.path.join(faces_db_path, filename)  # 파일의 전체 경로
            if os.path.isfile(file_path):  # 파일인지 확인
                # 파일 이름 비교
                # if 파일이름 person2.jpg
                baseName = os.path.splitext(filename)[0] # person2
                # 만약 삭제된 이름과 파일이 이름이 동알하다면 해당 파일 삭제함
                if personName == baseName:
                     os.remove(file_path)  # 파일 삭제
                     print(f"sent person is {personName}, deletePerson is {baseName}")

                     return "complete delete person", 200 
                
    return "No exsit personName", 400 

                

# 이미지 추가 요청 
@app.route('/android/upload_add', methods=['POST'])
def upload_image():
    dbName = request.form.get('dbName')
    FOLDER_NAME = dbName # 만들어야하는 폴더 이름 ex) People
    app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME #현재 폴더 경로

    # DB이름과 동일한 폴더가 생성되어있는지 확인 필요        
    if not os.path.exists("./"+FOLDER_NAME):
        os.makedirs("./"+FOLDER_NAME)
        print(FOLDER_NAME+"폴더 만듦")

    # CSV폴더가 있는지 확인하고 없으면 CSV폴더 만들어주기 -> 함수로 뽑는 게 좋을 것 같음 
    try:
       csv_directory = os.path.join(app.config['UPLOAD_FOLDER'],"CSV")
       # csv 폴더가 존재하지 않는다면
       if not os.path.exists(csv_directory):
           #폴더 생성
           os.makedirs(csv_directory) 
           print('CSV 폴더를 생성함')
    except Exception as e:
           print(f'폴더 생성 중 오류가 발생함 : {str(e)}')
        
    #csv 파일 저장 경로, 파일 이름
    csv_file_path = os.path.join(csv_directory, FOLDER_NAME+".csv")

    # csv 파일이 csv_file_path에 존재하는지 확인하고, 없으면 neo4j에 요청, 요청 시 false이면 서버에서 새로 생성
    with lock:
        csvHandler.isExitCSV(FOLDER_NAME,csv_file_path)

    # 추가된 이미지에 대한 분석 요청
    if 'addImage' in request.files: 

        print("add에 들어옴")

        file = request.files['addImage']

        if file:
            # 파일이 존재하지 않거나, 허용되지 않는 확장자의 경우
            if file.filename == '' or not allowed_file(file.filename):
                return 'No selected file or invalid file format', 400
            else :
                filename = file.filename  # 파일 이름 보안 검증

            # db 폴더 내 이미지 저장 폴더 존재 x 경우 폴더 생성 + 해당 폴더에 이미지 저장
            save_path = make_save_path_folder(file,app.config['UPLOAD_FOLDER'], 'gallery', filename)
            print("save_path : "+save_path)

            #메타데이터 추출
            meta_run(filename,save_path,csv_file_path)
            
            # 이미지 분석 코드 호출(google vision, deepface)
            #extract_face_list = image_analysis(app.config['UPLOAD_FOLDER'],filename, save_path,csv_file_path)
            image_analysis(app.config['UPLOAD_FOLDER'],filename, save_path,csv_file_path)
            print("추출된 이미지 결과 받음")
            return 'complete uplaod add image', 200
                
        else:
            return 'No file part', 400


@app.route('/android/upload_delete', methods=['POST'])
#@synchronized(lock)
def upload_delete_image():
    dbName = request.form.get('dbName')

    FOLDER_NAME = dbName # 만들어야하는 폴더 이름 ex) People
    app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME #현재 폴더 경로

    # csv 경로 생성
    csv_directory = os.path.join(app.config['UPLOAD_FOLDER'],"CSV") 

    #csv 파일 전체 경로
    csv_file_path = os.path.join(csv_directory, FOLDER_NAME+".csv") 

    # csv 파일 경로에 파일 존재하는지 확인함, 없으면 neo4j 서버에 요청, 요청에서 false가 오면 서버에서 새로 만듦
    with lock:
        csvHandler.isExitCSV(FOLDER_NAME,csv_file_path)

    if 'deleteImage' in request.files:
        print("delete에 들어옴")
        file = request.files['deleteImage']

        if file:
            filename = file.filename
            # 파일 경로에서 파일 이름만 추출함
            filename = os.path.basename(filename)

            with lock:
                csvHandler.delete_csv_file_info(csv_file_path,filename) 

            return "complete delete image", 200 

        else:
            'No file part', 404


# 데이터베이스 이미지 요청
# @app.route('/android/upload_database', methods=['POST'])
# #@synchronized(lock)
# def upload_database_image():
#     dbName = request.form.get('dbName')

#     # 만들어야하는 폴더 이름 ex) People
#     FOLDER_NAME = dbName

#     #현재 폴더 경로
#     app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME 

#     #얼굴 이미지 사진이 도착한 경우
#     if 'faceImage' in request.files: 
#         print("database에 들어옴") 

#         file = request.files['faceImage']

#         # 파일이 존재하는지 확인
#         if file: 
#             filename = file.filename
#             # 인물1로 들어옴 -> person1.jpg로 변경해야함
#             # 숫자만 출력함
            
    
#             # 파일 저장 경로 설정
#             save_path = make_save_path_folder(file,app.config['UPLOAD_FOLDER'], "faces", filename)
     
#             return 'Database image upload 완료', 200 
#         else:
#             return 'No database image provided', 400
#     else:
#         return 'No file part', 404
    

# 원 검색 요청
@app.route('/android/circle_search', methods=['POST'])
def upload_file():
    if 'searchImage' not in request.files:
        return jsonify({'error': 'No image part'}), 400
    
    # 클라이언트에게 받은 이미지 파일
    file = request.files['searchImage']

    # 클라이언트에게 받은 원 정보
    circles = request.form['circles']
    print(circles)  

    #DB 이름
    dbName = request.form.get('dbName')

    # 만들어야하는 폴더 이름 ex) People 
    FOLDER_NAME = dbName

    #현재 폴더 경로
    app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME 


    #DB이름과 동일한 폴더가 생성되어있지 않다면
    if not os.path.exists("./"+FOLDER_NAME):

        # 해당 경로에 파일 생성
        os.makedirs("./"+FOLDER_NAME)
        print(FOLDER_NAME+"폴더 만듦")

    # 파일이 이름이 없다면 400 에러 처리
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # 파일과 원 정보가 존재할 경우
    if file and circles:

        # 이미지 파일 이름
        filename = secure_filename(file.filename)

        # 이미지 파일이 저장된 경로
        save_path = make_save_path_folder(file,app.config['UPLOAD_FOLDER'], "search", filename)
 
        # 원 정보 추출
        circles_data = json.loads(circles)

        # 원 데이터 처리
        object_names_list = process_circles(app.config['UPLOAD_FOLDER'],save_path,circles_data)

        #추출된 이름이 있으면 json으로 전달
        if object_names_list:
            return jsonify({'message': 'File and circles uploaded successfully', 'detected_objects': object_names_list}), 200
        else:
            return jsonify({'message': 'File and circles uploaded successfully'}), 200
    return jsonify({'error': 'Invalid request'}), 400


# 요청으로 온 원 데이터 처리
def process_circles(db_link,save_path, circles_data):
    object_names_list = []

    # 원 정보 순회
    for circle in circles_data:
        print("매개변수로 전달되는 이미지 경로 :"+save_path)

        # 원 내부 객체 추출 함수 호출
        object = detect_and_draw_objects_in_radius(db_link,save_path, circle['centerX'], circle['centerY'], circle['radius'])
        if object:
            # 반환된 객체 정보 리스트에서 이름만 추출
            print('추출 이름')
            print(object.name)

            # 추출된 객체 이름 있을 경우
            if object.name:

                # 객체 이름 리스트에 담음
                object_names_list.append(object.name)                  
        else:
            object_names_list.append("")  

    # 추출된 객체 이름이 담겨진 리스트 반환  
    return object_names_list
   

# 파일 이름에서 확장자를 추출하고, 소문자로 변환하는 함수
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# db폴더 경로 내 gallery 폴더 생성 + 해당 이미지 저장    
def make_save_path_folder(file,folderPath, folderName,filename ):
      if folderName == "faces": # 얼굴에 저장할 사진이라면
          number = re.sub(r'\D', '', filename)
          save_path = os.path.join(folderPath,folderName , "person"+number+".jpg") #person1.jpg 로 이름 변경하여 faces에 저장
      else:
          save_path = os.path.join(folderPath,folderName , filename) #person1.jpg 로 이름 변경하여 faces에 저장

      # 필요한 경우 폴더 생성
      os.makedirs(os.path.dirname(save_path), exist_ok=True)

        #파일 저장
      file.save(save_path) 

      #저장 위치 반환
      return save_path 

# 디렉토리 내 파일 다 삭제
def delete_files(folder_directory):

    # 해당 경로에 폴더가 존재한다면
    if os.path.exists(folder_directory):

        # 파일 순회
        for filename in os.listdir(folder_directory):

            # 파일 경로
            file_path = os.path.join(folder_directory, filename)

            # 해당 경로가 파일인지 확인합니다.
            if os.path.isfile(file_path) or os.path.islink(file_path):

                # 파일을 삭제
                os.unlink(file_path)  

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

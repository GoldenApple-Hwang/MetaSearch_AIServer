from flask import Flask, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from io import BytesIO
import base64
from PIL import Image
import pandas as pd 
from image_analyze.extract_face import compareFace
from image_analyze.GVapi import image_analysis
from metadata.extract_metadata import meta_run
from image_analyze.ntrans import translate_csv
import serverConnectionHandler
import csvHandler
import csv
import threading
from functools import wraps
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


@app.route('/android/upload_finish', methods=['POST'])
def upload_finish():
    print("마지막 요청 들어옴")

    # 응답을 위한 배열
    images_response = []

    isFaceExit = False

    # 폴더 이름 받아옴 # 데이터베이스 row 개수 받아옴
    dbName,rowCount = request_info(request)
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

            #  (newfaces 폴더 내에서) 파일 이름 변경을 위해 전체 경로 지정 #faceImage는 old 이름 
            newFaces_oldFilePath = os.path.join(newFaces_directory, faceImage)
            newFaces_newFilePath = os.path.join(newFaces_directory, f'인물{rowCount}')

            # (faces 폴더 내에서) 파일 이름 변경을 위해 전체 경로 지정
            faces_oldFilePath = os.path.join(faces_directory,faceImage)
            faces_newFilePath = os.path.join(faces_directory,f'인물{rowCount}')
            
            # 파일 이름 변경
            os.rename(newFaces_oldFilePath, newFaces_newFilePath)

            # 파일 이름 변경
            os.rename(faces_oldFilePath, faces_newFilePath)

            base_face_name = faceImage
            # 파일 이름에서 확장자를 제거한 부분 => face_1
            base_face_name = os.path.splitext(base_face_name)[0]

            # csv에서 해당 이름 변경
            csvHandler.replace_names_in_csv_pandas(csv_file_path,base_face_name,newFaceName)

             # 해당 얼굴 이미지 파일 읽음
            with open(newFaces_newFilePath, "rb") as img_file:
                    image_bytes = img_file.read()
                    encoded_image = base64.b64encode(image_bytes).decode('utf-8')  # 바이트 배열을 base64로 인코딩하여 문자열로 변환

            images_response.append({
                # 이미지 이름
                'imageName': os.path.basename(newFaceName),

                # 이미지 바이트 or None
                'imageBytes': encoded_image,

                # 얼굴 추출 여부
                'isFaceExit' : isFaceExit
            })
    # 최종 csv 파일 번역
    translate_csv(csv_file_path) 

    # 최종 csv파일 neo4j 전송
    serverConnectionHandler.send_neo4jServer(csv_file_path)

    # 사용자의 폴더 내 csv, faces, temp, gallery 모두 비움
    
    # csv 폴더 내 파일 삭제
    delete_files(csv_directory)

    # faces 폴더 내 파일 다 삭제
    #delete_files(faces_directory)

    # temp 폴더 내 파일 삭제
    delete_files(temp_directory)

    # gallery 폴더 내 파일 삭제
    delete_files(gallery_directory)

    # newFaces 폴더를 삭제
    if isFaceExit:
        print("newFaces 폴더 삭제")
    else: #추출된 얼굴이 없을 경우
        images_response.append({
                # 얼굴 추출 여부
                'isFaceExit' : isFaceExit
            })
        
    # 응답 메시지 작성
    response = {
            'images': images_response
        }

    
    return jsonify(response), 200



# 이미지 추가 요청 
@app.route('/android/upload_add', methods=['POST'])
def upload_image():
    source = request_info(request)
    FOLDER_NAME = source # 만들어야하는 폴더 이름 ex) People
    app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME #현재 폴더 경로

    extract_face_list = [] #추출된 얼굴 이미지 경로를 담는 리스트
    isFaceExit = False #추출된 얼굴 이미지가 있었는지 판단

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
            extract_face_list = image_analysis(app.config['UPLOAD_FOLDER'],filename, save_path,csv_file_path)
            print("추출된 이미지 결과 받음")

            #추출된 얼굴이 있을 경우, isExit
            if extract_face_list:  
                isFaceExit = True

            # json 작성
            response = make_image_json(extract_face_list,"add",isFaceExit)
            return jsonify(response), 200
                
        else:
            'No file part', 400


@app.route('/android/upload_delete', methods=['POST'])
#@synchronized(lock)
def upload_delete_image():
    source = request_info(request)
    FOLDER_NAME = source # 만들어야하는 폴더 이름 ex) People
    app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME #현재 폴더 경로

    #추출된 얼굴 이미지 경로를 담는 리스트
    extract_face_list = [] 

    #추출된 얼굴 이미지가 있었는지 판단
    isFaceExit = False 

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
            filename = file.filename # 파일 이름 보안 검증
            print("deleteImage에서의 filename : "+filename)

            #얼굴 이미지가 저장되어있는 폴더
            directory = os.path.join(app.config['UPLOAD_FOLDER'],"faces") 

            # faces 폴더가 없는 경우
            if not os.path.exists(directory): 

                #폴더 생성
                os.makedirs(directory)

            #추출된 얼굴 이미지에 분석된 이미지의 이름을 추가하기 위한 변수
            # 파일 이름에서 확장자를 제거한 부분 => face_1      
            search_name = os.path.basename(search_name)
            search_name = os.path.splitext(search_name)[0]
            print("검색하고자 하는 이미지 이름 : "+search_name)

            # faces 폴더 내의 모든 파일 순회
            for imageName in os.listdir(directory):
                print("imageName : "+imageName)

                # 찾고자 하는 이미지의 경로
                image_path = os.path.join(directory, imageName)
                print("iamge_path :"+image_path)

                # 이미지 이름에 삭제된 이미지 이름이 포함되어있다면
                if search_name in imageName:

                    # 추출 얼굴 리스트에 삭제해야하는 얼굴 이미지 이름 추가
                    extract_face_list.append(imageName) 
                    
                    # 이미지 삭제
                    os.remove(image_path)
                    print(f"Found '{search_name}' in file: {imageName}")

                    #찾으면 종료함
                    break 
                    
            # 해당 이름이 들어간 데이터를 csv 파일에서 삭제함
            with lock:
                csvHandler.delete_csv_file_info(csv_file_path,filename) 

            #추출된 얼굴이 있을 경우, isExit = True
            if extract_face_list:  
                isFaceExit = True

            # 응답을 위한 json 작성
            response = make_image_json(extract_face_list,"delete",isFaceExit)

            #json 응답 전송
            return jsonify(response), 200 

        else:
            'No file part', 400


# 데이터베이스 이미지 요청
@app.route('/android/upload_database', methods=['POST'])
#@synchronized(lock)
def upload_database_image():
    source = request_info(request)

    # 만들어야하는 폴더 이름 ex) People
    FOLDER_NAME = source 

    #현재 폴더 경로
    app.config['UPLOAD_FOLDER'] = "./"+FOLDER_NAME 

    #얼굴 이미지 사진이 도착한 경우
    if 'faceImage' in request.files: 
        print("database에 들어옴") 

        file = request.files['faceImage']

        # 파일이 존재하는지 확인
        if file: 
            filename = file.filename

            # 파일 저장 경로 설정
            save_path = make_save_path_folder(file,app.config['UPLOAD_FOLDER'], "faces", filename)
     
            return 'Database image upload 완료', 200 
        else:
            return 'No database image provided', 400
    else:
        return 'No file part', 400
    

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
    source = request_info(request)

    # 만들어야하는 폴더 이름 ex) People 
    FOLDER_NAME = source 

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

    # 추출된 객체 이름이 담겨진 리스트 반환  
    return object_names_list

    

# 파일 이름에서 확장자를 추출하고, 소문자로 변환하는 함수
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#request 제공하는 info 추출
def request_info(request): 

    #DB 이름
    source = request.form.get('source') 
    return source


# db폴더 경로 내 gallery 폴더 생성 + 해당 이미지 저장    
def make_save_path_folder(file,folderPath, folderName, filename):
      save_path = os.path.join(folderPath,folderName , filename)

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

# json 작성 함수             
def make_image_json(image_lists,actionType,isFaceExit): 
    #actionType: add이면 이미지 경로가 저장되어있고, delete이면 바이트 배열이 필요없음 -> None 저장
    # isExit: 추출된 얼굴이 존재하는지에 따라서 json파일을 다르게 보내야하므로 이를 구분하는 변수이다. true와 false로 구분된다.

    # 이미지 관련 응답 작성 담는 리스트
    images_response = [] 

    #추출된 얼굴이 없는 경우
    if not image_lists: 
        images_response.append({
                # 추출된 얼굴이 없으므로 false가 담김
               'isFaceExit' : isFaceExit
           })
        
        # 응답 response 생성
        response = {
            'images': images_response
        }

    else: # 추출된 얼굴이 있는 경우

        # 추출된 얼굴 리스트 순회
        for image_path in image_lists:

            # 추가 요청이었다면
            if actionType == 'add':
                 
                 # 해당 이미지 파일 읽음
                 with open(image_path, "rb") as img_file:
                     image_bytes = img_file.read()
                     encoded_image = base64.b64encode(image_bytes).decode('utf-8')  # 바이트 배열을 base64로 인코딩하여 문자열로 변환
            else:
                 # 보내져야하는 이미지가 없다
                 encoded_image = None
                
            images_response.append({
                # 이미지 이름
                'imageName': os.path.basename(image_path),

                # 이미지 바이트 or None
                'imageBytes': encoded_image,

                # 얼굴 추출 여부
                'isFaceExit' : isFaceExit
            })

        # 응답 response 생성
        response = {
            'images': images_response
        }

    # 응답 response 반환
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

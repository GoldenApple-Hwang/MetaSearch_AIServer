import csv
import cv2
import os
import shutil  # 이미지 경로 변경을 위해 사용
from deepface import DeepFace
import threading
import re
import uuid

# csv 파일 lock
lock = threading.Lock()

# 딥러닝 기반의 얼굴 검출 모델 로드
face_detector_model = "/home/hstack/AiServer/image_analyze/deploy.prototxt"
face_detector_weights = "/home/hstack/AiServer/image_analyze/res10_300x300_ssd_iter_140000_fp16.caffemodel"
face_net = cv2.dnn.readNetFromCaffe(face_detector_model, face_detector_weights)

# 얼굴 분석 csv 파일 작성
def compareFace(db_link, app_image_link, db_image_link, csv_link, face_info): 
    print("받은 얼굴 영역 : ")
    print(face_info)

    # csv 파일에 작성해야하는 인물 리스트
    extract_person_name_list = []

    # 해당 인물의 성별이 이미 존재하는지 확인하는 딕셔너리
    extract_person_sex_list = []

    # 하나의 이미지에서 겹치지 않도록 감정을 추출함
    extract_person_emotion_list = [] 

    # 표정 분석 해야하는 얼굴 이미지 리스트
    expression_faces = []

    #추출할 인물에 대한 변수
    extract_person = None

    image_name = app_image_link  # 분석되고 있는 이미지 이름
    image_name_exclude_extension = os.path.splitext(app_image_link)[0]  #추출된 얼굴 이미지에 분석된 이미지의 이름을 추가하기 위한 변수
    # 만약 사진 이름에 한국어가 있다면 UUID로 대체하여 사용하도록 한다.
    image_name_exclude_extension = get_processed_image_name(image_name_exclude_extension)

    print("CompareFace에 들어옴")

    # 비교할 얼굴 이미지가 존재하는 폴더
    face_db_path = os.path.join(db_link, 'faces')

    # 새로 추출한 얼굴 이미지 저장하는 폴더
    new_face_db_path = os.path.join(db_link, 'newFaces')

    # 인식된 이미지 폴더
    temp_db_path = os.path.join(db_link, 'temp')

    # face 폴더가 없는지 확인 + face_db_path가 비어있는지 확인 필요
    if not os.path.exists(face_db_path):
        os.makedirs(face_db_path, exist_ok=True)
        print("face 폴더 만듦")

    if not os.path.exists(new_face_db_path):
        os.makedirs(new_face_db_path, exist_ok=True)
        print("newFaces 폴더 만듦")
    
    if not os.path.exists(temp_db_path):
        os.makedirs(temp_db_path, exist_ok=True)
        print("temp 폴더 만듦")

    compare_img_path = db_image_link  # 서버로부터 저장된 이미지
    img = cv2.imread(compare_img_path)  # 분석할 이미지 읽어드리기
    
    if img is None:
        print("이미지를 읽어오지 못했습니다.")
        return
    
    # 인식된 얼굴의 개수만큼 반복
    index = 0
    for face in face_info:
        index += 1
        bounding_poly = face['bounding_poly']
        vertices = bounding_poly  # vertices는 이미 추출된 리스트 형태
        
        # Get x, y coordinates of vertices
        x_coordinates = [vertex['x'] for vertex in vertices]
        y_coordinates = [vertex['y'] for vertex in vertices]

        # Calculate left, right, top, bottom
        left = min(x_coordinates)
        right = max(x_coordinates)
        top = min(y_coordinates)
        bottom = max(y_coordinates)

        # Crop the image
        cropped = img[top:bottom, left:right]

        # 얼굴이 맞는지 확인 (DNN 사용)
        if cropped.size == 0:
            print("잘못된 얼굴 영역입니다.")
            continue
        
        blob = cv2.dnn.blobFromImage(cropped, 1.0, (300, 300), [104, 117, 123], False, False)
        face_net.setInput(blob)
        detections = face_net.forward()
        h, w = cropped.shape[:2]
        face_detected = False

        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:  # 신뢰도가 50% 이상인 경우
                face_detected = True
                break

        if not face_detected:
            print("자른 이미지에서 얼굴을 찾지 못했습니다.")
            continue  # 얼굴이 아니면 다음 얼굴로 넘어감

        # temp 폴더에 임시 저장
        face_path = os.path.join(temp_db_path, f'face_{image_name_exclude_extension}_{index}.jpg')

        # 해당 face_path에 이미지 저장
        if cropped.size > 0:
            cv2.imwrite(face_path, cropped)  # temp 경로에 자른 이미지 저장
        else:
            print("비어 있는 이미지는 저장하지 않습니다.") 
        
        # 자른 얼굴 얼굴 비교 시작 
        try:
            files = os.listdir(face_db_path)

            # faces 폴더 내에 아무것도 존재하지 않을 경우
            if len(files) == 0:
                #faces 폴더
                new_path = os.path.join(face_db_path, f'face_{image_name_exclude_extension}_{index}.jpg')
                #temp 폴더에 있던 것을 faces 폴더로 이동
                shutil.move(face_path, new_path)
                #faces 폴더 경로
                face_path = new_path
                #newFaces 폴더 경로
                new_face_path = os.path.join(new_face_db_path, f'face_{image_name_exclude_extension}_{index}.jpg')
                # faces 폴더 경로에 있는 것을 newFaces 폴더 경로로 복사함
                shutil.copyfile(face_path, new_face_path)
                print("newFaces 폴더에도 저장함")
                # 표정 분석을 위해 faces 폴더 경로를 추가함
                expression_faces.append(face_path)
                # 추출한 이름은 faces 폴더 상의 경로
                extract_person = face_path
                print("처음으로 뽑은 사람 이름 : " + extract_person)
            else:
                print("faces 폴더 비어있지 않음")
                face_result = DeepFace.find(img_path=face_path, db_path=face_db_path, model_name='Facenet512', enforce_detection=False)
                print("얼굴 분석 시작")
                if (len(face_result) == 0 or face_result[0].empty):
                    print("얼굴을 찾지 못했습니다.")
                    # faces 폴더 경로
                    new_path = os.path.join(face_db_path, f'face_{image_name_exclude_extension}_{index}.jpg')
                    # temp 폴더 내에 있는 것을 faces 폴더로 이동시킴
                    shutil.move(face_path, new_path)
                    #face_path는 faces 폴더 내의 경로
                    face_path = new_path
                    #newFaces 폴더 상의 경로
                    new_face_path = os.path.join(new_face_db_path, f'face_{image_name_exclude_extension}_{index}.jpg')
                    # faces 폴더 상의 데이터를 newFaces 폴더로 이동시킴
                    shutil.copyfile(face_path, new_face_path)
                    print("newFaces 폴더에도 저장함")
                    # 표정 분석을 위해 faces 폴더 경로를 추가함
                    expression_faces.append(face_path)
                    # 추출한 사람으로 faces 폴더 경로를 설정함
                    extract_person = face_path
                    print("뽑은 사람 이름 : " + extract_person)
                else:
                    print("얼굴을 찾았습니다.")
                    # temp에서 뽑아낸 얼굴을 표정 분석하기 위해 넣음
                    expression_faces.append(face_path)
                    # 결과로 나온 것의 faces 폴더 경로를 추출함
                    extract_person = face_result[0]['identity'][0]
                    print("뽑은 사람 이름 : " + extract_person)             
                
            # 추출한 사람이 None이 아니라면
            if extract_person != None: #얼굴 이미지 경로
                print("extract_person 추출함")
                personName = extract_person #현재는 경로로 되어있음
                personName  = os.path.basename(personName) #face_heafg_2.jpg
                personName = os.path.splitext(personName)[0] #face_hger_2
                if "person" in personName: # 뽑은 이미지 이름에 person이 들어있다면 
                    number = re.sub(r'\D', '', personName) # 숫자 추출
                    personName = f"인물{number}" #person 이름을 인물+number로 표현함
                write_csv(csv_link, image_name, '인물', personName) # csv 파일에 추출한 인물 이름 작성함
                #extract_person_name_list.append(extract_person)

        except ValueError as E:
            print("deepface에서 얼굴 분석 못 함")
 
    if expression_faces:
        for expression_face in expression_faces:
            compare_expression_Face(csv_link, expression_face, image_name, extract_person_emotion_list, extract_person_sex_list)

def compare_expression_Face(csv_link, expression_face, image_name, extract_person_emotion_list, extract_person_sex_list):
    extract_emotion = '' 
    extract_gender = ''
    try:
        emotion_result = DeepFace.analyze(img_path=expression_face,
                            actions=['emotion', 'gender', 'race'],
                            detector_backend='retinaface')  # 얼굴 표정 분석

        print("emotion_result : ")
        print(emotion_result)

        for face_data in emotion_result:
            extract_emotion = face_data['dominant_emotion']
            extract_gender = face_data['dominant_gender']

        if extract_gender not in extract_person_sex_list:
            write_csv(csv_link, image_name, '성별', extract_gender)
        if extract_emotion not in extract_person_emotion_list:
            write_csv(csv_link, image_name, '감정', extract_emotion)

    except ValueError as E:
        print("deepface에서 표정 분석 못 함")

def check_if_emotion_exists(emotion_list, key, emotion):
    return any(item[1] == emotion for item in emotion_list if item[0] == key)

def write_csv(csv_link, entity1, relationship, entity2):
    global lock

    csv_file = open(csv_link, 'a', newline='')
    csv_writer = csv.writer(csv_file)
   
    with lock:
        Entity1 = entity1
        Relationship = relationship
        Entity2 = change_en_to_kor(entity2)
        csv_writer.writerow([Entity1, Relationship, Entity2])

def change_en_to_kor(en):
    kor = {"neutral" : "보통", "happy": "행복함", "surprise" : "놀람", "angry": "화남", "disgust": "역겨움", "fear": "공포", "sad": "슬픔",  # 감정
           "Woman": "여자", "Man": "남자"  # 성별
           }.get(en, en)  # 만약 이 중에 없는 값이 들어오면 이 값을 반환함
    return kor

# 이미지 이름에 한국말이 포함되어있는지 확인하는 함수
def contains_korean(text):
    # 한국어 문자가 포함되어 있는지 검사하는 정규 표현식
    korean_pattern = re.compile('[\uac00-\ud7a3]')
    return korean_pattern.search(text) is not None #true,false로 반환

# 한국어 이름 대신에 UUID로 변경
def safe_image_name():
    # 파일 이름을 짧은 UUID로 변경 (처음 8자 사용)
    new_name = str(uuid.uuid4())[:8]
    return new_name

def get_processed_image_name(image_name):
    # 이미지 이름에 한국어가 포함되어 있다면 안전한 이름으로 변경
    if contains_korean(image_name):
        print("Image name contains Korean characters. Converting to a safe name.")
        return safe_image_name()
    else:
        # 한국어가 없다면 원래 이름 반환
        return image_name

import csv
import cv2
import os
import shutil # 이미지 경로 변경을 위해 사용
from deepface import DeepFace
import dlib
from datetime import datetime 
import threading
# db_link : 서버 내 유효 DB 경로
# app_image_lick : 앱 내의 이미지 경로
# db_image_link : 서버 내 처리 이미지 링크
# csv_link : csv 파일 경로
# faces_detected : 인식된 얼굴 영역

#얼굴 추출 / #compareFace에서 호출함

# csv 파일 lock
lock = threading.Lock()

# 얼굴 분석 lock
#face_lock = threading.Lock()

#얼굴 분석 csv 파일 작성
def compareFace(db_link,app_image_link,db_image_link,csv_link,faces_detected): 
     # csv 파일에 작성해야하는 인물 리스트
     extract_person_name_list = []

     # 해당 인물의 성별이 이미 존재하는지 확인하는 딕셔너리 -----
     # 하나의 이미지에 성별이 겹치지 않도록 추출해야함
     extract_person_sex_list = []

     # 하나의 이미지에서 겹치지 않도록 감정을 추출함x
     extract_person_emotion_list = [] 

     # 표정 분석 해야하는 얼굴 이미지 리스트
     expression_faces = []

     #추출할 인물에 대한 변수
     extract_person='' 

     #새로 추출된 얼굴들을 저장하는 리스트 #반환되는 리스트
     #extractFaceList = [] 

     image_name = app_image_link # 분석되고 있는 이미지 이름
     image_name_exclude_extension = os.path.splitext(app_image_link)[0] #추출된 얼굴 이미지에 분석된 이미지의 이름을 추가하기 위한 변수
     
     print("CompareFace에 들어옴")
      
     #날짜+시간으로 얼굴 이름 지정 
     current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
 
     # 비교할 얼굴 이미지가 존재하는 폴더
     face_db_path = db_link+'/faces'

     # 새로 추출한 얼굴 이미지 저장하는 폴더
     new_face_db_path = db_link+'/newFaces'

     # 인식된 이미지 폴더
     temp_db_path = db_link+'/temp'

     #face 폴더가 없는지 확인 + face_db_path가 비어있는지 확인 필요 -> 만약 비어있다면 item을 찾을 수 없다는 에러가 뜨면서 얼굴 비교가 불가능해짐
     if not os.path.exists(face_db_path):

        # faces 폴더 생성함
        os.makedirs(face_db_path,exist_ok = True)
        print("face 폴더 만듦")

     if not os.path.exists(new_face_db_path):
         
         # newFaces 폴더 새로 생성함
         os.makedirs(new_face_db_path,exist_ok=True)
         print("newFaces 폴더 만듦")
    
     # temp 폴더가 없는지 확인
     if not os.path.exists(temp_db_path):
         
         # temp 폴더가 없으면 새로 만듦
         os.makedirs(temp_db_path,exist_ok= True)
         print("temp 폴더 만듦")
      
          
     # 서버로부터 저장된 이미지, 방금 Google Vision이 분석 후 face가 인식된 이미지
     compare_img_path = db_image_link 

     # 분석할 이미지 읽어드리기
     img = cv2.imread(compare_img_path) 
    
     # 인식된 얼굴의 개수만큼 반복
     for face in faces_detected:
            # vertices = [(vertex.x,vertex.y) for vertex in face.bounding_poly.vertices]
            # x1,y1 = vertices[0]
            # x2,y2 = vertices[2]

            # cropped = img[y1:y2,x1:x2]

            # #temp 폴더에 임시 저장
            # face_path = temp_db_path+f'/face_{image_name_exclude_extension}_{current_time}.jpg'
            vertices = [(vertex.x, vertex.y) for vertex in face.bounding_poly.vertices]
            x1, y1 = vertices[0]
            x2, y2 = vertices[2]

            # 원래 영역의 너비와 높이 계산
            width = x2 - x1
            height = y2 - y1

            # 0.4배 더 큰 영역 계산
            expand_width = width * 0.4
            expand_height = height * 0.4

            # 확장된 영역의 좌표 계산
            x1_expanded = max(x1 - expand_width // 2, 0) # 이미지 경계를 벗어나지 않도록 함
            y1_expanded = max(y1 - expand_height // 2, 0)
            x2_expanded = min(x2 + expand_width // 2, img.shape[1]) # img.shape[1]은 이미지의 너비
            y2_expanded = min(y2 + expand_height // 2, img.shape[0]) # img.shape[0]은 이미지의 높이

            # 확장된 영역으로 이미지 자르기
            cropped = img[int(y1_expanded):int(y2_expanded), int(x1_expanded):int(x2_expanded)]

            # temp 폴더에 임시 저장
            face_path = temp_db_path + f'/face_{image_name_exclude_extension}_{current_time}.jpg'


            # 해당 face_path에 이미지 저장
            if cropped.size>0:
                cv2.imwrite(face_path,cropped) # temp 경로에 자른 이미지 저장
            else:
                print("비어 있는 이미지는 저장하지 않습니다.") 
            #cv2.imwrite(face_path, cropped) # temp 경로에 자른 이미지 저장

            # 자른 얼굴 얼굴 비교 시작 
            try:    
                    
                    # 해당 faces 폴더가 비어있는지, 아닌지 확인
                    # 만약 비어있다면, 해당 이미지를 분석하지 않고, 그냥 faces 폴더와 newFaces 폴더에 넣고 csv파일에 작성한다.
                    files = os.listdir(face_db_path)

                    # faces 폴더 내에 아무것도 존재하지 않을 경우
                    if len(files) == 0:
                        # faces 폴더로 이동
                        new_path = face_db_path+f'/face_{image_name_exclude_extension}_{current_time}.jpg'
                        
                        # 이미지 파일을 temp에서 faces 다른 폴더로 이동
                        shutil.move(face_path, new_path)

                        face_path = new_path

                        # newFaces 폴더 저장 경로
                        new_face_path = new_face_db_path+f'/face_{image_name_exclude_extension}_{current_time}.jpg'

                        # newFaces 폴더에도 해당 얼굴 이미지 저장
                        shutil.copyfile(face_path, new_face_path)
                        print("newFaces 폴더에도 저장함")

                        expression_faces.append(face_path)

                        extract_person = face_path

                        print("처음으로 뽑은 사람 이름 : "+ extract_person)
                    else:

                        # 얼굴 비교 / 저장된 얼굴 이미지와 얼굴이 저장된 폴더와 비교
                        face_result = DeepFace.find(img_path=face_path, db_path=face_db_path, model_name='ArcFace',enforce_detection=False) 

                        # 만약 얼굴 비교 결과가 없으면 비교된 얼굴이 없다는 것 -> 얼굴 비교 폴더에 새롭게 저장함
                        if (len(face_result)==0 or face_result[0].empty):
                            print("얼굴을 찾지 못했습니다.")

                            # faces 폴더로 이동
                            new_path = face_db_path+f'/face_{image_name_exclude_extension}_{current_time}.jpg'
                            
                            # 이미지 파일을 temp에서 faces 다른 폴더로 이동
                            shutil.move(face_path, new_path)

                            face_path = new_path

                            # newFaces 폴더 저장 경로
                            new_face_path = new_face_db_path+f'/face_{image_name_exclude_extension}_{current_time}.jpg'

                            # newFaces 폴더에도 해당 얼굴 이미지 저장
                            shutil.copyfile(face_path, new_face_path)
                            print("newFaces 폴더에도 저장함")

                            # 분석해야하는 얼굴 리스트에 추가
                            # 해당 이미지는 faces 폴더 내에 존재
                            expression_faces.append(face_path)

                            extract_person = face_path

                            print("뽑은 사람 이름 : "+ extract_person)

                        else: # 찾은 얼굴이 있는 경우
                            print("얼굴을 찾았습니다.")

                            # 표정 분석 해야하는 얼굴 리스트에 추가
                            # temp에 존재하는 얼굴 사진
                            expression_faces.append(face_path)

                            # 찾은 얼굴에 대한 인물을 추출
                            # 여러 개로 찾은 경우, 첫 번째의 얼굴로 결정
                            #result[0]['identity'][0] -> 동일하다고 나온 이미지의 링크 전체를 알려줌 ex) ./faces/...

                            extract_person = face_result[0]['identity'][0] # 사람 이미지 이름
                            
                            print("뽑은 사람 이름 : "+ extract_person)             
                    
                    # test.jpg가 뽑힐 수도 있으므로 조건을 달음
                    if extract_person!= '':
                        # 인물 추출 
                        #os.path.basename(...) -> 사진 이름만 추출함 => face_1.jpg
                        extract_person  = os.path.basename(extract_person)
                        # 파일 이름에서 확장자를 제거한 부분 => face_1
                        extract_person = os.path.splitext(extract_person)[0]
                        
                        # csv에 적을 이름 리스트이므로 중복되지 않게 처리함
                        # 해당 리스트에 존재하지 않는 경우
                        if not (extract_person in extract_person_name_list):

                            # csv 파일에 인물 작성
                            write_csv(csv_link,image_name,'인물',extract_person)

                            # 추출된 얼굴 리스트에 포함
                            extract_person_name_list.append(extract_person)

            # 예외처리
            except ValueError as E:
                print("deepface에서 얼굴 분석 못 함")

     
     # 수정 필요 ( 필요없는 부분들이 있음 이를 수정할 필요가 있음 )
     # 표정 분석해야하는 얼굴 리스트가 비어있지 않는 경우 -> openCV에서 추출한 얼굴이 있는 경우
     if expression_faces:

        # 표정 분석 얼굴 리스트 순회
        for expression_face in expression_faces:
            # 표정 분석 함수 호출
            compare_expression_Face(csv_link,expression_face,image_name,extract_person_emotion_list,extract_person_sex_list)

# 표정 분석 및 csv 파일 작성
def compare_expression_Face(csv_link,expression_face,image_name,extract_person_emotion_list,extract_person_sex_list): #csv 파일 경로, 추출된 사람의 얼굴 이미지 이름, 분석된 사진의 이름
        extract_emotion = '' # 추출한 감정
        extract_gender = '' # 추출한 성별
        try:
            # 해당 얼굴 사진 표정 분석
            emotion_result = DeepFace.analyze(img_path=expression_face,
                                actions=['emotion', 'gender', 'race'],
                                detector_backend='retinaface') # 얼굴 표정 분석

            print("emotion_result : ")
            print(emotion_result)

            # 얼굴에서 뽑힌 감정, 성별, 인종 추출      
            for face_data in emotion_result:
                # 감정 추출
                extract_emotion = face_data['dominant_emotion']

                # 성별 추출
                extract_gender = face_data['dominant_gender']

            # 해당 인물에 대해서 성별을 추출한 적 있는지 확인하는 함수 호출
            # isExist_Sex = check_if_sex_exist(same_face_person_name,extract_person_sex_dict)

            if extract_gender not in extract_person_sex_list: #해당 성별이 이미지에서 추출된 적이 없으면 csv에 추출함
                write_csv(csv_link,image_name,'성별',extract_gender)
            if extract_emotion not in extract_person_emotion_list: #해당 감정이 이미지에서 추출된 적이 없으면 csv에 추출함
                write_csv(csv_link,image_name,'감정',extract_emotion)

        # 예외처리
        except ValueError as E:
            print("deepface에서 표정 분석 못 함")


# 해당 인물에 대해서 같은 emotion이 이미 있는지 확인
def check_if_emotion_exists(emotion_list, key, emotion):
    return any(item[1] == emotion for item in emotion_list if item[0] == key)


#csv 파일에 작성
def write_csv(csv_link,entity1, relationship, entity2):
    global lock

    #csv 파일 열기
    csv_file = open(csv_link,'a',newline='') #csv 행 추가하기
    csv_writer = csv.writer(csv_file)
   
    with lock:
        Entity1 = entity1
        Relationship = relationship
       
        # 매개변수로 들어온 entity2를 한국어 번역시킴
        Entity2 = change_en_to_kor(entity2)

        # csv에 한 행 작성
        csv_writer.writerow([Entity1, Relationship, Entity2])


#영어를 한국어로 반환함
def change_en_to_kor(en):
    kor = {"netural" : "보통", "happy": "행복함", "surprise" : "놀람","angry":"화남","disgust":"역겨움","fear":"공포","sad":"슬픔", #감정
               "Woman":"여자","Man":"남자" #성별
               }.get(en,en) # 만약 이 중에 없는 값이 들어오면 이 값을 반환함
    
    # 한국어로 변형한 값 반환함
    return kor

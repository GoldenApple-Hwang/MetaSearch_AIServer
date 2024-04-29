#구글 비전으로부터 ( 앱 내의 이미지 경로 / 서버 내 유효 DB 경로 / 서버 내 이미지 경로 / csv 파일 경로 )
#얼굴 인식 -> 얼굴 분류 -> 표정 인식

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

#얼굴 추출 / #compareFace에서 호출함

lock = threading.Lock()
face_lock = threading.Lock()

#얼굴 분석 csv 파일 작성
def compareFace(db_link,app_image_link,db_image_link,csv_link): 
     # csv 파일에 작성해야하는 인물 리스트
     extract_person_name_list = []

     # 해당 인물의 성별이 이미 존재하는지 확인하는 딕셔너리  
     extract_person_sex_dict = {} 

     # 기존에 있는 얼굴과 동일하다고 나온 얼굴을 key, 기존의 얼굴을 value로 하는 변수
     compare_extract_person_name = {}

     #각각의 인물에 대해서 감정의 값을 저장 ex) [[1,happy],[1,netural],[2,happy]]
     extract_person_emotion_list = [] 

     # 표정 분석 해야하는 얼굴 리스트
     expression_faces = []

     extract_person='' #추출할 인물에 대한 변수

     extractFaceList = [] #추출된 얼굴들을 저장하는 리스트 #반환

     image_name = app_image_link # 분석되고 있는 이미지 이름
     image_name_exclude_extension = os.path.splitext(app_image_link)[0] #추출된 얼굴 이미지에 분석된 이미지의 이름을 추가하기 위한 변수
     
     print("CompareFace에 들어옴")
      
     #날짜+시간으로 얼굴 이름 지정 
     current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
 
      
     # 비교할 얼굴 이미지가 존재하는 폴더
     face_db_path = db_link+'/faces'
     # faces가 빈 파일이면 에러 발생함 -> 나중에 수정 필요 

     # 인식된 이미지 폴더
     temp_db_path = db_link+'/temp'

     #face 폴더가 없는지 확인 + face_db_path가 비어있는지 확인 필요 -> 만약 비어있다면 item을 찾을 수 없다는 에러가 뜨면서 얼굴 비교가 불가능해짐
     if not os.path.exists(face_db_path):
        os.makedirs(face_db_path)
        test_image_path = "./test.jpg"
        shutil.copy(test_image_path,face_db_path)
        print("face 폴더 만듦 + test 이미지 복사함")
    
     # temp 폴더가 없는지 확인
     if not os.path.exists(temp_db_path):
         os.makedirs(temp_db_path)
         print("temp 폴더 만듦")
          
          
     # 서버로부터 저장된 이미지, 방금 Google Vision이 분석 후 face가 인식된 이미지
     compare_img_path = db_image_link 

     # 분석할 이미지 읽어드리기
     img = cv2.imread(compare_img_path) 

     # 얼굴 인식 
     # 얼굴 인식을 위해 dlib 필요
     detector_hog = dlib.get_frontal_face_detector() 

     img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) 
     # 얼굴 영역 인식
     dlib_rects = detector_hog(img_rgb, 1) 
    
     # 인식된 얼굴의 개수만큼 반복
     with face_lock:
        for idx,dlib_rect in enumerate(dlib_rects):
            new_extract_person = '' #처음으로 추출한 인물
            # 인식된 얼굴 영역의 0.5만큼 추출
            l = dlib_rect.left()
            t = dlib_rect.top()
            r = dlib_rect.right()
            b = dlib_rect.bottom()

            width = r - l
            height = b - t
            l = max(int(l - 0.4 * width), 0)
            t = max(int(t - 0.4 * height), 0)
            r = min(int(r + 0.4 * width), img.shape[1])
            b = min(int(b + 0.4 * height), img.shape[0]) 

            # 얼굴 부분만 잘라내기 / 자른 얼굴 temp에 임시 저장
            cropped = img[t:b, l:r]

            #temp 폴더에 임시 저장
            face_path = temp_db_path+f'/face_{image_name_exclude_extension}_{current_time}.jpg'

            # 해당 face_path에 이미지 저장
            cv2.imwrite(face_path, cropped) 

            # 자른 얼굴 얼굴 비교 시작 
            try:    
                    # 얼굴 비교 / 저장된 얼굴 이미지와 얼굴이 저장된 폴더와 비교
                    face_result = DeepFace.find(img_path=face_path, db_path=face_db_path, model_name='Facenet512',enforce_detection=False) 

                    # 만약 얼굴 비교 결과가 없으면 비교된 얼굴이 없다는 것 -> 얼굴 비교 폴더에 새롭게 저장함
                    if (len(face_result)==0 or face_result[0].empty):
                        print("얼굴을 찾지 못했습니다.")

                        # face 폴더로 이동
                        new_path = face_db_path+f'/face_{image_name_exclude_extension}_{current_time}.jpg'

                        # 이미지 파일을 temp에서 faces 다른 폴더로 이동
                        shutil.move(face_path, new_path)

                        face_path = new_path

                        # 분석해야하는 얼굴 리스트에 추가
                        # 해당 이미지는 faces 폴더 내에 존재
                        expression_faces.append(face_path)

                        new_extract_person = face_path

                        extract_person = face_path

                        print("뽑은 사람 이름 : "+ extract_person)

                    else: # 찾은 얼굴이 있는 경우
                        print("얼굴을 찾았습니다.")

                        # 표정 분석 해야하는 얼굴 리스트에 추가
                        # temp에 존재하는 얼굴 사진
                        expression_faces.append(face_path)

                        # temp 폴더에 저장했던 이미지 삭제
                        #os.remove(face_path) 

                        # 찾은 얼굴에 대한 인물을 추출
                        # 여러 개로 찾은 경우, 첫 번째의 얼굴로 결정
                        #result[0]['identity'][0] -> 동일하다고 나온 이미지의 링크 전체를 알려줌 ex) ./faces/...

                        extract_person = face_result[0]['identity'][0] # 사람 이미지 이름

                        # 키: 새로운 얼굴 값: 동일하다고 비교된 얼굴
                        compare_extract_person_name[face_path] = extract_person
                        print("뽑은 사람 이름 : "+ extract_person)
                    

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

                    # 처음 추출되는 얼굴을 반환할 추출 얼구 리스트에 포함
                    if new_extract_person!='':
                        extractFaceList.append(new_extract_person)    

                    # 표정 분석 시도
                    #compare_expression_Face(csv_link,extract_person,image_name,extract_person_name_list,extract_person_emotion_list,extract_person_sex_dict) # 표정 분석
            

                    # 뽑은 얼굴 리스트에 추가
                
            except ValueError as E:
                print("deepface에서 얼굴 분석 못 함")

     
     # 표정 분석해야하는 얼굴 리스트가 비어있지 않는 경우
     if expression_faces:
        for expression_face in expression_faces:
            # 새롭게 뽑힌 얼굴일 경우, 비교되는 얼굴이 동일하고, 기존의 얼굴과 동일하다고 나온 얼굴은 표정 분석되는 얼굴과 csv에 적혀야하는 얼굴 이름이 다르므로 체크함
            if expression_face in compare_extract_person_name.keys():
                same_face_person_name = compare_extract_person_name[expression_face]
            else:
                same_face_person_name = expression_face
            
            # 이미지 이름만 추출
            same_face_person_name  = os.path.basename(same_face_person_name)
                # 파일 이름에서 확장자를 제거한 부분 => face_1
            same_face_person_name = os.path.splitext(same_face_person_name)[0]
                
            compare_expression_Face(csv_link,expression_face,same_face_person_name,image_name,extract_person_emotion_list,extract_person_sex_dict)

        
     #얼굴 추출 리스트를 반환함
     return extractFaceList 

# 표정 분석 및 csv 파일 작성
def compare_expression_Face(csv_link,expression_face,same_face_person_name,image_name,extract_person_emotion_list,extract_person_sex_dict): #csv 파일 경로, 추출된 사람의 얼굴 이미지 이름, 분석된 사진의 이름
        # #csv 파일 열기
        # csv_file = open(csv_link,'a',newline='') #csv 행 추가하기
        # csv_writer = csv.writer(csv_file)

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

                # 인종 추출
                extract_race = face_data['dominant_race']


            isExist_Sex = check_if_sex_exist(same_face_person_name,extract_person_sex_dict)
            if not isExist_Sex:
                # 인물 리스트에 존재하지 않는다는 것은 아직 트리플에 적히지 않았다는 것이므로 트리플에 새로 적어줌                   
                # csv에 작성
                    
                #추출한 성별에 대해 작성
                write_csv(csv_link,image_name,same_face_person_name+'의 성별',extract_gender)
                # 성별 추가
                extract_person_sex_dict[same_face_person_name] = extract_gender
                    
                #추출한 인종 작성
                write_csv(csv_link,image_name,same_face_person_name+'의 인종',extract_race)

                    
            # 이미 해당 인물에게서 추출한 감정인지 체크함
            isExist_emotion = check_if_emotion_exists(extract_person_emotion_list,same_face_person_name,extract_emotion)
            if not isExist_emotion: # 만약 해당 감정이 존재하지 않는다면 추출해준다.
                write_csv(csv_link,image_name,same_face_person_name+'의 감정',extract_emotion)
            
        except ValueError as E:
            print("deepface에서 표정 분석 못 함")


# 해당 인물에 대해서 같은 emotion이 이미 있는지 확인
def check_if_emotion_exists(emotion_list, key, emotion):
    return any(item[1] == emotion for item in emotion_list if item[0] == key)

# 해당 인물에 대해서 성별이 있는지 확인
def check_if_sex_exist(extract_person_key,extract_person_sex_dict):
    if extract_person_key in extract_person_sex_dict.keys():
        return True
    else:
        return False

#csv 파일에 작성
def write_csv(csv_link,entity1, relationship, entity2):
    global lock
    #csv 파일 열기
    csv_file = open(csv_link,'a',newline='') #csv 행 추가하기
    csv_writer = csv.writer(csv_file)
   
    with lock:
        Entity1 = entity1
        Relationship = relationship
        Entity2 = change_en_to_kor(entity2)
        csv_writer.writerow([Entity1, Relationship, Entity2])

    
#영어를 한국어로 반환함
def change_en_to_kor(en):
    kor = {"netural" : "보통", "happy": "행복함", "surprise" : "놀람","angry":"화남","disgust":"역겨움","fear":"공포","sad":"슬픔", #감정
               "indian":"인도인","black":"백인","white":"백인","middle eastern":"중동인","latino hispanic":"라틴계인","asian":"아시아인", #인종
               "woman":"여자","man":"남자" #성별
               }.get(en,en)
    return kor

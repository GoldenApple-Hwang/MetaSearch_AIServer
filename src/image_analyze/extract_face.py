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

#얼굴 분석 csv 파일 작성
def compareFace(db_link,app_image_link,db_image_link,csv_link): 
     extract_person_list = [] # 인물에 대해서는 리스트로 값을 넣도록 합니다. 동일한 값이 쓰일려하는지 체크하는 용도
     extract_person='' #추출할 인물에 대한 변수
     extract_person_emotion_list = [] #각각의 인물에 대해서 감정의 값을 저장 ex) [[1,happy],[1,netural],[2,happy]]
     extractFaceList = [] #추출된 얼굴들을 저장하는 리스트
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
     for idx,dlib_rect in enumerate(dlib_rects):
        # 인식된 얼굴 영역의 0.5만큼 추출
        l = dlib_rect.left()
        t = dlib_rect.top()
        r = dlib_rect.right()
        b = dlib_rect.bottom()

        width = r - l
        height = b - t
        l = max(int(l - 0.5 * width), 0)
        t = max(int(t - 0.5 * height), 0)
        r = min(int(r + 0.5 * width), img.shape[1])
        b = min(int(b + 0.5 * height), img.shape[0]) 

        # 얼굴 부분만 잘라내기 / 자른 얼굴 temp에 임시 저장
        cropped = img[t:b, l:r]
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
                # 다른 폴더로 사진을 옮기기 위해 경로 설정
                new_path = db_link+f'/faces/face_{image_name_exclude_extension}_{current_time}.jpg'
                # 이미지 파일을 temp에서 faces 다른 폴더로 이동
                shutil.move(face_path, new_path)
                extract_person = new_path #사람 이미지 이름
                print("뽑은 사람 이름 : "+ extract_person)
                #face_path = new_path

            else: # 찾은 얼굴이 있는 경우
                print("얼굴을 찾았습니다.")
                os.remove(face_path) #저장했던 이미지 삭제

                # 찾은 얼굴에 대한 인물을 추출
                # 여러 개로 찾은 경우, 첫 번째의 얼굴로 결정
                #result[0]['identity'][0] -> 동일하다고 나온 이미지의 링크 전체를 알려줌 ex) ./faces/...

                extract_person = face_result[0]['identity'][0] # 사람 이미지 이름
                print("뽑은 사람 이름 : "+ extract_person)

            #삭제할 얼굴 사진 이름 리스트에 추가 
            extractFaceList.append(extract_person)  # 경로를 줘야 json에서 해당 경로를 타고 바이트 배열을 반환할 수 있음
            
            compare_expression_Face(csv_link,extract_person,image_name,extract_person_list,extract_person_emotion_list) # 표정 분석
            
        except ValueError as E:
            print("deepface에서 얼굴 분석 못 함")
            
     #얼굴 추출 리스트를 반환함
     return extractFaceList 
# 표정 분석 및 csv 파일 작성
def compare_expression_Face(csv_link,extract_person,image_name,extract_person_list,extract_person_emotion_list): #csv 파일 경로, 추출된 사람의 얼굴 이미지 이름, 분석된 사진의 이름
       
        #csv 파일 열기
        csv_file = open(csv_link,'a',newline='') #csv 행 추가하기
        csv_writer = csv.writer(csv_file)

        try:

            # 해당 얼굴 사진 표정 분석
            emotion_result = DeepFace.analyze(img_path=extract_person,
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


            # 인물 추출 
            #os.path.basename(...) -> 사진 이름만 추출함 => face_1.jpg
            extract_person  = os.path.basename(extract_person)
            # 파일 이름에서 확장자를 제거한 부분 => face_1
            extract_person = os.path.splitext(extract_person)[0]


            if(extract_person in extract_person_list): #만약 이미 인물 리스트에 추출한 얼굴 이미지 이름이 존재한다면
                pass # 패스
                    #이미 이름이 존재한다는 것은 트리플에 적혀있다는 것이므로 새로 csv에 적지 않도록 한다.
            else:
                    extract_person_list.append(extract_person) # 인물 리스트에 추출한 얼굴 이미지 이름이 존재하지 않는다면
                    # 인물 리스트에 존재하지 않는다는 것은 아직 트리플에 적히지 않았다는 것이므로 트리플에 새로 적어줌                   
                    # csv에 작성
                    # 추출한 얼굴에 대한 인물 작성
                    write_csv(csv_writer,image_name,'인물',extract_person)
                
                    #추출한 성별에 대해 작성
                    write_csv(csv_writer,image_name,extract_person+'의 성별',extract_gender)
                    #Entity1 = image_name
                    #Relationship=extract_person+"의 성별"
                    #Entity2 = change_en_to_kor(extract_gender) # 영어를 한국어로 변경
                    #csv_writer.writerow([Entity1, Relationship, Entity2]) 

                    #추출한 인종 작성
                    write_csv(csv_writer,image_name,extract_person+'의 인종',extract_race)

            # 이미 해당 인물에게서 추출한 감정인지 체크함
            isExist_emotion = check_if_emotion_exists(extract_person_emotion_list,extract_person,extract_emotion)
            if not isExist_emotion: # 만약 해당 감정이 존재하지 않는다면 추출해준다.
                write_csv(csv_writer,image_name,extract_person+'의 감정',extract_emotion)
                #Entity1 = image_name
                #Relationship = extract_person+"의 감정"
                #Entity2 = change_en_to_kor(extract_emotion) #영어를 한국어로 변경
                #csv_writer.writerow([Entity1, Relationship, Entity2])

        except ValueError as E:
            print("deepface에서 표정 분석 못 함")


# 해당 인물에 대해서 같은 emotion이 이미 있는지 확인
def check_if_emotion_exists(emotion_list, key, emotion):
    return any(item[1] == emotion for item in emotion_list if item[0] == key)


#csv 파일에 작성
def write_csv(csv_writer,entity1, relationship, entity2):
    global lock
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
               }.get(en)
    return kor

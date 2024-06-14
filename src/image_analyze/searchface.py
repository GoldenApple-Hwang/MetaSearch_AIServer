import cv2
import os
from deepface import DeepFace
from datetime import datetime 
import math
import dlib
import re
# 이미지 경로
# 구글 비전에서 자른 모서리 poly_points

# 원으로 검색할 때 호출
def cut_face_image(db_link,image_path,poly_points):
    extract_person = None

    # 비교할 얼굴 이미지가 존재하는 폴더
    face_db_path = db_link+'/faces'
   # face_db_path = '/home/hstack/AiServer/dbaa89842d858540b5b4c1ec1769677e78/faces'

    # 잠시 자른 이미지 저장 폴더
    temp_db_path = db_link+'/search/temp'

    #날짜+시간으로 얼굴 이름 지정 
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')

    # temp 폴더가 없는지 확인
    if not os.path.exists(temp_db_path):
        os.makedirs(temp_db_path)
        print("temp 폴더 만듦")

    image = cv2.imread(image_path)

    coordinate_x1 = int(poly_points[0][0])
    coordinate_x2 = int(poly_points[1][0])
    coordinate_y1 = int(poly_points[0][1])
    coordinate_y2 = int(poly_points[2][1])

    # 이미지 자르기
    cropped_image = image[coordinate_y1:coordinate_y2, coordinate_x1:coordinate_x2]

    cut_image_path = temp_db_path+f'/cut_image_{current_time}.jpg'

    # 이미지 저장
    cv2.imwrite(cut_image_path, cropped_image) 


    # 모서리 맞춰 자른 이미지에서 얼굴 인식
    #extract_person = detect_face(cut_image_path,temp_db_path,face_db_path)
    
    # 얼굴 비교 함수 호출 (매개변수: 자른 이미지 경로, 얼굴 비교 리스트 경로)
    extract_person = compare_face(cut_image_path,face_db_path)
    if extract_person != None:
        if "person" in extract_person:
            number = re.sub(r'\D', '', extract_person)
            extract_person = f"인물{number}"
    return extract_person


# # 얼굴 인식
# # 자른 이미지로 얼굴 인식하는 함수
# def detect_face(cut_image_path,temp_db_path,face_db_path):
#     extract_person = None

#     current_time = datetime.now().strftime('%Y%m%d_%H%M%S')

#     cut_image = cv2.imread(cut_image_path)
#     # 얼굴 인식을 위해 dlib 필요
#     detector_hog = dlib.get_frontal_face_detector() 

#     img_rgb = cv2.cvtColor(cut_image, cv2.COLOR_BGR2RGB) 
#      # 얼굴 영역 인식
#     dlib_rects = detector_hog(img_rgb, 1) 
#          # 인식된 얼굴의 개수만큼 반복 

#     # 자를 얼굴이 없다면
#     if not dlib_rects:
#         return extract_person

#     for idx,dlib_rect in enumerate(dlib_rects):
#         print("얼굴 인식")
#         # 인식된 얼굴 영역의 0.5만큼 추출
#         l = dlib_rect.left()
#         t = dlib_rect.top()
#         r = dlib_rect.right()
#         b = dlib_rect.bottom()

#         width = r - l
#         height = b - t
#         l = max(int(l - 0.4 * width), 0)
#         t = max(int(t - 0.4 * height), 0)
#         r = min(int(r + 0.4 * width), cut_image.shape[1])
#         b = min(int(b + 0.4 * height), cut_image.shape[0]) 

#         # 얼굴 부분만 잘라내기 / 자른 얼굴 temp에 임시 저장
#         cropped = cut_image[t:b, l:r]
#         face_path = temp_db_path+f'/face__{current_time}.jpg'
#         # 해당 face_path에 이미지 저장
#         cv2.imwrite(face_path, cropped)

#         # 인지된 얼굴 분석
#         extract_person = compare_face(face_path,face_db_path)

#     return extract_person


# 자른 얼굴 이미지 얼굴 이미지 리스트들과 비교
def compare_face(face_path,face_db_path):
    extract_person = None
    print("얼굴 추출 폴더 : "+face_db_path)
    try:
        face_result = DeepFace.find(img_path=face_path, db_path=face_db_path, model_name='Facenet512',enforce_detection=False) 

        # 비교된 얼굴이 없는 경우
        if (len(face_result)==0 or face_result[0].empty):
            os.remove(face_path) # 저장되었던 임시 사진 삭제
            extract_person = None
        else: # 비교된 얼굴이 있는 경우
            extract_person = face_result[0]['identity'][0] # 사람 이미지 이름
            extract_person = os.path.basename(extract_person)
            #extract_person = os.path.splitext(extract_person)[0] #수정함----
            print("뽑은 사람 이름 : "+ extract_person)
            
    except ValueError as E:
        print("deepface에서 얼굴 분석 못 함")
        #temp에 있는 얼굴 삭제
        print("temp에 저장되어있는 얼굴 삭제 시도하려함")
        if face_path: 
            print("temp에 있는 이미지의 경로 : "+face_path)
            #os.remove(face_path) # temp에 이미지가 존재하면 해당 이미지 삭제함
        print("temp에 있는 얼굴 삭제함")

    return extract_person

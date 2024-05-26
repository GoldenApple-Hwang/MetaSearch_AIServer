from google.cloud import vision
from PIL import Image, ImageDraw
from math import sqrt
#from circle_to_search_face import cut_face_image #deepface 함수 호출
from image_analyze.searchface import cut_face_image # 함수 호출
from kakaotrans import Translator
import requests
import json
import piexif

#번역
def papago_translation(text, source_lang='en', target_lang='ko'):
    url = "https://naveropenapi.apigw.ntruss.com/nmt/v1/translation"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": "API-KEY-ID",
        "X-NCP-APIGW-API-KEY": "API-KEY",
        "Content-Type": "application/json"
    }
    data = {
        "source": source_lang,
        "target": target_lang,
        "text": text
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        translated_text = response.json()['message']['result']['translatedText']
        return translated_text
    else:
        return "번역에 실패했습니다. 오류 코드: {}".format(response.status_code)


def detect_and_draw_objects_in_radius(db_link,path_to_image, normalized_x, normalized_y, normalized_radius): 
    #추출된 것들 
    dected_objects = []
    
    # Vision API 클라이언트 생성
    client = vision.ImageAnnotatorClient()

    #이미지를 로드
    with open(path_to_image, "rb") as image_file:
        content = image_file.read()
        image = vision.Image(content=content)


    # 객체 로컬라이제이션 수행
    objects = client.object_localization(image=image).localized_object_annotations

    # 원본 이미지 로드 및 그릴 준비
    original_image = Image.open(path_to_image)
    width, height = original_image.size
    draw = ImageDraw.Draw(original_image)

    # 정규화된 좌표 및 반경을 실제 좌표 및 반경으로 변환
    draw_center_x = normalized_x * width
    draw_center_y = normalized_y * height
    draw_radius = normalized_radius * max(width, height)

    # 주어진 위치와 반경에 원을 그림
    draw.ellipse(
        [(draw_center_x - draw_radius, draw_center_y - draw_radius),
         (draw_center_x + draw_radius, draw_center_y + draw_radius)],
        outline="red",
        width=2
    )

    # 주어진 반경 내에 객체가 있는지를 추적할 플래그 변수
    object_found = False
     # 주어진 반경 내에 있는 객체 중 최대 신뢰도를 가진 객체를 찾을 변수
    max_confidence = 0
    best_obj = None
    extract_person = None

    # 감지된 객체를 반복
    for obj in objects:
        # 객체의 경계 다각형을 가져옴
        bounding_poly = obj.bounding_poly.normalized_vertices

        # 각 객체의 경계 다각형을 그림
        poly_points = [(vertex.x * width, vertex.y * height) for vertex in bounding_poly]
        draw.polygon(poly_points, outline="green", width=2)
        print("poly_points 각 객체의 경계 :")
        print(poly_points)

        # 각 객체의 중심을 계산
        center_x = sum(vertex.x for vertex in bounding_poly) / len(bounding_poly)
        center_y = sum(vertex.y for vertex in bounding_poly) / len(bounding_poly)

        # 주어진 위치와 객체 중심 사이의 거리를 계산
        distance = sqrt((center_x * width - draw_center_x) ** 2 + (center_y * height - draw_center_y) ** 2)

        # 객체가 주어진 반경 내에 있는지 확인
        if distance <= draw_radius:
            if best_obj and best_obj.name != obj.name:
               continue

            if obj.score > max_confidence:
                max_confidence = obj.score
                best_obj = obj
                
                # 만약 사람이 추출되면 얼굴 분석으로 이동
                if best_obj.name == "Person":
                    print("이미지 경로 : "+path_to_image)
                    print("person 나옴")
                    extract_person = cut_face_image(db_link,path_to_image,poly_points)
                    if extract_person != None:  
                        best_obj.name = extract_person
                    print("best_obj.name : "+best_obj.name)

                print(f"객체 발견: {best_obj.name} (신뢰도: {best_obj.score})")
                object_found = True
 
        if object_found:
            # #  if not object_found_face:
            # 얼굴을 발견하지 못하였을 경우에만 해당 객체에 대해서 번역함
             if extract_person != None:
                best_obj.name = extract_person
             else:
                best_obj.name = papago_translation(best_obj.name)
                
            
             print(f"객체 발견: {best_obj.name}")
             original_image.save("/home/hstack/Downloads/output.jpeg") #사진
             return best_obj

    # 객체가 주어진 반경 내에 없을 때 메시지 프린트
    if not object_found:
        print("주어진 반경 내에 객체가 발견되지 않았습니다.")
        original_image.save("/home/hstack/Downloads/output.jpeg") #사진   
        return ""
     


import os
import csv
from google.cloud import vision
from typing import List
from nltk.corpus import wordnet as wn
import shutil
from image_analyze.extract_face import compareFace
#from extract_face import compareFace
import threading
import re
from konlpy.tag import Okt

#csv 파일 작성 lock
csv_lock = threading.Lock()
wordnet_lock = threading.Lock()


# 이미지 읽어오기
def read_image(file_path: str) -> bytes:
    with open(file_path, "rb") as image_file:
        content = image_file.read()
    return content

# 객체, 레이블, 텍스트, 색상, 얼굴 검출
def detect_entities(image_content: bytes) -> List[str]:
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_content)
    
    # 객체, 레이블, 텍스트, 색상, 얼굴 검출
    response_objects = client.object_localization(image=image)
    response_labels = client.label_detection(image=image, max_results=20)
    response_text = client.text_detection(image=image)
    response_colors = client.image_properties(image=image)
    response_faces = client.face_detection(image=image)
    
    objects = [obj.name.lower() for obj in response_objects.localized_object_annotations if obj.name.lower() != "person"]
    labels = [label.description.lower() for label in response_labels.label_annotations]
    text = [text.description for text in response_text.text_annotations]
    colors = [f"#{int(color.color.red):02X}{int(color.color.green):02X}{int(color.color.blue):02X}" for color in response_colors.image_properties_annotation.dominant_colors.colors[:3]]
    faces = response_faces.face_annotations
    
    return objects, labels, text, colors, faces

# WordNet 사용해서 원하는 상위어 찾기
def find_specific_hypernym(word: str, target_hypernym: str) -> str:
    with wordnet_lock:
        synsets = wn.synsets(word, pos=wn.NOUN)
        selected_hypernym = None
        min_depth = float('inf')
        for synset in synsets:
            current_synset = synset
            while current_synset.hypernyms():
                current_synset = current_synset.hypernyms()[0]
                if current_synset.name() == target_hypernym:
                    depth = current_synset.min_depth()
                    if depth < min_depth:
                        min_depth = depth
                        selected_hypernym = current_synset.name().split('.')[0]
        return selected_hypernym if selected_hypernym else ""

# CSV 파일 작성 함수
def write_to_csv(csv_file_path, image_app_path, translated_label, translated_description):

    #Lock 객체 정의
    #lock = threading.Lock()
    
    with csv_lock:
        with open(csv_file_path, 'a', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow([image_app_path, translated_label, translated_description])

# 실행 함수
def image_analysis(CSV_DIRECTORY, IMAGE_APP_PATH, IMAGE_FILE_PATH, CSV_FILE_PATH):
    print("gvapi 들어옴")
    extractFaceList = []
    
    # 이미지 파일 읽기
    image_content = read_image(IMAGE_FILE_PATH)

    # 객체, 레이블, 텍스트, 색상, 얼굴 검출
    objects_detected, labels_detected, text_detected, colors_detected, faces_detected = detect_entities(image_content)
    
    #얼굴 인식이 있을 경우
    if faces_detected:
        extractFaceList = compareFace(CSV_DIRECTORY, IMAGE_APP_PATH, IMAGE_FILE_PATH, CSV_FILE_PATH)

    # CSV 작성 관련된 값들을 기록하기 위해 세트 사용
    recorded_values = set()

    specific_hypernyms = {
        'color.n.01': 'color',
        'animal.n.01': 'animal',
        'furniture.n.01': 'furniture',
        'fruit.n.01': 'fruit',
        'food.n.01': 'food',
        'beverage.n.01': 'beverage',
        'dessert.n.01': 'dessert',
        'baked_goods.n.01': 'baked_goods',
        'clothing.n.01': 'clothing',
        'jewelry.n.01': 'jewelry',
        'electronic_equipment.n.01': 'electronic_equipment',
        'plant.n.01': 'plant',
        'footwear.n.01': 'footwear',
        'vegetable.n.01': 'vegetable',
        'person.n.01': 'person'
    }

    # objects_detected 처리
    for obj in objects_detected:
        if obj == "person":
            pass
        else:
            if obj not in recorded_values:
                recorded_values.add(obj)
                if obj in ('street', 'ice cream', 'cup', 'building', 'hat', 'cap', 'sports', 'glasses', 'sunset', 'sunrise', 'toy', 'sky', 'car'):
                    write_to_csv(CSV_FILE_PATH, IMAGE_APP_PATH, obj, obj)
                elif obj in ('photograph'):
                    write_to_csv(CSV_FILE_PATH, IMAGE_APP_PATH, "인생네컷", obj)
                elif obj in ('nail polish'):
                    write_to_csv(CSV_FILE_PATH, IMAGE_APP_PATH, "네일아트", obj)
                elif obj in ('beach', 'ocean', 'sea'):
                    write_to_csv(CSV_FILE_PATH, IMAGE_APP_PATH, "바다", obj)
                else:
                    for hypernym, label_type in specific_hypernyms.items():
                        if label_type == find_specific_hypernym(obj, hypernym):
                            write_to_csv(CSV_FILE_PATH, IMAGE_APP_PATH, label_type, obj)
                            break

    # labels_detected 처리
    for label in labels_detected:
        if label in objects_detected:
            continue
        if label not in recorded_values:
            recorded_values.add(label)
            if label in ('street', 'ice cream', 'cup', 'building', 'hat', 'cap', 'sports', 'glasses', 'sunset', 'sunrise', 'toy', 'sky', 'car'):
                write_to_csv(CSV_FILE_PATH, IMAGE_APP_PATH, label, label)
            elif label in ('photograph'):
                write_to_csv(CSV_FILE_PATH, IMAGE_APP_PATH, "인생네컷", label)
            elif label in ('nail polish'):
                write_to_csv(CSV_FILE_PATH, IMAGE_APP_PATH, "네일아트", label)
            elif label in ('beach', 'ocean', 'sea'):
                write_to_csv(CSV_FILE_PATH, IMAGE_APP_PATH, "바다", label)
            else:
                for hypernym, label_type in specific_hypernyms.items():
                    if label_type == find_specific_hypernym(label, hypernym):
                        write_to_csv(CSV_FILE_PATH, IMAGE_APP_PATH, label_type, label)
                        break

    # 형태소 분석기 초기화
    okt = Okt()

    # 단어를 추출하는 함수 정의
    def extract_words(text):
        # 형태소 분석을 통해 명사만 추출
        nouns = okt.nouns(text)
        return nouns

    #숫자를 추출하는 함수 정의
    def extract_numbers(text):
        #형태소 분석을 통해 숫자만 추출
        numbers = re.findall(r'\d+', text) 
        return numbers

    #영단어를 추출하는 함수 정의
    def extract_english_words(text):
        # 정규표현식을 사용하여 영단어만 추출
        english_words = re.findall(r'\b[A-Za-z]+\b', text)
        return english_words                      

    # text_detected 처리
    if text_detected:
        nouns = extract_words(text_detected[0])
        numbers = extract_numbers(text_detected[0])
        english_words = extract_english_words(text_detected[0])
 
        if nouns: 
            for word in nouns:
                write_to_csv(CSV_FILE_PATH, IMAGE_APP_PATH, "텍스트", word)
        if numbers:
            for word in numbers:
                write_to_csv(CSV_FILE_PATH, IMAGE_APP_PATH, "텍스트", word)
        if english_words:
            for word in english_words:
                write_to_csv(CSV_FILE_PATH, IMAGE_APP_PATH, "텍스트", word)   


    print(f"Triple CSV updated at: {CSV_FILE_PATH}")
    


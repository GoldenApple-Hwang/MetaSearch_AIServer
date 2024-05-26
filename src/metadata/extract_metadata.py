import csv
from PIL import Image
from PIL.ExifTags import TAGS
from geopy.geocoders import GoogleV3
import threading

#Lock 객체 정의
lock = threading.Lock()

# 이미지에서 EXIF 데이터를 추출하는 함수
def extract_exif_data(IMAGE_FILE_PATH):
    try:
        image = Image.open(IMAGE_FILE_PATH)
        exif_data = image._getexif()
        return exif_data
    except Exception as e:
        print(f"Error extracting EXIF data: {str(e)}")
        return None 

# EXIF 데이터를 통해 위치 정보를 추출하는 함수
def extract_gps_info(exif_data):
    gps_info = {}
    if exif_data:
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name == 'GPSInfo':
                try:
                    gps_info = {
                        'latitude': value[2],
                        'latitude_ref': value[1],
                        'longitude': value[4],
                        'longitude_ref': value[3]
                    }
                except (KeyError, IndexError):
                    print(f"Error extracting GPS info: {str(e)}")
                    return None
                    print("위치 정보 없음")
    print(f"gps_info: {gps_info}")
    return gps_info if gps_info else None


# 위도와 경도 정보를 DMS 형식에서 DD 형식으로 변환하는 함수
def convert_dms_to_dd(gps_info):
    def dms_to_dd(dms, ref):
        dd = dms[0] + dms[1] / 60 + dms[2] / 3600
        if ref in ['S', 'W']:
            dd *= -1
        return dd

    if gps_info:
        lat_dd = dms_to_dd(gps_info['latitude'], gps_info['latitude_ref'])
        lon_dd = dms_to_dd(gps_info['longitude'], gps_info['longitude_ref'])
        print("위치 변환함")
    else:
        lat_dd, lon_dd = None, None  

    print(f"lat_dd: {lat_dd}, lon_dd: {lon_dd}")
    return lat_dd, lon_dd

# 역 지오코딩을 통해 위치 정보를 추출하는 함수
def reverse_geocode(lat_dd, lon_dd, api_key):
    geolocator = GoogleV3(api_key=api_key)
    if lat_dd is not None and lon_dd is not None:
        try:
            location = geolocator.reverse((lat_dd, lon_dd))
            return location
            print("위치 정보 추출 완료")
        except Exception as e:
            print(f"Error during reverse geocoding: {str(e)}")
            print(f"Failed to retrieve location data for coordinates: lat_dd={lat_dd}, lon_dd={lon_dd}")
            return None
    else:
        return None

# 위치 정보를 CSV 형식으로 변환하는 함수
def process_location_data(location, IMAGE_APP_PATH):
    csv_data = []
    if location is not None:
        address_components = location.raw.get('address_components', [])
        
        # 주소 요소 추출
        def extract_component(component_type):
            return next((component['long_name'] for component in address_components if component_type in component['types']), '')
        
        # 각 위치 정보 요소를 CSV 데이터에 추가
        country = extract_component('country')
        administrative_area_level_1 = extract_component('administrative_area_level_1')
        locality = extract_component('locality')
        sublocality = extract_component('sublocality')
        sublocality_level_1 = extract_component('sublocality_level_1')
        postal_code = extract_component('postal_code')
        route = extract_component('route')
        premise = extract_component('premise')
        formatted_address = location.raw.get('formatted_address', '')

        # 각 위치 정보 요소가 있을 경우에만 CSV 데이터에 추가
        if country:
            csv_data.append((IMAGE_APP_PATH, '나라', extract_component('country')))
        if administrative_area_level_1:
            csv_data.append((IMAGE_APP_PATH, '도', extract_component('administrative_area_level_1')))
        if locality:
            csv_data.append((IMAGE_APP_PATH, '도시', extract_component('locality')))
        if sublocality_level_1:
            csv_data.append((IMAGE_APP_PATH, '구', extract_component('sublocality_level_1')))
        if sublocality:
            csv_data.append((IMAGE_APP_PATH, '동', extract_component('sublocality')))
        if postal_code:
            csv_data.append((IMAGE_APP_PATH, '우편번호', extract_component('postal_code')))
        if route:
            csv_data.append((IMAGE_APP_PATH, '도로', extract_component('route')))
        if premise:
            csv_data.append((IMAGE_APP_PATH, '건물', extract_component('premise')))
        if formatted_address:
            csv_data.append((IMAGE_APP_PATH, '형식화된 주소', location.raw.get('formatted_address', '')))

    return csv_data

# 날짜 및 시간 정보를 추출하는 함수
def extract_date_time_info(exif_data):
    date_time_info = {}
    if exif_data:
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name == 'DateTime':
                date_time = value.split()
                date = date_time[0].split(":")
                time = date_time[1].split(":")
                
                date_time_info = {
                    'year': date[0],
                    'month': date[1],
                    'day': date[2],
                    'time': date_time[1]
                    'hour': time[0]
                }
    return date_time_info

# 시간 정보를 통해 낮과 밤을 구분하는 함수
def determine_day_night(time):
    hour = int(time.split(":")[0])
    if 7 <= hour < 19:
        return '낮'
    else:
        return '밤'

# 월 정보를 통해 계절을 구분하는 함수
def determine_season(month):
    if month in ['03', '04', '05']:
        return '봄'
    elif month in ['06', '07', '08']:
        return '여름'
    elif month in ['09', '10', '11']:
        return '가을'
    else:
        return '겨울'

# 플래시 정보를 추출하는 함수
def extract_flash_info(exif_data):
    flash_info = {}
    if exif_data:
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name == 'Flash':
                flash_info = {'flash': '켜짐' if value == 1 else '꺼짐'}
    return flash_info

# 방향 정보를 추출하는 함수
def extract_orientation_info(exif_data):
    orientation_info = {}
    if exif_data:
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name == 'Orientation':
                orientation_info = {'orientation': '정상' if value == 1 else '비정상'}
    return orientation_info

# 해상도 정보를 추출하는 함수
def extract_resolution_info(exif_data):
    resolution_info = {}
    x_resolution, y_resolution = None, None
    if exif_data:
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name == 'XResolution':
                x_resolution = value
            elif tag_name == 'YResolution':
                y_resolution = value
                
    if x_resolution and y_resolution:
        resolution_info = determine_resolution(x_resolution, y_resolution)
    
    return resolution_info

# 해상도에 따라 해상도 종류를 결정하는 함수
def determine_resolution(x_resolution, y_resolution):
    if x_resolution <= 640 or y_resolution <= 480:
        return {'resolution': '낮음'}
    elif 640 < x_resolution <= 1280 and 480 < y_resolution <= 720:
        return {'resolution': '높음'}
    elif 1280 < x_resolution <= 1920 and 720 < y_resolution <= 1080:
        return {'resolution': '높음'}
    elif 1920 < x_resolution <= 2560 and 1080 < y_resolution <= 1440:
        return {'resolution': '높음'}
    elif 2560 < x_resolution <= 3840 and 1440 < y_resolution <= 2160:
        return {'resolution': '높음'}
    else:
        pass

# EXIF 데이터를 처리하고 CSV 데이터를 생성하는 함수
def process_exif_data(exif_data, api_key, IMAGE_APP_PATH):
    csv_data = []
    
    # GPS 정보 추출 및 역 지오코딩
    gps_info = extract_gps_info(exif_data)
    if gps_info:
        lat_dd, lon_dd = convert_dms_to_dd(gps_info)
        location = reverse_geocode(lat_dd, lon_dd, api_key)
        location_data = process_location_data(location, IMAGE_APP_PATH)
        csv_data.extend(location_data)
    
    # 시간, 플래시, 방향 및 해상도 정보 처리
    date_time_info = extract_date_time_info(exif_data)
    if date_time_info:
        # 낮과 밤 구분
        day_night = determine_day_night(date_time_info['time'])
        csv_data.append((IMAGE_APP_PATH, '밤/낮', day_night))
        
        # 계절 구분
        season = determine_season(date_time_info['month'])
        csv_data.append((IMAGE_APP_PATH, '계절', season))
        
        # 날짜 및 시간 정보 추가
        csv_data.append((IMAGE_APP_PATH, '년', date_time_info['year']))
        csv_data.append((IMAGE_APP_PATH, '월', date_time_info['month']))
        csv_data.append((IMAGE_APP_PATH, '일', date_time_info['day']))
        csv_data.append((IMAGE_APP_PATH, '시', date_time_info['hour']))

    # 플래시 정보
    flash_info = extract_flash_info(exif_data)
    if flash_info:
        csv_data.append((IMAGE_APP_PATH, '플래시', flash_info['flash']))
    
    # 방향 정보
    orientation_info = extract_orientation_info(exif_data)
    if orientation_info:
        csv_data.append((IMAGE_APP_PATH, '방향', orientation_info['orientation']))
    
    # 해상도 정보
    resolution_info = extract_resolution_info(exif_data)
    if resolution_info:
        csv_data.append((IMAGE_APP_PATH, '해상도', resolution_info['resolution']))
    
    return csv_data

# CSV 파일에 데이터를 작성하는 함수
def write_csv_data(CSV_FILE_PATH, csv_data):
    with lock:
        with open(CSV_FILE_PATH, mode='a', newline='') as file:
            csv_writer = csv.writer(file)
            csv_writer.writerows(csv_data)

# 전체 코드를 실행하는 함수
def meta_run(IMAGE_APP_PATH, IMAGE_FILE_PATH, CSV_FILE_PATH):
    # Google Maps Geocoding API 키
    api_key = 'AIzaSyAlpcJJZZfYKRt_ESF9KMyKFeEsDmaepTo'
    
    # 이미지 파일에서 EXIF 데이터 추출
    exif_data = extract_exif_data(IMAGE_FILE_PATH)
    
    # EXIF 데이터 처리
    csv_data = process_exif_data(exif_data, api_key, IMAGE_APP_PATH)
    
    # CSV 파일에 데이터 작성
    write_csv_data(CSV_FILE_PATH, csv_data)

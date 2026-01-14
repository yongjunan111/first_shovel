"""
RideQuest 초기 데이터 삽입 스크립트
국토종주 인증센터 좌표 데이터
"""
from database import SessionLocal, engine
import models

# 테이블 생성
models.Base.metadata.create_all(bind=engine)

# 국토종주 인증센터 데이터 (4대강 자전거길)
SPOT_DATA = [
    # 낙동강 자전거길
    {"name": "낙동강하구둑 인증센터", "description": "낙동강 자전거길 시작점", "latitude": 35.0795, "longitude": 128.9419, "radius": 150},
    {"name": "삼락생태공원 인증센터", "description": "부산 삼락생태공원", "latitude": 35.1465, "longitude": 129.0167, "radius": 150},
    {"name": "물금취수장 인증센터", "description": "양산 물금", "latitude": 35.3103, "longitude": 129.0047, "radius": 150},
    {"name": "달성보 인증센터", "description": "대구 달성보", "latitude": 35.8139, "longitude": 128.4361, "radius": 150},
    {"name": "상주보 인증센터", "description": "상주보", "latitude": 36.4164, "longitude": 128.1614, "radius": 150},
    {"name": "안동댐 인증센터", "description": "낙동강 자전거길 종점", "latitude": 36.6381, "longitude": 128.8694, "radius": 150},
    
    # 금강 자전거길
    {"name": "금강하구둑 인증센터", "description": "금강 자전거길 시작점", "latitude": 36.0086, "longitude": 126.7564, "radius": 150},
    {"name": "백제보 인증센터", "description": "부여 백제보", "latitude": 36.2758, "longitude": 126.9086, "radius": 150},
    {"name": "공주보 인증센터", "description": "공주보", "latitude": 36.4603, "longitude": 127.0869, "radius": 150},
    {"name": "세종보 인증센터", "description": "세종시 세종보", "latitude": 36.5456, "longitude": 127.2294, "radius": 150},
    {"name": "대청댐 인증센터", "description": "금강 자전거길 종점", "latitude": 36.4786, "longitude": 127.4839, "radius": 150},
    
    # 영산강 자전거길
    {"name": "영산강하구둑 인증센터", "description": "영산강 자전거길 시작점", "latitude": 34.8003, "longitude": 126.4269, "radius": 150},
    {"name": "죽산보 인증센터", "description": "나주 죽산보", "latitude": 35.0086, "longitude": 126.7028, "radius": 150},
    {"name": "승촌보 인증센터", "description": "광주 승촌보", "latitude": 35.0492, "longitude": 126.8183, "radius": 150},
    {"name": "담양댐 인증센터", "description": "영산강 자전거길 종점", "latitude": 35.2844, "longitude": 126.9919, "radius": 150},
    
    # 한강 자전거길 (서울~양평)
    {"name": "한강하구 인증센터", "description": "한강 자전거길 시작점 (김포)", "latitude": 37.6089, "longitude": 126.7217, "radius": 150},
    {"name": "여의도 인증센터", "description": "서울 여의도한강공원", "latitude": 37.5284, "longitude": 126.9344, "radius": 150},
    {"name": "잠실 인증센터", "description": "서울 잠실한강공원", "latitude": 37.5172, "longitude": 127.0756, "radius": 150},
    {"name": "팔당댐 인증센터", "description": "남양주 팔당댐", "latitude": 37.5214, "longitude": 127.2797, "radius": 150},
    {"name": "양평 인증센터", "description": "한강 자전거길 종점", "latitude": 37.4908, "longitude": 127.4875, "radius": 150},
    
    # 섬진강 자전거길
    {"name": "섬진강댐 인증센터", "description": "섬진강 자전거길 시작점", "latitude": 35.6322, "longitude": 127.1353, "radius": 150},
    {"name": "곡성기차마을 인증센터", "description": "곡성 기차마을", "latitude": 35.2722, "longitude": 127.2911, "radius": 150},
    {"name": "광양 인증센터", "description": "섬진강 자전거길 종점", "latitude": 34.9408, "longitude": 127.6956, "radius": 150},
]


def init_spots():
    """스팟 데이터 초기화"""
    db = SessionLocal()
    try:
        # 기존 데이터 확인
        existing = db.query(models.Spot).count()
        if existing > 0:
            print(f"⚠️  이미 {existing}개의 스팟이 존재합니다. 초기화를 건너뜁니다.")
            return
        
        # 데이터 삽입
        for spot_data in SPOT_DATA:
            spot = models.Spot(**spot_data)
            db.add(spot)
        
        db.commit()
        print(f"✅ {len(SPOT_DATA)}개의 스팟 데이터가 성공적으로 삽입되었습니다.")
        
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_spots()

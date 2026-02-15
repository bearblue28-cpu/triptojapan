import json, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST_FILE = os.path.join(BASE_DIR, "data", "destinations.json")


# ----------------------------------
# 데이터 구조 보정
# ----------------------------------
def normalize_city_data(city):
    city.setdefault("views", 0)
    city.setdefault("districts", {})

    for district in city["districts"].values():
        district.setdefault("views", 0)
        district.setdefault("attractions", {})

        for attraction in district["attractions"].values():
            attraction.setdefault("views", 0)


# ----------------------------------
# 전체 데이터 로드
# ----------------------------------
def load_destinations(include_region=False):
    if not os.path.exists(DEST_FILE):
        return []

    with open(DEST_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # ✅ region 구조 그대로 필요할 때
    if include_region:
        for region in data:
            for city in region.get("cities", []):
                normalize_city_data(city)
        return data

    # ✅ recommend 용: 도시만 flat
    cities = []
    for region in data:
        for city in region.get("cities", []):
            normalize_city_data(city)
            cities.append(city)

    return cities


# ----------------------------------
# 저장
# ----------------------------------
def save_destinations(data):
    with open(DEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

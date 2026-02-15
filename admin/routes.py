from flask import Blueprint, render_template, request, redirect, url_for, current_app
import os, json, uuid
from werkzeug.utils import secure_filename


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "data", "destinations.json")
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "templates", "admin")

admin_bp = Blueprint("admin", __name__, template_folder=TEMPLATE_FOLDER)

# ----------------------------
# 체크리스트 데이터
# ----------------------------
checklist = {
    "R": {
        "name": "Relax / 휴식형",
        "items": {
            "리조트/온천 중심 체류": 30,
            "도시 외곽·섬·고원 환경": 25,
            "관광객 밀도 낮음": 20,
            "자연 속 장기 체류 가능": 15,
            "조용한 산책·휴식 동선": 5,
            "도심 공원·카페 존재": 5
        }
    },

    "A": {
        "name": "Activity / 액티비티형",
        "items": {
            "대형 테마파크/놀이공원": 30,
            "스키·해양·산악 레저": 25,
            "하루 소비형 체험 콘텐츠": 20,
            "체험형 시설 밀집": 15,
            "도심 체험 시설": 5,
            "일반 쇼핑/상업 활동": 5
        }
    },

    "C": {
        "name": "Culture / 문화형",
        "items": {
            "구역 전체가 역사·문화 자산": 30,
            "전통 거리·건축 보존": 25,
            "지역/국가 정체성 상징": 20,
            "연중 전통 행사·의식": 15,
            "박물관·미술관": 5,
            "현대 문화 시설": 5
        }
    },

    "F": {
        "name": "Food / 미식형",
        "items": {
            "미식 자체가 여행 목적": 30,
            "전국적 인지도 음식 문화": 25,
            "지역 특화 음식 다양성": 20,
            "로컬 맛집 밀집 지역": 15,
            "프랜차이즈·대중 음식": 5,
            "카페/디저트 문화": 5
        }
    },

    "N": {
        "name": "Nature / 자연형",
        "items": {
            "자연 경관 자체가 관광 목적": 30,
            "산·바다·계곡·호수 중심": 25,
            "자연 보호구역/국립공원": 20,
            "하이킹·자연 탐방": 15,
            "근교 자연 명소": 5,
            "도심 대형 공원": 5
        }
    },

    "P": {
        "name": "Planning / 계획형",
        "items": {
            "사전 예약 필수 관광지": 25,
            "시간대·시즌 영향 큼": 20,
            "동선 계획 난이도 높음": 20,
            "볼거리 분산·선별 필요": 15,
            "인기 관광지 일부 존재": 10,
            "교통의 중심지(ex: 복잡한 환승역)": 10
        }
    },

    "I": {
        "name": "Image / 사진형",
        "items": {
            "포토스팟 존재": 25,
            "야경/조명 포인트": 20,
            "독특한 풍경/건축": 20,
            "계절별 변화": 15,
            "SNS 인기": 20
        }
    },

    "S": {
        "name": "Spontaneous / 즉흥형",
        "items": {
            "돌발 이벤트 가능": 20,
            "길거리 공연/마켓": 20,
            "도보 탐방/산책": 20,
            "테마 다양성": 15,
            "좋은 접근성": 25
        }
    }
}


# ----------------------------
# 데이터 로드/저장
# ----------------------------
def load_destinations():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_destinations(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ----------------------------
# 도시 평점 계산 (구 평점 평균)
# ----------------------------
def calc_city_rating(city):
    districts = city.get("districts", {})
    ratings = []

    for d in districts.values():
        r = d.get("rating")
        if isinstance(r, (int, float)):
            ratings.append(r)

    if not ratings:
        return None

    return round(sum(ratings) / len(ratings), 1)
def calc_district_rating(district):
    attractions = district.get("attractions", {})
    ratings = []

    for a in attractions.values():
        r = a.get("rating")
        if isinstance(r, (int, float)):
            ratings.append(r)

    if not ratings:
        return None

    return round(sum(ratings) / len(ratings), 1)
def calc_region_rating(region):
    cities = region.get("cities", [])
    ratings = []

    for c in cities:
        r = c.get("rating")
        if isinstance(r, (int, float)):
            ratings.append(r)

    if not ratings:
        return None

    return round(sum(ratings) / len(ratings), 1)



# ----------------------------
# 구 점수 계산
# ----------------------------
def calc_city_score(city, importance_weights=None, drop_bottom=1):
    """
    구별 점수 기준으로 가중 평균 계산
    - 항목별 하위 N개 구 제외(drop_bottom)
    - importance_weights 적용
    - 최종 점수 정수
    """
    if importance_weights is None:
        importance_weights = {k: 1 for k in ["R","A","C","F","N","P","I","S"]}

    districts = city.get("districts", {})
    if not districts:
        return {k: 0 for k in ["R","A","C","F","N","P","I","S"]}

    city_score = {k: 0.0 for k in ["R","A","C","F","N","P","I","S"]}

    for k in city_score.keys():
        # 각 구의 항목 점수 + 중요도 적용
        scores = []
        for d_name, district in districts.items():
            score = district.get("scores", {}).get(k, 0) * importance_weights.get(k,1)
            scores.append((d_name, score))

        # drop_bottom 적용: 구 수가 충분하면 하위 N개 제외
        if len(scores) > drop_bottom:
            scores = sorted(scores, key=lambda x: x[1], reverse=True)[:-drop_bottom]

        # 총합 계산 (0 방지)
        total = sum(score for _, score in scores) or 1

        # 가중 평균 계산
        for d_name, _ in scores:
            district_score = districts.get(d_name, {}).get("scores", {}).get(k, 0)
            city_score[k] += district_score * (districts.get(d_name, {}).get("scores", {}).get(k, 0) * importance_weights.get(k,1) / total if total else 0)

    # 정수 반올림
    city_score = {k: int(round(v)) for k,v in city_score.items()}
    return city_score

# ----------------------------
# 대시보드
# ----------------------------
@admin_bp.route("/")
def dashboard():
    selected_city = request.args.get("city", "all")
    regions = load_destinations()  # JSON 불러오기

    # ----------------------------
    # 모든 도시 점수 계산 (importance_weights 적용)
    # ----------------------------
    importance_weights = {
        "R": 1.3, "A": 1.2, "C": 1.0, "F": 1.0,
        "N": 0.9, "P": 1.0, "I": 1.1, "S": 1.0
    }

    # ----------------------------
    # rating 기본값 보정 (구 / 관광지)
    # ----------------------------
    for region in regions:
        for city in region.get("cities", []):
            for district in city.get("districts", {}).values():
                district.setdefault("rating", None)
                for attraction in district.get("attractions", {}).values():
                    attraction.setdefault("rating", None)

    # ----------------------------
    # 도시 점수 & 도시 평점 계산
    # ----------------------------
    for region in regions:
        for city in region.get("cities", []):
            city["scores"] = calc_city_score(city, importance_weights)
            city["rating"] = calc_city_rating(city)

    # ----------------------------
    # 계산된 점수 JSON에 저장
    # ----------------------------
    save_destinations(regions)



    # ----------------------------
    # 도시 목록 (셀렉트용)
    # ----------------------------
    all_cities = [
        c["city"]
        for r in regions
        for c in r.get("cities", [])
    ]

    # ----------------------------
    # 선택된 도시만 필터링
    # ----------------------------
    if selected_city != "all":
        filtered_regions = []
        for region in regions:
            filtered_cities = [
                city for city in region.get("cities", [])
                if city.get("city") == selected_city
            ]
            if filtered_cities:
                filtered_regions.append({
                    "region": region["region"],
                    "cities": filtered_cities
                })
        regions = filtered_regions

    # ----------------------------
    # 대시보드 렌더링
    # ----------------------------
    return render_template(
        "dashboard.html",
        regions=regions,
        all_cities=sorted(all_cities),
        selected_city=selected_city,
        checklist=checklist
    )
@admin_bp.route(
    "/city/<city_name>/district/<district_name>/attraction/<attraction_name>/rating",
    methods=["POST"]
)
def update_attraction_rating(city_name, district_name, attraction_name):
    data = load_destinations()
    rating = request.form.get("rating")

    try:
        rating = round(float(rating), 1)
        if not (0 <= rating <= 5):
            raise ValueError
    except:
        rating = None

    city = next((c for r in data for c in r.get("cities", []) if c["city"]==city_name), None)
    if city:
        district = city.get("districts", {}).get(district_name)
        if district:
            attraction = district.get("attractions", {}).get(attraction_name)
            if attraction:
                attraction["rating"] = rating
                save_destinations(data)

    return redirect(url_for("admin.dashboard"))

@admin_bp.route(
    "/city/<city_name>/district/<district_name>/rating",
    methods=["POST"]
)
def update_district_rating(city_name, district_name):
    data = load_destinations()
    rating = request.form.get("rating")

    try:
        rating = round(float(rating), 1)
        if not (0 <= rating <= 5):
            raise ValueError
    except:
        rating = None

    city = next((c for r in data for c in r.get("cities", [])
                 if c["city"] == city_name), None)

    if city and district_name in city.get("districts", {}):
        city["districts"][district_name]["rating"] = rating
        save_destinations(data)

    return redirect(url_for("admin.dashboard"))

# ----------------------------
# 구/지구 추가
# ----------------------------
@admin_bp.route("/city/<city_name>/district/add", methods=["POST"])
def add_district(city_name):
    data = load_destinations()
    district_name = request.form.get("district_name")
    description = request.form.get("description", "")

    if not district_name:
        return redirect(url_for("admin.dashboard"))

    city = next((c for r in data for c in r.get("cities", []) if c["city"] == city_name), None)
    if not city:
        return redirect(url_for("admin.dashboard"))

    if "districts" not in city:
        city["districts"] = {}

    if district_name not in city["districts"]:
        city["districts"][district_name] = {
            "description": description,
            "views": 0,
            "rating": None,   # ⭐ 추가
            "attractions": {},
            "scores": {k:0 for k in ["R","A","C","F","N","P","I","S"]}
        }
    save_destinations(data)
    return redirect(url_for("admin.dashboard"))


# ----------------------------
# 지역 CRUD
# ----------------------------
@admin_bp.route("/region/add", methods=["POST"])
def add_region():
    data = load_destinations()
    name = request.form.get("region_name", "").strip()
    if not name: return "지역 이름 필요", 400
    if any(r["region"]==name for r in data): return "이미 존재", 400
    data.append({"region": name, "cities":[]})
    save_destinations(data)
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/region/<region_name>/delete")
def delete_region(region_name):
    data = load_destinations()
    data = [r for r in data if r["region"] != region_name]
    save_destinations(data)
    return redirect(url_for("admin.dashboard"))

# ----------------------------
# 도시 CRUD
# ----------------------------
@admin_bp.route("/city/add", methods=["POST"])
def add_city():
    data = load_destinations()
    city_name = request.form["city"]
    region_name = request.form.get("region")
    region = next((r for r in data if r["region"]==region_name), None)
    if not region:
        return "지역 선택", 400
    if any(c["city"]==city_name for c in region.get("cities", [])):
        return "이미 존재", 400

    # 🔥 이미지 처리 추가
    image_filename = None
    file = request.files.get("image")
    if file and allowed_file(file.filename):
        filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)
        upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(upload_path)
        image_filename = filename

    region["cities"].append({
        "city": city_name,
        "description": request.form.get("description",""),
        "scores": {k:0 for k in ["R","A","C","F","N","P","S","I"]},
        "rating": None,
        "views": 0,
        "image": image_filename,  # 🔥 추가
        "districts": {}
    })

    save_destinations(data)
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/city/<city_name>/edit", methods=["POST"])
def edit_city(city_name):
    data = load_destinations()
    city = next((c for r in data for c in r.get("cities", []) if c["city"] == city_name), None)

    if city:
        # 1. 설명 업데이트
        city["description"] = request.form.get("description", city.get("description",""))

        # 2. 이미지 파일 처리
        file = request.files.get("image")
        print("FILES RECEIVED:", request.files)  # ← 디버깅
        if file and allowed_file(file.filename):
            filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)
            upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            print("Saving file to:", upload_path)  # ← 디버깅
            file.save(upload_path)
            city["image"] = filename
            print("Image saved as:", city["image"])  # ← 디버깅

        save_destinations(data)

    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/city/<city_name>/delete")
def delete_city(city_name):
    data = load_destinations()
    for region in data:
        region["cities"] = [c for c in region.get("cities", []) if c["city"] != city_name]
    save_destinations(data)
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/upload_district_image/<city_name>/<district_name>", methods=["POST"])
def upload_district_image(city_name, district_name):

    if "image" not in request.files:
        return "No file part", 400

    file = request.files["image"]

    if file.filename == "":
        return "No selected file", 400

    if file and allowed_file(file.filename):

        filename = secure_filename(file.filename)

        upload_folder = current_app.config["UPLOAD_FOLDER"]
        dest_file = current_app.config["DEST_FILE"]

        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        with open(dest_file, encoding="utf-8") as f:
            data = json.load(f)

        for region in data:
            for city in region.get("cities", []):
                if city.get("city") == city_name:
                    districts = city.get("districts", {})
                    if district_name in districts:
                        district = districts[district_name]

                        if "images" not in district:
                            district["images"] = {}

                        district["images"]["main"] = filename

        with open(dest_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return redirect(url_for("admin.dashboard"))

    return "Invalid file", 400

# ----------------------------
# 구역 점수 계산
# ----------------------------
def calc_zone_score(scores):
    """구역 점수 합계"""
    return sum(scores.get(k, 0) for k in ["R","A","C","F","N","P","I","S"])


# ----------------------------
# 구 점수 업데이트
# ----------------------------
@admin_bp.route("/city/<city_name>/district/score/update", methods=["POST"])
def update_district_score(city_name):
    data = load_destinations()

    district_name = request.form.get("district")
    if not district_name:
        return redirect(url_for("admin.dashboard"))

    # 도시 찾기
    city = next((c for r in data for c in r.get("cities", []) if c["city"] == city_name), None)
    if not city:
        return redirect(url_for("admin.dashboard"))

    if "districts" not in city:
        city["districts"] = {}
    if district_name not in city["districts"]:
        # 새 구 생성
        city["districts"][district_name] = {
            "scores": {k: 0 for k in ["R","A","C","F","N","P","I","S"]},
            "rating": None,
            "attractions": {}
        }

    district = city["districts"][district_name]

    # 체크리스트 점수 가져오기
    new_scores = {k:int(request.form.get(k,0)) for k in ["R","A","C","F","N","P","I","S"]}
    district["scores"] = new_scores

    # 구 평점 가져오기
    rating = request.form.get("district_rating")
    district["rating"] = float(rating) if rating else None

    # 도시 평점 재계산 (구 평점 평균)
    ratings = [d["rating"] for d in city["districts"].values() if d.get("rating") is not None]
    city["rating"] = round(sum(ratings)/len(ratings), 1) if ratings else None

    save_destinations(data)
    return redirect(url_for("admin.dashboard"))



@admin_bp.route("/city/<city_name>/district/<district_name>/edit", methods=["POST"])
def edit_district(city_name, district_name):
    data = load_destinations()
    city = next((c for r in data for c in r.get("cities", []) if c["city"]==city_name), None)
    if city and district_name in city.get("districts", {}):
        city["districts"][district_name]["description"] = request.form.get("description","")
        save_destinations(data)
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/city/<city_name>/district/<district_name>/delete")
def delete_district(city_name, district_name):
    data = load_destinations()
    city = next((c for r in data for c in r.get("cities", []) if c["city"]==city_name), None)
    if city and district_name in city.get("districts", {}):
        del city["districts"][district_name]
        # 삭제 후 도시 점수 재계산
        city["scores"] = calc_city_score(city)
        save_destinations(data)
    return redirect(url_for("admin.dashboard"))


# ----------------------------
# 관광지 CRUD
# ----------------------------
@admin_bp.route("/city/<city_name>/district/<district_name>/attraction/<attraction_name>/edit", methods=["POST"])
def edit_attraction(city_name, district_name, attraction_name):
    data = load_destinations()
    city = next((c for r in data for c in r.get("cities", []) if c["city"]==city_name), None)
    if not city: return redirect(url_for("admin.dashboard"))

    district = city["districts"].get(district_name)
    if not district: return redirect(url_for("admin.dashboard"))

    attraction = district.get("attractions", {}).get(attraction_name)
    if not attraction: return redirect(url_for("admin.dashboard"))

    old_scores = attraction["scores"].copy()

    old_scores = attraction["scores"].copy()
    new_scores = {k:int(request.form.get(k, old_scores.get(k,0))) for k in ["R","A","C","F","N","P","S","I"]}
    for k in new_scores:
        city["scores"][k] += new_scores[k] - old_scores[k]


    attraction["description"] = request.form.get("description","")
    attraction["scores"] = new_scores
    attraction["tags"] = [t.strip() for t in request.form.get("tags","").split(",") if t.strip()]
    attraction["background"] = [b.strip() for b in request.form.get("background","").split(",") if b.strip()]

    save_destinations(data)
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/city/<city_name>/district/<district_name>/attraction/add", methods=["POST"])
def add_attraction(city_name, district_name):
    data = load_destinations()

    # 도시 찾기
    city = next((c for r in data for c in r.get("cities", []) if c["city"] == city_name), None)
    if not city:
        return redirect(url_for("admin.dashboard"))

    # 구 찾기
    district = city["districts"].get(district_name)
    if not district:
        return redirect(url_for("admin.dashboard"))

    # 폼 데이터
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("admin.dashboard"))

    description = request.form.get("description", "").strip()
    tags = [t.strip() for t in request.form.get("tags","").split(",") if t.strip()]
    background = [b.strip() for b in request.form.get("background","").split(",") if b.strip()]
    scores = {k: int(request.form.get(k, 0)) for k in ["R","A","C","F","N","P","S","I"]}

    # 관광지 추가
    district.setdefault("attractions", {})[name] = {
        "description": description,
        "tags": tags,
        "background": background,
        "scores": scores,
        "rating": None,   # ⭐ 추가
        "views": 0        # (권장)
    }


    # 도시 점수 업데이트 (기존 점수 + 새 관광지 점수)
    for k in scores:
        city["scores"][k] = city["scores"].get(k, 0) + scores[k]

    save_destinations(data)
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/city/<city_name>/district/<district_name>/attraction/<attraction_name>/delete")
def delete_attraction(city_name, district_name, attraction_name):
    data = load_destinations()
    city = next((c for r in data for c in r.get("cities", []) if c["city"]==city_name), None)
    if not city: return redirect(url_for("admin.dashboard"))

    district = city["districts"].get(district_name)
    if not district: return redirect(url_for("admin.dashboard"))

    attraction = district["attractions"].pop(attraction_name, None)
    if attraction:
        # ✅ 도시 점수 차감
        for k, v in attraction["scores"].items():
            city["scores"][k] -= v

    save_destinations(data)
    return redirect(url_for("admin.dashboard"))


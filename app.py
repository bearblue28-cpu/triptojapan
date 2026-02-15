from flask import Flask, render_template, request, session, redirect, url_for, abort
import os, json, re, uuid

from data.questions import QUESTIONS
from logic.scoring import add_score
from logic.type import make_type, TRAVEL_TYPES
from logic.logger import log_survey_result
from utils.text import display_text
from utils.data_loader import normalize_city_data
from werkzeug.utils import secure_filename

# ================================
# Flask 앱 설정
# ================================
app = Flask(__name__)
app.secret_key = "secret-key"
# ================================
# 이미지 업로드 설정
# ================================
APP_BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_BASE, "static", "uploads")
app.config["DEST_FILE"] = os.path.join(APP_BASE, "data", "destinations.json")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB 제한
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 폴더 자동 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ================================
# 관리자 Blueprint
# ================================
from admin.routes import admin_bp
app.register_blueprint(admin_bp, url_prefix="/admin")

# ================================
# JSON 경로
# ================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # routes.py 기준 상위 폴더
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "templates", "admin")
# app.py 기준
APP_BASE = os.path.dirname(os.path.abspath(__file__))
DEST_FILE = os.path.join(APP_BASE, "data", "destinations.json")

def load_destinations(include_region=True):
    with open(DEST_FILE, encoding="utf-8") as f:
        data = json.load(f)
    if include_region:
        return data
    else:
        cities = []
        for region in data:
            for city in region.get("cities", []):
                city_copy = city.copy()
                city_copy['region'] = region.get('region', '')
                cities.append(city_copy)
        return cities
    
def normalize_images():
    with open(DEST_FILE, encoding="utf-8") as f:
        data = json.load(f)

    for region in data:
        for city in region.get("cities", []):
            if "images" not in city:
                city["images"] = {}

            # image가 있으면 images.main으로 이동
            if city.get("image"):
                city["images"]["main"] = city["image"]
                del city["image"]

            # district 레벨도 동일
            for district_name, district in city.get("districts", {}).items():
                if "images" not in district:
                    district["images"] = {}
                if district.get("image"):
                    district["images"]["main"] = district["image"]
                    del district["image"]

    with open(DEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
# ================================
# 실행
# ================================
normalize_images()


def save_destinations(data):
    with open(DEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================================
# Template 공용 함수
# ================================
@app.context_processor
def inject_utils():
    return dict(display_text=display_text)

# ================================
# 홈 / 설문 / 결과 / 추천
# ================================
@app.route("/")
def home():
    return render_template("user/home.html")

@app.route("/upload_image/<city_name>/<district_name>", methods=["POST"])
def upload_image(city_name, district_name=None):
    if "image" not in request.files:
        return "No file part", 400

    file = request.files["image"]
    if file.filename == "":
        return "No selected file", 400

    if file and allowed_file(file.filename):
        filename = secure_filename(str(uuid.uuid4()) + "_" + file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # JSON 업데이트
        with open(DEST_FILE, encoding="utf-8") as f:
            data = json.load(f)

        for region in data:
            for city in region.get("cities", []):
                if city["city"] == city_name:
                    if district_name:
                        district = city.get("districts", {}).get(district_name)
                        if district:
                            if "images" not in district or not isinstance(district["images"], dict):
                                district["images"] = {}
                            district["images"]["main"] = filename
                            if "image" in district:
                                del district["image"]
                    else:
                        if "images" not in city or not isinstance(city["images"], dict):
                            city["images"] = {}
                        city["images"]["main"] = filename
                        if "image" in city:
                            del city["image"]

        # 덮어쓰기
        with open(DEST_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return "Upload success", 200

    return "Invalid file", 400

@app.route("/survey", methods=["GET", "POST"])
def survey():
    if request.method == "GET":
        session["step"] = 0
        # ✅ I 포함
        session["scores"] = {k: 0 for k in ["R","A","C","F","N","P","S","I"]}

    step = session.get("step", 0)
    scores = session.get("scores", {})

    if request.method == "POST":
        if request.form.get("back"):
            step = max(step - 1, 0)
        else:
            choice = request.form.get("choice")
            if choice:
                question = QUESTIONS[step]
                session["scores"] = add_score(scores, question, choice)
                step += 1

        session["step"] = step
        session["scores"] = scores

        if step >= len(QUESTIONS):
            log_survey_result(scores)
            return redirect(url_for("result"))

    return render_template(
        "user/survey.html",
        question=QUESTIONS[step],
        step=step + 1,
        total=len(QUESTIONS)
    )

@app.route("/reset")
def reset():
    session.clear()
    return redirect(url_for("home"))

@app.route("/result")
def result():
    scores = session.get("scores", {})
    t = make_type(scores)  # ✅ I 포함 make_type
    return render_template("user/result.html", travel_type=TRAVEL_TYPES[t])

# ================================
# City / District / Attraction
# ================================
def find_city_by_name(data, city_name):
    for region in data:
        for city in region.get("cities", []):
            if city["city"] == city_name:
                city["region"] = region["region"]
                return city
    return None

# 도시 이미지 수정
@app.route("/admin/edit_city/<city_name>", methods=["POST"])
def edit_city(city_name):
    destinations = load_destinations(include_region=True)
    city = None
    for region in destinations:
        for c in region.get("cities", []):
            if c["city"] == city_name:
                city = c
                break
        if city:
            break

    if not city:
        abort(404)

    # 설명 수정
    city["description"] = request.form.get("description", city.get("description",""))

    # 이미지 업로드
    if "image" in request.files:
        file = request.files["image"]
        if file.filename != "":
            # 안전한 파일명
            filename = secure_filename(str(uuid.uuid4()) + "_" + file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            # 기존 image 필드 삭제 후 images.main에 저장
            if "images" not in city:
                city["images"] = {}
            city["images"]["main"] = filename
            if "image" in city:
                del city["image"]

    # 저장
    with open(DEST_FILE, "w", encoding="utf-8") as f:
        json.dump(destinations, f, ensure_ascii=False, indent=2)

    return redirect(url_for("admin.edit_city", city_name=city_name))

    

@app.route("/city/<city_name>")
def city_detail(city_name):
    sort_by = request.args.get("sort", "views")  # 기본값: 인기순

    destinations = load_destinations(include_region=True)
    city = None
    for region in destinations:
        for c in region.get("cities", []):
            if c["city"] == city_name:
                city = c
                city["region"] = region["region"]
                break
        if city:
            break

    if not city:
        abort(404)

    districts = city.get("districts") or {}
    for name, info in districts.items():
        info.setdefault("description", "")
        info.setdefault("views", 0)
        info.setdefault("attractions", {})

    if sort_by == "views":
        sorted_districts = dict(
            sorted(districts.items(), key=lambda x: x[1].get("views", 0), reverse=True)
        )
    elif sort_by == "name":
        sorted_districts = dict(sorted(districts.items(), key=lambda x: x[0]))
    else:
        sorted_districts = districts

    spots = []
    for district_name, district in sorted_districts.items():
        for attr_name, attr in district.get("attractions", {}).items():
            spot = {
                "name": attr_name,
                "description": attr.get("description", ""),
                "tags": attr.get("tags", []),
                "background": attr.get("background", []),
                "district": district_name
            }
            spots.append(spot)

    return render_template(
        "user/city_detail.html",
        city=city,
        districts=sorted_districts,
        current_sort=sort_by,
        spots=spots
    )

@app.route("/city/<city_name>/<district_name>", endpoint="district_detail")
def district_detail(city_name, district_name):
    destinations = load_destinations(include_region=True)
    city = find_city_by_name(destinations, city_name)
    if not city:
        abort(404)

    district = city.get("districts", {}).get(district_name)
    if not district:
        abort(404)

    district["views"] = district.get("views", 0) + 1
    save_destinations(destinations)

    return render_template(
        "user/district_detail.html",
        city=city,
        district_name=district_name,
        district=district,
        attractions=district.get("attractions", {})
    )

@app.route("/city/<city_name>/<district_name>/<attraction_name>", endpoint="attraction_detail")
def attraction_detail(city_name, district_name, attraction_name):
    destinations = load_destinations(include_region=True)
    city = find_city_by_name(destinations, city_name)
    if not city:
        abort(404)

    district = city.get("districts", {}).get(district_name)
    if not district:
        abort(404)

    attraction = district.get("attractions", {}).get(attraction_name)
    if not attraction:
        abort(404)

    # 조회수 증가
    attraction["views"] = attraction.get("views", 0) + 1
    save_destinations(destinations)

    # 태그 처리
    all_tags = attraction.get("tags", [])
    main_tags = all_tags[:10]
    extra_tags = all_tags[10:]

    # background 처리
    backgrounds = attraction.get("background", [])  # 리스트 그대로

    return render_template(
        "user/attraction_detail.html",
        city=city,
        district_name=district_name,
        attraction_name=attraction_name,
        attraction=attraction,
        main_tags=main_tags,
        extra_tags=extra_tags,
        backgrounds=backgrounds
    )



# ================================
# 추천
# ================================
@app.route("/recommend")
def recommend():
    scores = session.get("scores")
    if not scores:
        # ✅ I 포함
        scores = {k: 1 for k in ["R","A","C","F","N","P","S","I"]}
        session["scores"] = scores

    regions = load_destinations()
    cities = []

    for region in regions:
        for city in region.get("cities", []):
            normalize_city_data(city)
            city["region"] = region.get("region", "")
            cities.append(city)

    results = []
    max_city_score = 100
    total_user_score = sum(scores.values())
    scale_factor = 1.4

    for city in cities:
        city_scores = city.get("scores", {})
        weighted_sum = sum(
            scores[k] * city_scores.get(k, 0)
            for k in scores
        )

        percent = round(
            min((weighted_sum / (total_user_score * max_city_score)) * 100 * scale_factor, 100),
            1
        )

        if percent > 0:
            city["views"] += 1

            # 🔹 region과 city 이름이 같으면 region 카드 따로 만들지 않음
            if city.get("region") == city.get("city"):
                card_name = city.get("city")
                region_for_card = ""  # 카드에는 region 표시 안 함
            else:
                card_name = f"{city.get('region')} - {city.get('city')}"
                region_for_card = city.get("region")

            results.append({
                "city": city["city"],
                "description": city.get("description", ""),
                "region": region_for_card,
                "percent": percent,
                "image": city.get("images", {}).get("main"),
                "card_name": card_name
            })

    results.sort(key=lambda x: x["percent"], reverse=True)

    save_destinations(regions)

    t = make_type(scores)  # ✅ I 포함
    return render_template(
        "user/recommend.html",
        travel_type=TRAVEL_TYPES[t],
        results=results
    )
# ================================
# 검색 (region 포함)
# ================================
@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    results = []

    if not query:
        return render_template("user/search_results.html", results=[], query=query)

    def highlight(text, q):
        return re.sub(re.escape(q), lambda m: f"<mark>{m.group(0)}</mark>", text, flags=re.IGNORECASE)

    destinations = load_destinations(include_region=True)

    for region in destinations:
        region_name = region.get("region", "")

        for city in region.get("cities", []):
            city_name = city.get("city", "")
            city_desc = city.get("description", "")
            city_views = city.get("views", 0)

            # 🔹 region=city면 region 카드 생성 생략
            if city_name == region_name:
                path_display = city_name
                region_for_card = ""
            else:
                path_display = f"{region_name} - {city_name}"
                region_for_card = region_name

            if query.lower() in city_name.lower() or query.lower() in city_desc.lower():
                results.append({
                    "type": "city",
                    "region": region_for_card,
                    "name": city_name,
                    "description": city_desc,
                    "views": city_views,
                    "path": path_display,
                    "highlighted_path": highlight(path_display, query),
                    "highlighted_description": highlight(city_desc, query),
                    "image": city.get("images", {}).get("main")
                })

            for district_name, district in city.get("districts", {}).items():
                district_desc = district.get("description", "")
                district_views = district.get("views", 0)

                full_text = f"{city_name} {district_name} {district_desc}"
                if query.lower() in full_text.lower():
                    results.append({
                        "type": "district",
                        "region": region_name,
                        "city": city_name,
                        "district": district_name,
                        "name": district_name,
                        "description": district_desc,
                        "views": district_views,
                        "path": f"{region_name} - {city_name} - {district_name}",
                        "highlighted_path": highlight(f"{region_name} - {city_name} - {district_name}", query),
                        "highlighted_description": highlight(district_desc, query)
                    })

                for attr_name, attr in district.get("attractions", {}).items():
                    attr_desc = attr.get("description", "")
                    tags = " ".join(attr.get("tags", []))
                    attr_views = attr.get("views", 0)

                    full_text_attr = f"{city_name} {district_name} {attr_name} {attr_desc} {tags}"
                    if query.lower() in full_text_attr.lower():
                        results.append({
                            "type": "attraction",
                            "region": region_name,
                            "city": city_name,
                            "district": district_name,
                            "attraction": attr_name,
                            "name": attr_name,
                            "description": attr_desc,
                            "views": attr_views,
                            "path": f"{region_name} - {city_name} - {district_name} - {attr_name}",
                            "highlighted_path": highlight(f"{region_name} - {city_name} - {district_name} - {attr_name}", query),
                            "highlighted_description": highlight(attr_desc, query)
                        })
    seen = set()
    unique_results = []
    for r in results:
        key = (r["type"], r.get("city"), r.get("district"), r.get("attraction"))
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
    results = unique_results

    PRIORITY = {"region": 5, "city": 4, "district": 3, "attraction": 2}
    results.sort(key=lambda x: (PRIORITY.get(x["type"], 0), x.get("views", 0)), reverse=True)

    return render_template("user/search_results.html", results=results, query=query)

# ================================
# 실행
# ================================
if __name__ == "__main__":
    app.run(debug=True)

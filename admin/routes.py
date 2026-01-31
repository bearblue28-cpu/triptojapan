import json, os
from flask import Blueprint, render_template, request, redirect, url_for

# =================================================
# Blueprint
# =================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "templates", "admin")

admin_bp = Blueprint(
    "admin",
    __name__,
    template_folder=TEMPLATE_FOLDER,
    url_prefix="/admin"
)

# =================================================
# JSON 파일 경로
# =================================================
DEST_FILE = os.path.join(BASE_DIR, "data", "destinations.json")

def load():
    if not os.path.exists(DEST_FILE):
        return []
    with open(DEST_FILE, encoding="utf-8") as f:
        return json.load(f)

def save(data):
    with open(DEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =================================================
# 관리자 대시보드
# =================================================
@admin_bp.route("/")
def dashboard():
    return render_template("dashboard.html", destinations=load())

# =================================================
# 도시 추가/삭제
# =================================================
@admin_bp.route("/city/add", methods=["POST"])
def add_city():
    data = load()
    city_name = request.form["city"]
    data.append({
        "city": city_name,
        "description": request.form.get("description",""),
        "scores": {k:int(request.form.get(k,0)) for k in ["R","A","C","F","N","P","S"]},
        "districts": {}
    })
    save(data)
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/city/<city_name>/delete")
def delete_city(city_name):
    data = load()
    data = [c for c in data if c["city"] != city_name]
    save(data)
    return redirect(url_for("admin.dashboard"))

# =================================================
# 구/지구 추가/삭제/수정
# =================================================
@admin_bp.route("/city/<city_name>/district/add", methods=["POST"])
def add_district(city_name):
    data = load()
    city = next(c for c in data if c["city"] == city_name)
    name = request.form["district"]
    city["districts"][name] = {
        "description": request.form.get("description",""),
        "attractions": {}
    }
    save(data)
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/city/<city_name>/district/<district_name>/delete")
def delete_district(city_name, district_name):
    data = load()
    city = next(c for c in data if c["city"]==city_name)
    if district_name in city["districts"]:
        del city["districts"][district_name]
    save(data)
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/city/<city_name>/district/<district_name>/edit", methods=["POST"])
def edit_district(city_name, district_name):
    data = load()
    city = next(c for c in data if c["city"] == city_name)
    district = city["districts"].get(district_name)
    if district:
        district["description"] = request.form.get("description", district["description"])
        save(data)
    return redirect(url_for("admin.dashboard"))

# =================================================
# 관광지 추가/삭제/수정
# =================================================
@admin_bp.route("/city/<city_name>/district/<district_name>/attraction/add", methods=["POST"])
def add_attraction(city_name, district_name):
    data = load()
    city = next(c for c in data if c["city"] == city_name)
    district = city["districts"][district_name]
    name = request.form["name"]
    district["attractions"][name] = {
        "description": request.form.get("description",""),
        "tags": [t.strip() for t in request.form.get("tags","").split(",") if t.strip()],
        "background": [m.strip() for m in request.form.get("background","").split(",") if m.strip()]
    }
    save(data)
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/city/<city_name>/district/<district_name>/attraction/<attraction_name>/delete")
def delete_attraction(city_name, district_name, attraction_name):
    data = load()
    city = next(c for c in data if c["city"] == city_name)
    district = city["districts"][district_name]
    if attraction_name in district["attractions"]:
        del district["attractions"][attraction_name]
        save(data)
    return redirect(url_for("admin.dashboard"))

# -------------------
# 관광지 세부 삭제 (설명, 태그, 배경)
# -------------------
@admin_bp.route("/city/<city_name>/district/<district_name>/attraction/<attraction_name>/delete_field/<field>")
def delete_attraction_field(city_name, district_name, attraction_name, field):
    """
    field: description / tags / background
    """
    data = load()
    city = next(c for c in data if c["city"] == city_name)
    district = city["districts"].get(district_name, {})
    attraction = district.get("attractions", {}).get(attraction_name)

    if not attraction:
        return "관광지를 찾을 수 없습니다.", 404

    if field in attraction:
        if isinstance(attraction[field], list):
            attraction[field] = []
        else:
            attraction[field] = ""
        save(data)

    return redirect(url_for("admin.dashboard"))

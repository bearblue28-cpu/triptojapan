from flask import Flask, render_template, request, session, redirect, url_for
import os, json

from data.questions import QUESTIONS
from logic.scoring import add_score
from logic.type import make_type, TRAVEL_TYPES
from logic.logger import log_survey_result
from utils.text import display_text

# ================================
# Flask 앱 설정
# ================================
app = Flask(__name__)
app.secret_key = "secret-key"

# ================================
# JSON 경로
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEST_FILE = os.path.join(BASE_DIR, "data", "destinations.json")

def load_destinations():
    if not os.path.exists(DEST_FILE):
        return []
    with open(DEST_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_destinations(data):
    with open(DEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================================
# 관리자 Blueprint
# ================================
from admin.routes import admin_bp
app.register_blueprint(admin_bp, url_prefix="/admin")

# ================================
# Template 공용 함수
# ================================
@app.context_processor
def inject_utils():
    return dict(display_text=display_text)

# -----------------------------
# 홈 페이지
# -----------------------------
@app.route("/")
def home():
    return render_template("user/home.html")  # 검색창 + 홈 버튼 + 설문 버튼

# -----------------------------
# 설문 페이지
# -----------------------------
@app.route("/survey", methods=["GET", "POST"])
def survey():
    if request.method == "GET":
        session["step"] = 0
        session["scores"] = {}

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
        "user/survey.html",  # 기존 index.html 대신 survey.html로 분리
        question=QUESTIONS[step],
        step=step + 1,
        total=len(QUESTIONS)
    )


# ================================
# 설문 결과
# ================================
@app.route("/result")
def result():
    scores = session.get("scores", {})
    t = make_type(scores)
    return render_template(
        "user/result.html",
        travel_type=TRAVEL_TYPES[t]
    )

# ================================
# 추천 (가중치 보정 적용)
# ================================
@app.route("/recommend")
def recommend():
    # 세션 점수
    scores = session.get("scores")
    if not scores:
        destinations = load_destinations()
        if not destinations:
            return redirect(url_for("survey"))
        scores = {k: 1 for k in ["R","A","C","F","N","P","S"]}
        session["scores"] = scores

    destinations = load_destinations()
    results = []

    max_city_score = 5  # 각 항목 5점 만점
    total_user_score = sum(scores.values())  # 사용자 점수 총합
    scale_factor = 1.4  # 매칭율 보정 상수 (조정 가능)

    for dest in destinations:
        city_scores = dest.get("scores", {})

        # 가중 합 계산
        weighted_sum = 0
        for trait, user_val in scores.items():
            city_val = city_scores.get(trait, 0)
            weighted_sum += user_val * city_val

        # 보정 적용
        percent = round(
            min((weighted_sum / (total_user_score * max_city_score)) * 100 * scale_factor, 100),
            1
        )

        if percent > 0:
            results.append({
                "city": dest.get("city", ""),
                "description": dest.get("description", ""),
                "percent": percent
            })

    # 매칭율 높은 순 정렬
    results.sort(key=lambda x: x["percent"], reverse=True)

    t = make_type(scores)

    return render_template(
        "user/recommend.html",
        travel_type=TRAVEL_TYPES[t],
        results=results
    )




# ================================
# 검색
# ================================
@app.route("/search")
def search():
    query = request.args.get("q", "").lower().strip()
    results = []

    for dest in load_destinations():
        if query in dest.get("city", "").lower():
            results.append({
                "type": "city",
                "name": dest.get("city", ""),
                "description": dest.get("description", "")
            })

    return render_template("user/search_results.html", results=results, query=query)

# ================================
# 도시 상세
# ================================
@app.route("/city/<city_name>")
def city_detail(city_name):
    city = next((c for c in load_destinations() if c.get("city") == city_name), None)
    if not city:
        return redirect(url_for("survey"))

    return render_template(
        "user/city_detail.html",
        city=city,
        districts=city.get("districts", {})  # 없으면 빈 dict
    )

# ================================
# 구/지구 상세
# ================================
@app.route("/city/<city_name>/<district_name>")
def district_detail(city_name, district_name):
    destinations = load_destinations()
    city = next((c for c in destinations if c.get("city") == city_name), None)
    if not city:
        return redirect(url_for("survey"))

    districts = city.get("districts", {})
    district = districts.get(district_name)
    if not district:
        return redirect(url_for("city_detail", city_name=city_name))

    return render_template(
        "user/district_detail.html",
        city=city,
        district_name=district_name,
        district=district,
        attractions=district.get("attractions", {})
    )

# ================================
# 명소 상세
# ================================
@app.route("/city/<city_name>/<district_name>/<attraction_name>")
def attraction_detail(city_name, district_name, attraction_name):
    city = next((c for c in load_destinations() if c.get("city") == city_name), None)
    if not city:
        return redirect(url_for("survey"))

    district = city.get("districts", {}).get(district_name)
    if not district:
        return redirect(url_for("city_detail", city_name=city_name))

    attraction = district.get("attractions", {}).get(attraction_name)
    if not attraction:
        return redirect(url_for("district_detail", city_name=city_name, district_name=district_name))

    return render_template(
        "user/attraction_detail.html",
        city=city,
        district_name=district_name,
        attraction_name=attraction_name,
        attraction=attraction
    )

# ================================
# 설문 초기화
# ================================
@app.route("/reset")
def reset():
    session.clear()
    return redirect(url_for("survey"))
    

# ================================
# 실행
# ================================
if __name__ == "__main__":
    app.run(debug=True)

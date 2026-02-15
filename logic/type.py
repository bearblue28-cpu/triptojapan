import random

TRAVEL_TYPES = {
    "RA": "힐링_액티비티형",
    "RC": "조용한_문화형",
    "RF": "힐링_미식형",
    "AP": "계획적인_액티비티형",
    "AS": "즉흥_액티비티형",
    "CP": "계획적인_관광형",
    "CS": "자유로운_관광형",
    "FP": "미식_플래너",
    "FS": "자유_미식가",
    "RI": "힐링_사진형",
    "AI": "액티비티_사진형",
    "CI": "문화_사진형",
    "FI": "미식_사진형",
}

def make_type(scores):
    """
    사용자 점수(scores)를 기반으로 두 글자 여행 유형 결정.
    사진형(I) 포함, 동점일 경우 랜덤 선택.
    """
    # 첫 글자 후보: 기존 + 사진형
    first_candidates = ["R", "A", "C", "F", "I"]
    
    # 두 번째 글자 후보 맵
    second_candidates_map = {
        "R": ["A", "F", "I"],  # 힐링 → 액티비티/미식/사진형
        "A": ["P", "S", "I"],  # 액티비티 → 계획/즉흥/사진형
        "C": ["P", "S", "I"],  # 문화 → 계획/자유/사진형
        "F": ["P", "S", "I"],  # 미식 → 계획/자유/사진형
        "I": ["R", "A", "C", "F"],  # 사진형 → 기존 성향과 매칭
    }

    # 첫 글자 결정
    first_scores = {k: scores.get(k, 0) for k in first_candidates}
    max_first_score = max(first_scores.values())
    first_max_candidates = [k for k, v in first_scores.items() if v == max_first_score]
    first = random.choice(first_max_candidates)

    # 두 번째 글자 결정
    second_candidates = second_candidates_map.get(first, ["A"])
    second_scores = {k: scores.get(k, 0) for k in second_candidates}
    max_second_score = max(second_scores.values())
    second_max_candidates = [k for k, v in second_scores.items() if v == max_second_score]
    second = random.choice(second_max_candidates)

    t = first + second
    return t if t in TRAVEL_TYPES else "RA"  # 안전 장치

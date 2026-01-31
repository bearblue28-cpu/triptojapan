def make_type(scores):
    # 1글자씩 결정
    first = "R" if scores.get("R",0) >= scores.get("A",0) else "A"
    
    # 두 번째 글자 결정
    # C/F (문화/미식), P/S (계획/즉흥) 등 TRAVEL_TYPES와 맞춰서 선택
    if first == "R":  # 힐링
        second = "A" if scores.get("A",0) > scores.get("F",0) else "F"
    elif first == "A":  # 액티비티
        second = "P" if scores.get("P",0) >= scores.get("S",0) else "S"
    elif first == "C":  # 관광
        second = "P" if scores.get("P",0) >= scores.get("S",0) else "S"
    elif first == "F":  # 미식
        second = "P" if scores.get("P",0) >= scores.get("S",0) else "S"
    else:
        second = "A"  # 안전 장치

    t = first + second
    # TRAVEL_TYPES에 없는 경우 안전 장치
    return t if t in TRAVEL_TYPES else "RA"



TRAVEL_TYPES = {
    "RA": "힐링_액티비티형",   # 휴식 + 활동
    "RC": "조용한_문화형",
    "RF": "힐링_미식형",

    "AP": "계획적인_액티비티형",
    "AS": "즉흥_액티비티형",

    "CP": "계획적인_관광형",
    "CS": "자유로운_관광형",

    "FP": "미식_플래너",
    "FS": "자유_미식가",
}

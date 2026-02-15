import json, os, shutil, datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEST_FILE = os.path.join(DATA_DIR, "destinations.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backup")
MAX_BACKUPS = 20  # 원하는 최대 백업 수

# ----------------------------------------
# 오래된 백업 정리
# ----------------------------------------
def cleanup_backups(limit=MAX_BACKUPS):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    files = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith("destinations_")],
        reverse=True
    )
    for f in files[limit:]:
        os.remove(os.path.join(BACKUP_DIR, f))

# ----------------------------------------
# 저장 + 자동 백업
# ----------------------------------------
def save_destinations(data):
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # 1️⃣ 백업 파일명 생성
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"destinations_{timestamp}.json")

    # 2️⃣ 기존 destinations.json 백업
    if os.path.exists(DEST_FILE):
        shutil.copy2(DEST_FILE, backup_file)

    # 3️⃣ 새 데이터 저장
    with open(DEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 4️⃣ 오래된 백업 정리
    cleanup_backups()

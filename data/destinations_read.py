import json
import os
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEST_FILE = os.path.join(DATA_DIR, "destinations.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backup")  # destinations_admin.py와 동일하게 맞춤

# =================================================
# JSON 데이터 로드
# =================================================
def load_destinations():
    """
    destinations.json 로드.
    파일이 없거나 깨진 경우, 최신 백업에서 복원
    """
    if not os.path.exists(DEST_FILE):
        return restore_latest_backup()

    try:
        with open(DEST_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError:
        # JSON 오류 시 최신 백업에서 복원
        return restore_latest_backup()


# =================================================
# 최신 백업 복원
# =================================================
def restore_latest_backup():
    """
    백업 폴더에서 가장 최신 백업 파일을 찾아 destinations.json으로 복원
    """
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        return []

    backups = sorted(
        glob.glob(os.path.join(BACKUP_DIR, "destinations_*.json")),
        reverse=True
    )

    if not backups:
        # 백업이 없으면 빈 리스트 반환
        return []

    latest = backups[0]

    with open(latest, encoding="utf-8") as f:
        data = json.load(f)

    # 복원
    with open(DEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return data

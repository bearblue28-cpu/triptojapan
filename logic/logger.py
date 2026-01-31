import logging
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "survey.log")

# logs 폴더 없으면 생성
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("survey")
logger.setLevel(logging.INFO)

handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)


def log_survey_result(scores, travel_type=None):
    logger.info({
        "scores": scores,
        "type": travel_type
    })

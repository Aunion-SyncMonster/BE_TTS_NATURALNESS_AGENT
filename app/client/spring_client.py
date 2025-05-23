import logging
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from app.schema.tts_naturalness_dto import TtsNaturalnessResult

env_path = (Path(__file__).resolve().parents[1] / "config" / ".env")
load_dotenv(dotenv_path=env_path)
TTS_NATURALNESS_BE_URL = os.getenv("TTS_NATURALNESS_BE_URL")
RESULT_URL = f"{TTS_NATURALNESS_BE_URL}/api/tts-naturalness"


def send_result_to_be(result: TtsNaturalnessResult):
    try:
        payload = result.model_dump()
        resp = requests.post(RESULT_URL, json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        logging.info(f"Failed to send result to Spring: {e}")
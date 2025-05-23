import logging
import os
from pydub import AudioSegment
import io

import re
from pathlib import Path

from dotenv import load_dotenv
import requests

from app.util.exception import S3UploadError, TtsError
from app.util.s3 import upload_s3
from app.web_socket.notifier import notify_progress

env_path = (Path(__file__).resolve().parents[2] / "config" / ".env")

load_dotenv(dotenv_path=env_path)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_URL = os.getenv("ELEVENLABS_URL")

voice_ids = {
    "Chi": os.getenv("VOICE_ID_CHI"),
    "Su": os.getenv("VOICE_ID_SU"),
    "He": os.getenv("VOICE_ID_HE"),
    "Je": os.getenv("VOICE_ID_JE"),
    "Chan": os.getenv("VOICE_ID_CHAN"),
    "Yoon": os.getenv("VOICE_ID_YOON"),
    "Bin": os.getenv("VOICE_ID_BIN"),
    "JangHo": os.getenv("VOICE_ID_JANGHO"),
    "Manbo": os.getenv("VOICE_ID_MANBO"),
    "Aria": os.getenv("VOICE_ID_ARIA"),
}

headers = {
    "xi-api-key": ELEVENLABS_API_KEY,
    "Content-Type": "application/json",
    "Accept": "audio/wav"
}

def _split_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def text_to_speech_elevenlabs(translated_text: str, task_name: str, stability: float, similarity_boost: float, style: float, use_speaker_boost: bool, voice_id: str):
    total_url = ELEVENLABS_URL + f"/{voice_ids[voice_id]}"

    data = {
        "text": translated_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost,
            "speed": 1
        }
    }

    try:
        response = requests.post(total_url, headers=headers, json=data)
    except requests.exceptions.RequestException as e:
        logging.error(f"ElevenLabs API error: {e}")
        raise TtsError(f"ElevenLabs API error: {e}")

    if response.status_code == 200:
        # ElevenLabs 응답(response.content)은 MP3
        mp3_bytes = io.BytesIO(response.content)
        audio = AudioSegment.from_file(mp3_bytes, format="mp3")

        # WAV로 변환
        wav_bytes = io.BytesIO()
        audio.export(wav_bytes, format="wav")
        wav_bytes.seek(0)
        
        filename = f"translated_video_{task_name}.wav"

        key = f"tts_naturalness/{task_name}/{filename}"
        try:
            upload_s3(key, wav_bytes.read(), "audio/wav")

            return key
        except S3UploadError as e:
            raise e
    else:
        logging.error(f"Elevenlabs tts error: {response.status_code}")
        raise TtsError(f"Elevenlabs tts error: {response.status_code}")


async def compute_tts_api(
    task_name: str,
    request,          # TtsNaturalnessRequest
    existing_key: str
) -> str:
    """1) TTS API 호출, S3 키 반환"""
    if existing_key is None and request.tts_api_type.name == "ELEVENLABS":
        try:
            return text_to_speech_elevenlabs(
                translated_text=request.translated_text,
                task_name=task_name,
                stability=request.stability,
                similarity_boost=request.similarity_boost,
                style=request.style,
                use_speaker_boost=request.use_speaker_boost,
                voice_id=request.voice_id
            )
        except Exception as e:
            logging.error(f"TTS API error: {e}")
            await notify_progress(task_name, -1, error=str(e))
            raise TtsError(e)
    return existing_key


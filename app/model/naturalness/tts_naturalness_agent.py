from tempfile import mkstemp
import logging
import os
import librosa
import soundfile as sf
from pathlib import Path

import torch

from app.core import models
from app.util.exception import EvaluationError
from app.util.s3 import s3_client, S3_BUCKET


def _download_to_tmp(key: str) -> str:
    _, ext = os.path.splitext(key)
    fd, path = mkstemp(suffix=ext or ".wav", prefix="tts_eval_")
    os.close(fd)
    obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
    with open(path, "wb") as f:
        f.write(obj["Body"].read())
    return path

def _cleanup(*paths: str) -> None:
    for p in paths:
        try:
            os.remove(p)
        except OSError:
            logging.warning(f"Temp file cleanup failed: {p}")

async def compute_mos(
    task_name: str,
    translated_key: str,
) -> float:
    mp3_path = _download_to_tmp(translated_key)
    wav_path = mp3_path + ".wav"

    # librosa 로 MP3 읽고, soundfile로 WAV 쓰기
    audio, sr = librosa.load(mp3_path, sr=None)
    sf.write(wav_path, audio, sr)
    logging.info(f"Downloaded for MOS eval: {wav_path}")
    try:
        mos = models.utmos_model.predict(input_path=wav_path, device=torch.device("cpu"), num_workers=0)
    except Exception as e:
        logging.error(f"MOS evaluation error: {e}")
        _cleanup(mp3_path, wav_path)
        raise EvaluationError(e)
    _cleanup(mp3_path, wav_path)
    return float(mos)


async def compute_sc(
    task_name: str,
    original_key: str,
    translated_key: str,
) -> float:
    # 1) S3에서 파일 다운로드
    orig_tmp = _download_to_tmp(original_key)
    gen_tmp  = _download_to_tmp(translated_key)

    # 2) 절대 경로로 변환하고, POSIX 스타일 슬래시 사용
    orig_path = Path(orig_tmp).resolve().as_posix()
    gen_path  = Path(gen_tmp).resolve().as_posix()

    logging.info(f"SC evaluation paths: {orig_path}, {gen_path}")

    try:
        # 3) verify_files에 “있는 그대로” 넘기기 (큰따옴표 제거)
        sc_score, _ = models.speaker_recognizer.verify_files(orig_path, gen_path)
        result = float(sc_score.item())
        return result

    except Exception as e:
        logging.error(f"SC evaluation error: {e}")
        raise EvaluationError(e)

    finally:
        # 4) 임시 파일 정리
        _cleanup(orig_tmp, gen_tmp)
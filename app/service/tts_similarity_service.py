import logging
import time
from typing import Optional

from app.client.spring_client import send_result_to_be
from app.model.tts.elevenlabs import compute_tts_api
from app.schema.tts_naturalness_dto import (
    TtsNaturalnessRequest,
    TtsNaturalnessResult,
)
from app.util.exception import EvaluationError, TtsError
from app.util.s3 import make_public_url
from app.web_socket.notifier import notify_progress

from app.model.naturalness.tts_naturalness_agent import (
    compute_mos,
    compute_sc,
)


def _build_and_send(
    task_name: str,
    request: TtsNaturalnessRequest,
    original_key: str,
    translated_key: Optional[str],
    mos_score: float,
    sc_score: float,
    inference_time: float,
):
    result = TtsNaturalnessResult(
        total_project_id=request.total_project_id,
        input_original_key=make_public_url(original_key),
        result_translation_text_key=make_public_url(request.translated_text_key),
        output_voice_key=make_public_url(translated_key) or "",
        mos_score=mos_score,
        sc_score=sc_score,
        tts_api_type=request.tts_api_type,
        inference_time=inference_time,
        status="SUCCESS",
        task_name=task_name,
        stability=request.stability,
        similarity_boost=request.similarity_boost,
        style=request.style,
        use_speaker_boost=request.use_speaker_boost,
        voice_id=request.voice_id,
    )

    logging.info(f"task_name completed: {task_name}")
    logging.info(f"result: {result}")

    send_result_to_be(result)


async def run_tts_naturalness(
    task_name: str,
    request: TtsNaturalnessRequest,
    original_key: str,
    translated_key: Optional[str],
) -> None:
    logging.info(f"🔄 Starting TTS naturalness task: {task_name}")
    start_time = time.perf_counter()

    # 0% 알림
    await notify_progress(task_name, 0)

    # 3단계 함수 모음
    steps = [
        ("TTS API", lambda input_key: compute_tts_api(task_name, request, input_key)),
        ("MOS",     lambda input_key: compute_mos(task_name, input_key)),
        ("SC",      lambda input_key: compute_sc(task_name, original_key, input_key)),
    ]
    total_steps = len(steps)

    current_key = translated_key
    mos_score = sc_score = 0.0

    for idx, (label, fn) in enumerate(steps):
        try:
            if label == "TTS API":
                current_key = await fn(current_key)
            elif label == "MOS":
                mos_score   = await fn(current_key)
            else:
                sc_score    = await fn(current_key)
        except TtsError as e:
            logging.error(f"{label} 단계 실패: {e}")
            await notify_progress(task_name, -1, error=str(e))
            _build_and_send(
                task_name, request, original_key, None, 0.0, 0.0, 0.0
            )
            return
        except EvaluationError as e:
            logging.error(f"{label} 단계 실패: {e}")
            await notify_progress(task_name, -1, error=str(e))
            _build_and_send(
                task_name, request, original_key, translated_key, 0.0, 0.0, 0.0
            )
            return

        # 진행률 계산 및 알림
        progress = int((idx + 1) / total_steps * 100)
        await notify_progress(task_name, progress)

    # 최종 결과 전송
    inference_time = time.perf_counter() - start_time
    _build_and_send(
        task_name,
        request,
        original_key,
        current_key,
        mos_score,
        sc_score,
        inference_time
    )
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form
from pydantic import ValidationError

from app.schema.tts_naturalness_dto import TtsNaturalnessRequest, TtsNaturalnessResponse, TtsType
from app.service.tts_similarity_service import run_tts_naturalness
from app.util.exception import S3UploadError
from app.util.s3 import upload_s3
from app.util.task_utils import generate_task_name

router = APIRouter()

@router.post("/tts-naturalness", response_model=TtsNaturalnessResponse)
async def submit_tts_naturalness(
    background_tasks: BackgroundTasks,
    translated_text: UploadFile = File(...),
    original_voice: UploadFile = File(...),
    translated_voice: Optional[UploadFile] = File(None),
    total_project_id: int = Form(...),
    tts_api_type: TtsType = Form(...),
    stability: float = Form(...),
    similarity_boost: float = Form(...),
    style: float = Form(...),
    use_speaker_boost: bool = Form(...),
    voice_id: str = Form(...),
):
    """
    translated_voice는 선택적(Optional)입니다.
    """
    task_name = generate_task_name()
    logging.info(f"[TTS] queued task: {task_name}")

    try:
        raw_translated_text = await translated_text.read()
        translated_txt_key = f"tts_naturalness/{task_name}/{translated_text.filename}"
        upload_s3(translated_txt_key, raw_translated_text, translated_text.filename)

        translated_text = raw_translated_text.decode("utf-8")

        request = TtsNaturalnessRequest(
            translated_text=translated_text,
            translated_text_key=translated_txt_key,
            tts_api_type=tts_api_type,
            total_project_id=total_project_id,
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            use_speaker_boost=use_speaker_boost,
            voice_id=voice_id,
        )
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=ve.errors())


    original_key = f"tts_naturalness/{task_name}/{original_voice.filename}"
    original_bytes = await original_voice.read()
    try:
        upload_s3(original_key, original_bytes, original_voice.content_type)
    except S3UploadError as e:
        raise HTTPException(status_code=500, detail=f"S3 upload error (original): {e}")

    translated_key: Optional[str] = None
    if translated_voice is not None:
        translated_key = f"tts_naturalness/{task_name}/{translated_voice.filename}"
        translated_bytes = await translated_voice.read()
        try:
            upload_s3(translated_key, translated_bytes, translated_voice.content_type)
        except S3UploadError as e:
            raise HTTPException(status_code=500, detail=f"S3 upload error (translated): {e}")

    try:
        background_tasks.add_task(
            run_tts_naturalness,
            task_name,
            request,
            original_key,
            translated_key
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue tts naturalness: {e}")

    return TtsNaturalnessResponse(task_name=task_name, status="processing")

from enum import Enum

from pydantic import BaseModel

class TtsType(str, Enum):
    ELEVENLABS = "ELEVENLABS"

class TtsNaturalnessRequest(BaseModel):
    translated_text: str
    translated_text_key: str
    tts_api_type: TtsType
    total_project_id: int
    stability: float
    similarity_boost: float
    style: float
    use_speaker_boost: bool
    voice_id: str

class TtsNaturalnessResponse(BaseModel):
    task_name: str
    status: str

class TtsNaturalnessResult(BaseModel):
    total_project_id: int
    input_original_key: str
    result_translation_text_key: str
    output_voice_key: str
    mos_score: float
    sc_score: float
    tts_api_type: TtsType
    inference_time: float
    status: str
    task_name: str
    stability: float
    similarity_boost: float
    style: float
    use_speaker_boost: bool
    voice_id: str

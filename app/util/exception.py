class S3UploadError(Exception):
    """S3 업로드 실패 시 던지는 예외"""
    pass

class TtsError(Exception):
    """TTS API 실패 응답 시 던지는 예외"""
    pass

class EvaluationError(Exception):
    """Evaluation 실패 시 던지는 예외"""
    pass
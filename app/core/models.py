import logging

from speechbrain.inference import SpeakerRecognition
import utmosv2
import torch


speaker_recognizer = None
utmos_model = None

def init_models():
    global speaker_recognizer, utmos_model

    logging.info("🔄 Loading models at startup…")

    # 1) SpeechBrain 스피커 인식 모델
    speaker_recognizer = SpeakerRecognition.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        run_opts={"device": "cpu"},
    )

    logging.info(f"torch.__version__: {torch.__version__}")
    utmos_model = utmosv2.create_model(pretrained=True, device="cpu")

    logging.info("✅ All models loaded successfully")

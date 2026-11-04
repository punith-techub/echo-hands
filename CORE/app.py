"""
ECHOHANDS - FastAPI Application
Real-Time Indian Sign Language to Text & Speech Translator Server
Serves ASTRA-VISION Tactical Dark Cockpit HUD and high-performance REST APIs.
"""

import os
import io
import time
import base64
from typing import Optional, List, Dict, Any
import torch
from pydantic import BaseModel
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import numpy as np
import cv2

from CORE.sign_knowledge import (
    ALPHANUMERIC_CLASSES,
    ALL_SIGNS,
    get_all_alphanumeric_classes,
    get_all_words,
    get_sign_info
)
from CORE.multi_sign_engine import MultiSignEngine
from CORE.vision import DualBrainVisionEngine
from CORE.sentence_synthesizer import SentenceSynthesizer
from CORE.speech_engine import SpeechEngine
from CORE.online_learner import OnlineLearner

def encode_rgb_to_base64(rgb_np: np.ndarray) -> str:
    _, buffer = cv2.imencode(".jpg", cv2.cvtColor(rgb_np, cv2.COLOR_RGB2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    return base64.b64encode(buffer).decode("utf-8")

def decode_base64_to_rgb(b64_str: str) -> np.ndarray:
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    img_bytes = base64.b64decode(b64_str)
    pil = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return np.array(pil)

# Directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")

app = FastAPI(
    title="ECHOHANDS ISL Neural Engine",
    description="Real-Time Indian Sign Language to Text/Speech Translator (Phase-1)",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize Singletons
sign_engine = MultiSignEngine(target_size=(224, 224))
vision_engine = DualBrainVisionEngine()
synthesizer = SentenceSynthesizer()
speech_engine = SpeechEngine()
online_learner = OnlineLearner(model=vision_engine.model, memory_trainer=vision_engine.memory)

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve ASTRA-VISION tactical HUD index page."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>ECHOHANDS Server Active. UI initializing...</h1>")

@app.get("/api/health")
async def health_check():
    """Engine health, device status, and prototype counts."""
    return {
        "status": "healthy",
        "engine": "ECHOHANDS Dual-Brain Hybrid ISL Engine",
        "device": str(vision_engine.device),
        "alphanumeric_classes": len(ALPHANUMERIC_CLASSES),
        "prototype_memory_words": vision_engine.memory.count(),
        "version": "1.0.0"
    }

@app.get("/api/vocabulary")
async def get_vocabulary():
    """Full catalog of 35 Alphanumerics and 60+ ISL Words."""
    return {
        "alphanumerics": [get_sign_info(c) for c in get_all_alphanumeric_classes()],
        "words": [get_sign_info(w) for w in get_all_words()]
    }

@app.get("/api/metrics")
async def get_metrics():
    """Retrieve benchmark training metrics, F1 scores, confusion matrix and ROC URLs."""
    metrics_file = os.path.join(MODELS_DIR, "metrics.json")
    cm_file = os.path.join(MODELS_DIR, "confusion_matrix.png")
    roc_file = os.path.join(MODELS_DIR, "roc_curve.png")

    if not os.path.exists(metrics_file):
        raise HTTPException(status_code=404, detail="Benchmark metrics not yet computed.")

    import json
    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics_data = json.load(f)

    metrics_data["has_confusion_matrix"] = os.path.exists(cm_file)
    metrics_data["has_roc_curve"] = os.path.exists(roc_file)
    metrics_data["confusion_matrix_url"] = "/api/metrics/confusion-matrix"
    metrics_data["roc_curve_url"] = "/api/metrics/roc-curve"

    return metrics_data

@app.get("/api/metrics/confusion-matrix")
async def get_confusion_matrix_img():
    cm_file = os.path.join(MODELS_DIR, "confusion_matrix.png")
    if os.path.exists(cm_file):
        return FileResponse(cm_file, media_type="image/png")
    raise HTTPException(status_code=404, detail="Confusion matrix image not found.")

@app.get("/api/metrics/roc-curve")
async def get_roc_curve_img():
    roc_file = os.path.join(MODELS_DIR, "roc_curve.png")
    if os.path.exists(roc_file):
        return FileResponse(roc_file, media_type="image/png")
    raise HTTPException(status_code=404, detail="ROC curve image not found.")

@app.get("/api/sample-images")
async def get_sample_images():
    """List sample test images available for instant one-click testing."""
    sample_files = []
    if os.path.exists(DATA_DIR):
        for fname in sorted(os.listdir(DATA_DIR)):
            if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                sample_files.append({
                    "filename": fname,
                    "url": f"/api/sample-images/{fname}",
                    "name": fname.rsplit(".", 1)[0].replace("_", " ").title()
                })
    return {"samples": sample_files}

@app.get("/api/sample-images/{filename}")
async def serve_sample_image(filename: str):
    file_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail=f"Sample file {filename} not found.")

@app.post("/api/predict")
async def predict_gesture(
    file: UploadFile = File(...),
    preferred_brain: Optional[str] = Form(None)
):
    """
    Primary ECHOHANDS Translation Pipeline:
    1. Multi-sign spatial reading-order extraction & zoom cropping
    2. Dual-Brain vision inference + Grad-CAM heatmap generation
    3. Sentence synthesis (fingerspelling aggregation + SOV to SVO translation)
    4. Bilingual TTS metadata generation
    """
    start_time = time.time()
    try:
        contents = await file.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
        rgb_np = np.array(pil_image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")

    # 1. Extract sign regions in reading order
    regions = sign_engine.extract_signs(rgb_np)
    
    # 2. Predict each region
    region_results = []
    raw_tokens = []

    for reg in regions:
        pred = vision_engine.predict_sign(
            reg.crop,
            is_dual_hand=reg.is_dual_hand,
            preferred_brain=preferred_brain
        )
        raw_tokens.append(pred["predicted_sign"])
        region_results.append({
            "index": reg.index,
            "bbox": list(reg.bbox),
            "is_dual_hand": reg.is_dual_hand,
            "aspect_ratio": round(reg.aspect_ratio, 2),
            "crop_base64": f"data:image/jpeg;base64,{encode_rgb_to_base64(reg.crop)}",
            **pred
        })

    # 3. Synthesize sentence
    synthesized = synthesizer.synthesize(raw_tokens)

    # 4. Generate TTS metadata
    tts_meta = speech_engine.generate_tts_metadata(
        english_sentence=synthesized["english_sentence"],
        hindi_sentence=synthesized["hindi_sentence"],
        preferred_lang="en-IN"
    )

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "status": "success",
        "regions_count": len(regions),
        "regions": region_results,
        "sentence": synthesized,
        "speech": tts_meta,
        "inference_time_ms": elapsed_ms
    }

@app.post("/api/learn")
async def continuous_learn(
    file: UploadFile = File(...),
    word: str = Form(...),
    category: Optional[str] = Form(None)
):
    """
    Local Offline Continuous Learning Endpoint:
    Accepts a hand gesture image and registers it into the local prototype
    vector memory isl_memory.pt without retraining the backbone network.
    """
    try:
        contents = await file.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
        rgb_np = np.array(pil_image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")

    # Extract single crop
    regions = sign_engine.extract_signs(rgb_np)
    crop = regions[0].crop if regions else cv2.resize(rgb_np, (224, 224))

    # Preprocess and extract 512-dim embedding
    tensor = vision_engine.preprocess_tensor(crop)
    with torch.no_grad():
        _, embedding = vision_engine.model.extract_features(tensor)
        emb_np = embedding.cpu().numpy()[0]

    # Register into memory
    meta = {}
    if category:
        meta["category"] = category
    vision_engine.memory.add_prototype(word, emb_np, metadata=meta)
    vision_engine.memory.save()

    return {
        "status": "success",
        "message": f"Successfully registered prototype for '{word.upper()}' into local memory.",
        "word": word.upper(),
        "total_prototypes": vision_engine.memory.count()
    }

class FeedbackRequest(BaseModel):
    is_positive: bool
    predicted_sign: str
    correct_sign: Optional[str] = None
    crop_base64: Optional[str] = None
    is_dual_hand: Optional[bool] = False

@app.post("/api/feedback")
async def user_feedback(req: FeedbackRequest):
    """
    Self-Learning Online Reinforcement / Punishment Endpoint:
    - If user clicks Thumbs Up (is_positive=True):
      Awards the model by nudging the prototype centroid closer to this gesture's embedding.
    - If user clicks Thumbs Down (is_positive=False):
      Requires correct_sign. Severely punishes the wrong prediction by pushing its centroid away,
      and strongly attracts/registers the correct sign with this sample's embedding.
      Re-runs inference on the crop so the updated prediction is returned immediately!
    """
    if not req.crop_base64:
        raise HTTPException(status_code=400, detail="Missing crop_base64 image data for online feedback.")

    try:
        crop_rgb = decode_base64_to_rgb(req.crop_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid crop_base64: {e}")

    # Extract 512-dim embedding from crop
    tensor = vision_engine.preprocess_tensor(crop_rgb)
    with torch.no_grad():
        _, embedding = vision_engine.model.extract_features(tensor)
        emb_np = embedding.cpu().numpy()[0]

    if req.is_positive:
        # User confirmed correct prediction -> Reward model
        result = online_learner.reward_prediction(req.predicted_sign, crop_rgb)
        return {
            "status": "success",
            "action": "reward",
            "message": f"Model confirmed and awarded! Prototype for '{req.predicted_sign.upper()}' reinforced.",
            "details": result
        }
    else:
        # User reported incorrect prediction -> Punish wrong & actively train neural model
        if not req.correct_sign or not req.correct_sign.strip():
            raise HTTPException(status_code=400, detail="correct_sign is required when reporting incorrect prediction.")

        correct_clean = req.correct_sign.strip().upper()
        learn_result = online_learner.learn_from_feedback(
            crop_rgb=crop_rgb,
            wrong_sign=req.predicted_sign,
            correct_sign=correct_clean,
            is_dual_hand=bool(req.is_dual_hand)
        )

        # Re-run inference with the newly trained neural model & prototype memory
        updated_pred = vision_engine.predict_sign(crop_rgb, is_dual_hand=bool(req.is_dual_hand))
        updated_sentence = synthesizer.synthesize([updated_pred["predicted_sign"]])
        updated_speech = speech_engine.generate_tts_metadata(
            english_sentence=updated_sentence["english_sentence"],
            hindi_sentence=updated_sentence["hindi_sentence"],
            preferred_lang="en-IN"
        )

        return {
            "status": "success",
            "action": "punished_and_corrected",
            "previous_sign": req.predicted_sign.upper(),
            "corrected_sign": correct_clean,
            "message": f"False prediction '{req.predicted_sign.upper()}' severely penalized. Correct sign '{correct_clean}' actively trained into neural network and memory.",
            "details": learn_result,
            "updated_prediction": updated_pred,
            "updated_sentence": updated_sentence,
            "updated_speech": updated_speech
        }

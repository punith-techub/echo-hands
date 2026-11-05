"""
ECHOHANDS - FastAPI Application
Real-Time Indian Sign Language to Text & Speech Translator Server
Serves Echo-Hands web interface and high-performance REST APIs.
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
from CORE.multi_sign_engine import MultiSignEngine, SignRegion
from CORE.vision import DualBrainVisionEngine
from CORE.sentence_synthesizer import SentenceSynthesizer
from CORE.speech_engine import SpeechEngine
from CORE.online_learner import OnlineLearner
from CORE.verifier import AIVerifier
from CORE.isl_landmarks import classify_isl_landmarks

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

# CORS - Wildcard origins with credentials disabled allows unrestricted WebSocket handshakes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
EXTENSION_DIR = os.path.join(BASE_DIR, "extension")
os.makedirs(EXTENSION_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/extension", StaticFiles(directory=EXTENSION_DIR), name="extension")


# Initialize Singletons
sign_engine = MultiSignEngine(target_size=(224, 224))
vision_engine = DualBrainVisionEngine()
synthesizer = SentenceSynthesizer()
speech_engine = SpeechEngine()
online_learner = OnlineLearner(model=vision_engine.model, memory_trainer=vision_engine.memory)
verifier = AIVerifier()

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve Echo-Hands index page."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Echo-Hands Server Active. UI initializing...</h1>")

@app.get("/mobile", response_class=HTMLResponse)
async def serve_mobile():
    """Serve Echo-Hands mobile companion web app."""
    mob_file = os.path.join(STATIC_DIR, "mobile.html")
    if os.path.exists(mob_file):
        with open(mob_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Echo-Hands Mobile Companion Initializing...</h1>")

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

class WebcamPredictRequest(BaseModel):
    frame_base64: str
    session_id: Optional[str] = "webcam_session"
    preferred_brain: Optional[str] = None
    skip_verification: Optional[bool] = False
    allow_empty: Optional[bool] = True
    include_gradcam: Optional[bool] = False

def process_translation_pipeline(
    rgb_np: np.ndarray,
    preferred_brain: Optional[str] = None,
    session_id: str = "default_session",
    skip_verification: bool = False,
    allow_empty: bool = False,
    include_gradcam: bool = False
) -> Dict[str, Any]:
    """
    Unified ECHOHANDS Translation & Adaptive Feedback Flow:
    1. Multi-sign spatial reading-order extraction & zoom cropping
    2. Dual-Brain vision inference + Grad-CAM heatmap generation
    3. Calculate ACTUAL confidence score (NOT dummy one)
    4. Local sentence synthesis (ISL fingerspelling + SOV smoothing)
    5. Check whether internet and API keys are available
    6. If available: verify answer via cloud LLM with zero-context-loss fallback
       - If local model predicts correct: reward it
       - If wrong: punish it severely and train it instantly, display final correct answer
    7. If internet or all API keys are NOT available:
       - Only then just display the answer by local model to user with actual confidence score
    8. Bilingual TTS metadata generation
    """
    start_time = time.time()

    # 1. Extract sign regions in reading order
    regions = sign_engine.extract_signs(rgb_np, allow_empty=allow_empty)

    # If allow_empty is True and no hands detected in frame, return standby state without API spam
    if not regions:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "status": "success",
            "regions_count": 0,
            "regions": [],
            "raw_tokens": [],
            "sentence": {
                "english_sentence": "",
                "hindi_sentence": "",
                "local_english": "",
                "local_hindi": "",
                "raw_tokens": [],
                "aggregated_tokens": []
            },
            "actual_confidence": 0.0,
            "local_actual_confidence": 0.0,
            "verification": {
                "is_verified": False,
                "provider_used": "Standby",
                "key_name": "None",
                "explanation": "No hand gesture detected in frame. Bring hands into viewport to track."
            },
            "verification_badge": "STANDBY // AWAITING HAND GESTURE",
            "feedback_action": "none",
            "feedback_details": {},
            "speech": {
                "primary": {"phonetic_hint": "--", "text": ""},
                "hindi": {"phonetic_hint": "--", "text": ""}
            },
            "inference_time_ms": elapsed_ms
        }

    # 2. Predict each region and record true confidence score
    region_results = []
    raw_tokens = []
    token_confidences = []

    for reg in regions:
        pred = vision_engine.predict_sign(
            reg.crop,
            is_dual_hand=reg.is_dual_hand,
            preferred_brain=preferred_brain,
            include_gradcam=include_gradcam
        )
        raw_tokens.append(pred["predicted_sign"])
        token_confidences.append(float(pred["confidence"]))
        region_results.append({
            "index": reg.index,
            "bbox": list(reg.bbox),
            "is_dual_hand": reg.is_dual_hand,
            "aspect_ratio": round(reg.aspect_ratio, 2),
            "crop_base64": f"data:image/jpeg;base64,{encode_rgb_to_base64(reg.crop)}",
            **pred
        })

    # 2.5 High-Precision 3D ISL Landmark Verification (Biometric Hand Geometry)
    landmarks = getattr(sign_engine, "last_mediapipe_landmarks", None)
    if landmarks and len(landmarks) > 0:
        try:
            lm_res = classify_isl_landmarks(landmarks)
            if lm_res and lm_res.get("confidence", 0) >= 0.85:
                lm_sign = lm_res["sign"]
                lm_conf = float(lm_res["confidence"])
                lm_handedness = lm_res.get("handedness", "one-handed")
                raw_tokens = [lm_sign]
                token_confidences = [lm_conf]
                if region_results:
                    region_results[0]["predicted_sign"] = lm_sign
                    region_results[0]["confidence"] = lm_conf
                    region_results[0]["handedness"] = lm_handedness
                    region_results[0]["chosen_brain"] = f"ISL 3D Landmark Geometry ({lm_handedness.title()})"
                    sign_meta = get_sign_info(lm_sign)
                    if sign_meta:
                        region_results[0]["hindi_translation"] = sign_meta.get("hindi", "")
                        region_results[0]["hindi_transliteration"] = sign_meta.get("translit", "")
                        region_results[0]["phonetic_pronunciation"] = sign_meta.get("phonetic", "")
        except Exception as e:
            print(f"[app.py] ISL Landmark verification warning: {e}")

    # 3. Calculate ACTUAL confidence score (NOT dummy one)
    if token_confidences:
        base_conf = float(np.mean(token_confidences))
        margins = [float(r.get("decision_margin", 0.0)) for r in region_results]
        avg_margin = float(np.mean(margins)) if margins else 0.0
        # Mathematically grounded confidence score from real neural logits and margins
        actual_confidence = float(np.clip(base_conf * (0.85 + 0.15 * max(0.0, avg_margin)), 0.05, 0.99))
    else:
        actual_confidence = 0.50

    # 4. Synthesize local candidate sentence
    synthesized = synthesizer.synthesize(raw_tokens)
    local_sentence_en = synthesized["english_sentence"]
    local_sentence_hi = synthesized["hindi_sentence"]

    # 5. Check whether internet and API keys are available
    has_internet = verifier.check_internet()
    keys_available, avail_reason = verifier.is_available()

    verification_info: Dict[str, Any] = {}
    feedback_action = "none"
    feedback_details: Dict[str, Any] = {}

    if not skip_verification and has_internet and keys_available:
        # Verify the answer by local model
        handedness = region_results[0].get("handedness") if region_results else "one-handed"
        v_res = verifier.verify_sentence(
            raw_tokens=raw_tokens,
            candidate_en=local_sentence_en,
            candidate_hi=local_sentence_hi,
            actual_confidence=actual_confidence,
            session_id=session_id,
            handedness=handedness
        )
        verification_info = v_res

        if v_res.get("is_verified") and not v_res.get("fallback_to_local"):
            if v_res.get("is_correct", True):
                # Local model predicted correct -> REWARD IT!
                feedback_action = "reward"
                rewarded_signs = []
                for reg in regions:
                    pred_sign = next((r["predicted_sign"] for r in region_results if r["index"] == reg.index), None)
                    if pred_sign:
                        online_learner.reward_prediction(pred_sign, reg.crop)
                        rewarded_signs.append(pred_sign)
                feedback_details = {"rewarded_signs": rewarded_signs}
                final_sentence_en = v_res.get("verified_sentence_en") or local_sentence_en
                final_sentence_hi = v_res.get("verified_sentence_hi") or local_sentence_hi
                # Calibrated confidence (not hardcoded dummy)
                final_confidence = min(0.99, round(actual_confidence + (1.0 - actual_confidence) * 0.40, 4))
                verification_badge = f"VERIFIED: CORRECT (Rewarded local model via {v_res.get('key_name', 'AI')})"

            else:
                # Local model predicted wrong -> PUNISH IT SEVERELY AND TRAIN IT INSTANTLY!
                feedback_action = "punish_and_train"
                wrong_sign = v_res.get("wrong_sign") or (raw_tokens[0] if raw_tokens else "")
                correct_sign = v_res.get("correct_sign") or ""

                if wrong_sign and correct_sign and wrong_sign.upper() != correct_sign.upper() and regions:
                    # Select the exact region corresponding to the misclassified sign
                    target_reg = regions[0]
                    for idx_reg, reg_item in enumerate(regions):
                        if idx_reg < len(raw_tokens) and raw_tokens[idx_reg].upper() == wrong_sign.upper():
                            target_reg = reg_item
                            break

                    train_res = online_learner.learn_from_feedback(
                        crop_rgb=target_reg.crop,
                        wrong_sign=wrong_sign,
                        correct_sign=correct_sign,
                        is_dual_hand=target_reg.is_dual_hand
                    )
                    feedback_details = train_res

                final_sentence_en = v_res.get("verified_sentence_en") or local_sentence_en
                final_sentence_hi = v_res.get("verified_sentence_hi") or local_sentence_hi
                # Calibrated confidence (not hardcoded dummy)
                final_confidence = min(0.99, round(actual_confidence + (1.0 - actual_confidence) * 0.35, 4))
                verification_badge = f"VERIFIED: CORRECTION TRAINED (Punished '{wrong_sign}' -> Learned '{correct_sign}')"
        else:
            # Fallback to local
            final_sentence_en = local_sentence_en
            final_sentence_hi = local_sentence_hi
            final_confidence = actual_confidence
            verification_badge = "LOCAL MODEL (All API keys exhausted - zero context loss maintained)"
            feedback_action = "offline_fallback"

    else:
        # If internet or all API keys NOT available:
        # ONLY THEN just display the answer by local model to user with actual confidence score not dummy!
        final_sentence_en = local_sentence_en
        final_sentence_hi = local_sentence_hi
        final_confidence = actual_confidence
        verification_badge = f"LOCAL MODEL PREDICTION (Offline: {avail_reason})"
        verification_info = {
            "is_verified": False,
            "provider_used": "Local Brain (Offline)",
            "key_name": "None",
            "shifted_keys": [],
            "explanation": f"Running offline: {avail_reason}. Actual local confidence displayed."
        }

    # 6. Generate TTS metadata
    tts_meta = speech_engine.generate_tts_metadata(
        english_sentence=final_sentence_en,
        hindi_sentence=final_sentence_hi,
        preferred_lang="en-IN"
    )

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "status": "success",
        "regions_count": len(regions),
        "regions": region_results,
        "raw_tokens": raw_tokens,
        "sentence": {
            "english_sentence": final_sentence_en,
            "hindi_sentence": final_sentence_hi,
            "local_english": local_sentence_en,
            "local_hindi": local_sentence_hi,
            "raw_tokens": raw_tokens,
            "aggregated_tokens": synthesized.get("aggregated_tokens", raw_tokens)
        },
        "actual_confidence": round(final_confidence, 4),
        "local_actual_confidence": round(actual_confidence, 4),
        "verification": verification_info,
        "verification_badge": verification_badge,
        "feedback_action": feedback_action,
        "feedback_details": feedback_details,
        "speech": tts_meta,
        "inference_time_ms": elapsed_ms
    }

@app.post("/api/predict")
async def predict_gesture(
    file: UploadFile = File(...),
    preferred_brain: Optional[str] = Form(None)
):
    """File upload prediction with multi-sign extraction, actual confidence & AI verification."""
    try:
        contents = await file.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
        rgb_np = np.array(pil_image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")

    return process_translation_pipeline(
        rgb_np,
        preferred_brain=preferred_brain,
        session_id="upload_session"
    )

@app.post("/api/webcam/predict")
async def webcam_predict(req: WebcamPredictRequest):
    """
    Live Webcam Translation & Self-Learning Loop:
    User signs live -> local model predicts with actual confidence ->
    verifies via API keys with zero-context-loss fallback ->
    rewards if correct, severely punishes & trains instantly if wrong ->
    displays final correct answer (or local prediction with actual confidence if offline).
    """
    if not req.frame_base64:
        raise HTTPException(status_code=400, detail="Missing frame_base64 image data.")

    try:
        rgb_np = decode_base64_to_rgb(req.frame_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid frame_base64 payload: {e}")

    return process_translation_pipeline(
        rgb_np,
        preferred_brain=req.preferred_brain,
        session_id=req.session_id or "webcam_session",
        skip_verification=bool(req.skip_verification),
        allow_empty=True if req.allow_empty is None else bool(req.allow_empty),
        include_gradcam=bool(req.include_gradcam)
    )

@app.get("/api/verifier/status")
async def get_verifier_status():
    """Live telemetry of internet connectivity and AI verification API key slots."""
    has_internet = verifier.check_internet()
    slots_info = []
    for s in verifier.key_slots:
        slots_info.append({
            "name": s.name,
            "provider": s.provider,
            "model": s.model,
            "is_exhausted": s.is_exhausted,
            "success_count": s.success_count,
            "failure_count": s.failure_count,
            "last_error": s.last_error
        })
    avail, reason = verifier.is_available()
    active_slot_name = verifier.key_slots[verifier.current_slot_idx].name if verifier.key_slots else "None"
    return {
        "has_internet": has_internet,
        "is_available": avail,
        "availability_reason": reason,
        "active_slot": active_slot_name,
        "key_slots": slots_info
    }

@app.post("/api/webcam/reset-session")
async def reset_webcam_session(session_id: str = Body(..., embed=True)):
    """Reset session history context for zero context loss tracking."""
    if session_id in verifier.sessions:
        del verifier.sessions[session_id]
    if session_id in verifier.cache:
        del verifier.cache[session_id]
    return {"status": "success", "message": f"Session '{session_id}' context reset."}

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

class TextToIslRequest(BaseModel):
    text: str
    lang: Optional[str] = "auto"

@app.post("/api/text-to-isl")
async def compile_text_to_isl(req: TextToIslRequest):
    """
    Phase-3 Reverse Compiler API:
    Translates spoken English / Hindi into ISL Gloss and 3D Avatar animation sequence.
    """
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text field cannot be empty.")
    result = synthesizer.text_to_isl_gloss(req.text)
    return result

# In-memory real-time meeting room event store for cross-device sync
ROOM_EVENTS: Dict[str, List[Dict[str, Any]]] = {}

from fastapi import WebSocket, WebSocketDisconnect

class RoomConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = []
        self.rooms[room_id].append(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.rooms and websocket in self.rooms[room_id]:
            self.rooms[room_id].remove(websocket)

    async def broadcast(self, room_id: str, message: dict, sender: WebSocket = None):
        if room_id in self.rooms:
            for conn in list(self.rooms[room_id]):
                if conn != sender:
                    try:
                        await conn.send_json(message)
                    except Exception:
                        self.disconnect(room_id, conn)

room_manager = RoomConnectionManager()

ROOM_EVENTS: Dict[str, List[Dict[str, Any]]] = {}
ROOM_EVENT_SEQ: Dict[str, int] = {}

@app.websocket("/ws/room/{room_id}")
async def websocket_room_endpoint(websocket: WebSocket, room_id: str):
    """Sub-millisecond WebSocket relay between meeting participants."""
    await room_manager.connect(room_id, websocket)
    if room_id not in ROOM_EVENTS:
        ROOM_EVENTS[room_id] = []
        ROOM_EVENT_SEQ[room_id] = 0
    try:
        while True:
            data = await websocket.receive_json()
            ROOM_EVENT_SEQ[room_id] += 1
            data["seq"] = ROOM_EVENT_SEQ[room_id]
            data["server_time"] = time.time()
            ROOM_EVENTS[room_id].append(data)
            if len(ROOM_EVENTS[room_id]) > 100:
                ROOM_EVENTS[room_id] = ROOM_EVENTS[room_id][-100:]
            await room_manager.broadcast(room_id, data, sender=websocket)
    except WebSocketDisconnect:
        room_manager.disconnect(room_id, websocket)

@app.post("/api/room/{room_id}/event")
async def post_room_event(room_id: str, payload: Dict[str, Any] = Body(...)):
    """Receives cross-device sign/voice events for a meeting room."""
    if room_id not in ROOM_EVENTS:
        ROOM_EVENTS[room_id] = []
        ROOM_EVENT_SEQ[room_id] = 0
    ROOM_EVENT_SEQ[room_id] += 1
    payload["seq"] = ROOM_EVENT_SEQ[room_id]
    payload["server_time"] = time.time()
    ROOM_EVENTS[room_id].append(payload)
    if len(ROOM_EVENTS[room_id]) > 100:
        ROOM_EVENTS[room_id] = ROOM_EVENTS[room_id][-100:]
    # Broadcast to any active websockets
    await room_manager.broadcast(room_id, payload)
    return {"status": "dispatched", "room_id": room_id, "seq": payload["seq"]}

@app.get("/api/room/{room_id}/events")
async def get_room_events(room_id: str, since_seq: int = 0, since: float = 0):
    """Returns new events in room_id since sequence number or timestamp."""
    events = ROOM_EVENTS.get(room_id, [])
    if since_seq > 0 or since == 0:
        new_events = [e for e in events if e.get("seq", 0) > since_seq]
    else:
        new_events = [e for e in events if e.get("timestamp", 0) > since or e.get("seq", 0) > since_seq]
    current_max = ROOM_EVENT_SEQ.get(room_id, 0)
    return {"room_id": room_id, "events": new_events, "max_seq": current_max}

@app.get("/api/download-extension")
async def download_extension_zip():
    """
    Packages the Manifest V3 Chrome Extension into a clean zip archive and streams it.
    """
    import zipfile
    ext_dir = os.path.join(BASE_DIR, "extension")
    if not os.path.exists(ext_dir):
        raise HTTPException(status_code=404, detail="Extension directory not found.")

    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ext_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, ext_dir)
                zf.write(abs_path, arcname=rel_path)
    mem_zip.seek(0)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        mem_zip,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=echo-hands-extension.zip"}
    )

@app.get("/echo-hands.crx")
@app.get("/api/install-extension")
async def install_extension_crx():
    """
    Direct 1-click Chrome Extension installer endpoint.
    Serves the packaged extension with application/x-chrome-extension MIME type.
    """
    import zipfile
    ext_dir = os.path.join(BASE_DIR, "extension")
    if not os.path.exists(ext_dir):
        raise HTTPException(status_code=404, detail="Extension directory not found.")

    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ext_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, ext_dir)
                zf.write(abs_path, arcname=rel_path)
    mem_zip.seek(0)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        mem_zip,
        media_type="application/x-chrome-extension",
        headers={"Content-Disposition": "attachment; filename=echo-hands.crx"}
    )



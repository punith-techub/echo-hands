"""
ECHOHANDS 5.0 - Multi-Key AI Verification & Context-Lossless Fallback Engine
Verifies local neural predictions against cloud LLM providers (Groq, Gemini, OpenAI).
Features:
1. Internet connectivity check.
2. Multi-provider key rotation & automatic fallback on rate-limits (429), quotas, or errors.
3. Zero Context Loss: Preserves full conversation context, past tokens, and verification
   history across fallback transitions.
4. Reward / Punish signals: Identifies whether the local model was correct or wrong,
   triggering reinforcement or online backpropagation training.
5. Offline graceful fallback: If internet or all keys are exhausted, returns the
   local model's actual confidence score and prediction without crashing.
"""

import os
import re
import json
import time
import socket
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("echohands.verifier")

# Provider configs
DEFAULT_GROQ_MODEL = "qwen/qwen3.8-27b"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


@dataclass
class APIKeySlot:
    provider: str            # "groq", "gemini", "openai"
    key: str                 # API key string
    model: str               # Model identifier
    name: str                # Display name (e.g., "Groq-Key-1")
    is_exhausted: bool = False
    exhausted_until: float = 0.0
    failure_count: int = 0
    success_count: int = 0
    last_error: Optional[str] = None


@dataclass
class VerificationContext:
    """Session context preserved across API key rotations to guarantee ZERO context loss."""
    session_id: str = "default_session"
    history: List[Dict[str, Any]] = field(default_factory=list)
    recent_signs: List[str] = field(default_factory=list)
    recent_sentences: List[str] = field(default_factory=list)

    def add_turn(self, raw_tokens: List[str], sentence_en: str, verified_en: str):
        self.recent_signs.extend(raw_tokens)
        if len(self.recent_signs) > 30:
            self.recent_signs = self.recent_signs[-30:]
        self.recent_sentences.append(verified_en)
        if len(self.recent_sentences) > 10:
            self.recent_sentences = self.recent_sentences[-10:]
        self.history.append({
            "timestamp": time.time(),
            "raw_tokens": raw_tokens,
            "predicted": sentence_en,
            "verified": verified_en
        })
        if len(self.history) > 20:
            self.history.pop(0)

    def get_context_summary(self) -> str:
        if not self.recent_sentences:
            return "No previous sentences in this session."
        return "Previous verified sentences in session: " + " | ".join(self.recent_sentences[-3:])


class AIVerifier:
    def __init__(self, key_slots: Optional[List[APIKeySlot]] = None):
        self.key_slots: List[APIKeySlot] = key_slots if key_slots is not None else self._discover_keys()
        self.current_slot_idx: int = 0
        self.sessions: Dict[str, VerificationContext] = {}
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._last_internet_check: float = 0.0
        self._last_internet_status: bool = False

    def _discover_keys(self) -> List[APIKeySlot]:
        """Discover available API keys from environment variables with deduplication."""
        slots: List[APIKeySlot] = []

        def _gather_env_keys(prefixes: List[str]) -> List[str]:
            found: List[str] = []
            seen = set()
            # 1. Direct env vars
            for p in prefixes:
                val = os.getenv(p, "")
                for part in val.split(","):
                    k = part.strip()
                    if k and k not in seen:
                        seen.add(k)
                        found.append(k)
            # 2. Numbered / wildcards: e.g. GROQ_API_KEY_1, GROQ_KEY_2
            for env_k, env_v in os.environ.items():
                env_k_upper = env_k.upper()
                if any(env_k_upper.startswith(p.upper()) for p in prefixes):
                    for part in env_v.split(","):
                        k = part.strip()
                        if k and k not in seen:
                            seen.add(k)
                            found.append(k)
            return found

        # 1. Groq Keys
        groq_keys = _gather_env_keys(["GROQ_API_KEYS", "GROQ_API_KEY", "GROQ_KEY"])
        for idx, k in enumerate(groq_keys):
            slots.append(APIKeySlot(
                provider="groq",
                key=k,
                model=os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
                name=f"Groq-Key-{idx + 1}"
            ))

        # 2. Gemini Keys
        gemini_keys = _gather_env_keys(["GEMINI_API_KEYS", "GEMINI_API_KEY", "GEMINI_KEY", "GOOGLE_API_KEY"])
        for idx, k in enumerate(gemini_keys):
            slots.append(APIKeySlot(
                provider="gemini",
                key=k,
                model=os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
                name=f"Gemini-Key-{idx + 1}"
            ))

        # 3. OpenAI Keys
        openai_keys = _gather_env_keys(["OPENAI_API_KEYS", "OPENAI_API_KEY", "OPENAI_KEY"])
        for idx, k in enumerate(openai_keys):
            slots.append(APIKeySlot(
                provider="openai",
                key=k,
                model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
                name=f"OpenAI-Key-{idx + 1}"
            ))

        return slots

    def check_internet(self, force: bool = False) -> bool:
        """Fast non-blocking connectivity check with DNS resolution / socket ping."""
        now = time.time()
        if not force and (now - self._last_internet_check < 5.0):
            return self._last_internet_status

        self._last_internet_check = now
        for host, port in [("1.1.1.1", 53), ("8.8.8.8", 53), ("api.groq.com", 443)]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.8)
                s.connect((host, port))
                s.close()
                self._last_internet_status = True
                return True
            except Exception:
                continue

        self._last_internet_status = False
        return False

    def is_available(self) -> Tuple[bool, str]:
        """Check if internet and at least one API key slot is active."""
        if not self.check_internet():
            return False, "Offline: No active internet connection detected"

        now = time.time()
        active_slots = [
            s for s in self.key_slots
            if not s.is_exhausted or (s.exhausted_until > 0 and s.exhausted_until < now)
        ]
        if not active_slots:
            return False, "All API keys exhausted or rate-limited"

        return True, f"Active API keys available ({len(active_slots)} slots)"

    def get_or_create_context(self, session_id: str) -> VerificationContext:
        if session_id not in self.sessions:
            self.sessions[session_id] = VerificationContext(session_id=session_id)
        return self.sessions[session_id]

    def _mark_slot_exhausted(self, slot: APIKeySlot, err: str, cooldown_seconds: float = 60.0):
        slot.is_exhausted = True
        slot.exhausted_until = time.time() + cooldown_seconds
        slot.failure_count += 1
        slot.last_error = str(err)
        logger.warning(
            f"[AIVerifier] Slot '{slot.name}' ({slot.provider}) hit rate limit/error: {err}. "
            f"Cooling down for {cooldown_seconds}s. Shifting to next available key without context loss."
        )

    def _build_verification_prompt(
        self,
        raw_tokens: List[str],
        candidate_en: str,
        candidate_hi: str,
        actual_confidence: float,
        context: VerificationContext,
        handedness: Optional[str] = None
    ) -> str:
        """
        Build zero-context-loss prompt embedding conversation history,
        raw ISL token detections, and candidate sentences.
        """
        context_summary = context.get_context_summary()
        prompt = f"""You are the ECHOHANDS Master Indian Sign Language (ISL) Verification Arbiter.
The user is signing live via webcam. Our local neural vision model recognized gesture tokens and produced a candidate translation.
Your mission is to VERIFY the prediction with 100% accuracy, correcting any visual misclassifications, and translating into natural English (SVO) and Hindi (SOV).

SESSION CONTEXT:
{context_summary}

CURRENT DETECTION:
- Detected Tokens: {json.dumps(raw_tokens)}
- Handedness: {handedness or "unknown"}
- Local Model Actual Confidence: {actual_confidence * 100:.1f}%
- Local Model English Sentence: "{candidate_en}"
- Local Model Hindi Sentence: "{candidate_hi}"

ISL KNOWLEDGE & GUIDELINES:
- Preserve Authentic Recognition: Faithfully recognize the user's hand gesture. DO NOT default or bias towards letter 'I'. Letters A-Z and digits 1-9 each have unique finger positions.
- Known ISL Words: 'NAMASTE', 'HELLO', 'PLEASE', 'THANK_YOU', 'SORRY', 'HELP', 'FOOD', 'WATER', 'DOCTOR', 'FAMILY', 'MOTHER', 'FATHER', 'STOP', etc.
- If the gesture token is a valid letter, number, or word and fits the context, mark "is_correct": true.
- Only mark "is_correct": false when there is an obvious visual misclassification.
- correct_sign MUST be a single standard ISL token (e.g. 'A', '5', 'NAMASTE', 'HELP'), never multiple words or punctuation.

INSTRUCTIONS:
Determine whether the local model prediction is correct or needs correction.
Output STRICTLY valid JSON with no markdown wrapping or preamble, in this exact schema:
{{
  "is_correct": true or false,
  "wrong_sign": "THE_WRONG_TOKEN_OR_EMPTY",
  "correct_sign": "THE_CORRECT_TOKEN_OR_EMPTY",
  "verified_sentence_en": "Polished Natural English Sentence",
  "verified_sentence_hi": "प्राकृतिक और शुद्ध हिन्दी वाक्य",
  "explanation": "Brief 1-sentence tactical explanation"
}}
"""
        return prompt

    def _call_groq(self, slot: APIKeySlot, prompt: str) -> Dict[str, Any]:
        from groq import Groq
        client = Groq(api_key=slot.key)
        resp = client.chat.completions.create(
            model=slot.model,
            messages=[
                {"role": "system", "content": "You are a precise JSON-only ISL verification engine."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=250,
            timeout=5.0
        )
        content = resp.choices[0].message.content
        return json.loads(content)

    def _call_gemini(self, slot: APIKeySlot, prompt: str) -> Dict[str, Any]:
        from google import genai
        client = genai.Client(api_key=slot.key)
        models_to_try = [slot.model]
        if "2.5-flash" in slot.model:
            models_to_try.append("gemini-3.5-flash-lite")
        elif "3.5" in slot.model:
            models_to_try.append("gemini-2.5-flash")

        last_err = None
        for m in models_to_try:
            try:
                resp = client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "temperature": 0.1
                    }
                )
                text = resp.text.strip()
                if "```" in text:
                    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
                    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
                return json.loads(text.strip())
            except Exception as e:
                last_err = e
                if "503" in str(e) or "404" in str(e) or "not available" in str(e).lower():
                    continue
                raise e
        raise last_err

    def _call_openai(self, slot: APIKeySlot, prompt: str) -> Dict[str, Any]:
        import openai
        client = openai.OpenAI(api_key=slot.key)
        resp = client.chat.completions.create(
            model=slot.model,
            messages=[
                {"role": "system", "content": "You are a precise JSON-only ISL verification engine."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=250,
            timeout=5.0
        )
        content = resp.choices[0].message.content
        return json.loads(content)

    def _dispatch_call(self, slot: APIKeySlot, prompt: str) -> Dict[str, Any]:
        """Dispatch call to provider with uniform interface."""
        if slot.provider == "groq":
            return self._call_groq(slot, prompt)
        elif slot.provider == "gemini":
            return self._call_gemini(slot, prompt)
        elif slot.provider == "openai":
            return self._call_openai(slot, prompt)
        else:
            raise ValueError(f"Unknown provider '{slot.provider}'")

    def verify_sentence(
        self,
        raw_tokens: List[str],
        candidate_en: str,
        candidate_hi: str,
        actual_confidence: float,
        session_id: str = "default_session",
        handedness: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify prediction with automatic, zero-context-loss fallback across API keys.
        
        Returns:
        {
            "is_verified": bool,
            "is_correct": bool,
            "provider_used": str,
            "key_name": str,
            "verified_sentence_en": str,
            "verified_sentence_hi": str,
            "wrong_sign": str,
            "correct_sign": str,
            "explanation": str,
            "shifted_keys": List[str],
            "fallback_to_local": bool
        }
        """
        context = self.get_or_create_context(session_id)
        tokens_key = tuple(raw_tokens)
        now = time.time()

        # Check in-flight cache (prevents duplicate API spam during continuous webcam capture)
        cached_entry = self.cache.get(session_id)
        if cached_entry and cached_entry.get("tokens") == tokens_key and (now - cached_entry.get("time", 0.0) < 2.5):
            cached_res = dict(cached_entry["result"])
            cached_res["verification_time_ms"] = 0.0
            cached_res["is_cached"] = True
            return cached_res

        prompt = self._build_verification_prompt(
            raw_tokens=raw_tokens,
            candidate_en=candidate_en,
            candidate_hi=candidate_hi,
            actual_confidence=actual_confidence,
            context=context,
            handedness=handedness
        )

        shifted_keys: List[str] = []
        num_slots = len(self.key_slots)

        if num_slots == 0 or not self.check_internet():
            # Update context even while offline to maintain zero context loss
            context.add_turn(raw_tokens, candidate_en, candidate_en)
            return {
                "is_verified": False,
                "is_correct": True,
                "provider_used": "None (Offline)",
                "key_name": "None",
                "verified_sentence_en": candidate_en,
                "verified_sentence_hi": candidate_hi,
                "wrong_sign": "",
                "correct_sign": "",
                "explanation": "Offline: Operating on local neural model prediction.",
                "shifted_keys": [],
                "fallback_to_local": True
            }

        # Try active slots starting from current_slot_idx
        for attempt in range(num_slots):
            idx = (self.current_slot_idx + attempt) % num_slots
            slot = self.key_slots[idx]

            # If slot is exhausted, check if cooldown elapsed
            if slot.is_exhausted:
                if slot.exhausted_until > 0 and slot.exhausted_until < now:
                    slot.is_exhausted = False
                else:
                    shifted_keys.append(f"{slot.name} (Exhausted)")
                    continue

            # Attempt verification with this slot
            try:
                start_t = time.time()
                result_json = self._dispatch_call(slot, prompt)
                slot.success_count += 1
                self.current_slot_idx = idx  # Keep active slot

                # Parse verified result
                is_correct = bool(result_json.get("is_correct", True))
                v_en = result_json.get("verified_sentence_en", candidate_en)
                v_hi = result_json.get("verified_sentence_hi", candidate_hi)
                w_sign = str(result_json.get("wrong_sign", "")).strip().upper()
                c_sign = str(result_json.get("correct_sign", "")).strip().upper()
                expl = result_json.get("explanation", "Prediction verified.")

                # Update context with zero context loss
                context.add_turn(raw_tokens, candidate_en, v_en)

                verif_res = {
                    "is_verified": True,
                    "is_correct": is_correct,
                    "provider_used": f"{slot.provider} ({slot.model})",
                    "key_name": slot.name,
                    "verified_sentence_en": v_en,
                    "verified_sentence_hi": v_hi,
                    "wrong_sign": w_sign,
                    "correct_sign": c_sign,
                    "explanation": expl,
                    "shifted_keys": shifted_keys,
                    "fallback_to_local": False,
                    "verification_time_ms": round((time.time() - start_t) * 1000, 2)
                }

                # Store in cache
                self.cache[session_id] = {
                    "tokens": tokens_key,
                    "result": verif_res,
                    "time": time.time()
                }

                return verif_res

            except Exception as e:
                err_str = str(e)
                # Mark as exhausted on rate limit, quota, auth, or model errors
                is_rate_limit = any(term in err_str.lower() for term in [
                    "429", "quota", "rate limit", "credit_balance_exhausted",
                    "resourceexhausted", "limit_exceeded", "too many requests"
                ])
                cooldown = 120.0 if is_rate_limit else 30.0
                self._mark_slot_exhausted(slot, err_str, cooldown_seconds=cooldown)
                shifted_keys.append(f"{slot.name} -> {slot.provider} Error: {err_str[:40]}...")
                continue

        # If all slots failed, fallback to local model prediction without crashing
        logger.warning("[AIVerifier] All API slots exhausted. Falling back to local neural prediction.")
        # Maintain zero context loss even on exhaustion
        context.add_turn(raw_tokens, candidate_en, candidate_en)
        return {
            "is_verified": False,
            "is_correct": True,
            "provider_used": "Fallback (Local Only)",
            "key_name": "None",
            "verified_sentence_en": candidate_en,
            "verified_sentence_hi": candidate_hi,
            "wrong_sign": "",
            "correct_sign": "",
            "explanation": "All API keys reached rate limit/exhausted. Zero context loss maintained. Running on local neural engine.",
            "shifted_keys": shifted_keys,
            "fallback_to_local": True
        }

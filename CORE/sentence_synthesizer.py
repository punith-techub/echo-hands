"""
ECHOHANDS - Sentence Synthesizer
Advanced fingerspell aggregation & Indian Sign Language (ISL) SOV
grammar smoothing to natural English (SVO) and Hindi (SOV) sentences.
"""

from typing import List, Dict, Any, Tuple
import re
from CORE.sign_knowledge import get_sign_info, is_alphanumeric, is_word

PRONOUNS = {"I", "ME", "YOU", "WE", "THEY", "HE", "SHE"}
VERBS = {"EAT", "DRINK", "GO", "COME", "STOP", "LIKE", "LOVE", "LEARN", "MEET", "WORK", "HELP", "WANT", "NEED"}
OBJECTS = {"FOOD", "WATER", "HOME", "SCHOOL", "HOSPITAL", "BOOK", "MEDICINE", "MONEY", "TIME"}
QUESTIONS = {"WHAT", "WHERE", "WHEN", "WHY", "HOW", "WHO"}

# Idiomatic ISL template patterns -> (English, Hindi)
ISL_PATTERNS: Dict[Tuple[str, ...], Tuple[str, str]] = {
    ("NAMASTE",): ("Namaste! Greetings.", "नमस्ते! आपका स्वागत है।"),
    ("HELLO",): ("Hello! Greetings.", "नमस्ते!"),
    ("GOOD_MORNING",): ("Good morning!", "सुप्रभात!"),
    ("GOOD_AFTERNOON",): ("Good afternoon!", "शुभ दोपहर!"),
    ("GOOD_NIGHT",): ("Good night!", "शुभ रात्रि!"),
    ("THANK_YOU",): ("Thank you very much!", "आपका बहुत-बहुत धन्यवाद!"),
    ("WELCOME",): ("You are welcome!", "आपका स्वागत है।"),
    ("PLEASE",): ("Please.", "कृपया।"),
    ("SORRY",): ("I am very sorry.", "मुझे माफ़ कीजिए।"),
    ("EXCUSE_ME",): ("Excuse me, please.", "क्षमा करें।"),
    ("YES",): ("Yes, absolutely.", "हाँ, बिल्कुल।"),
    ("NO",): ("No.", "नहीं।"),
    ("GOOD",): ("It is good.", "यह अच्छा है।"),
    ("BAD",): ("It is not good.", "यह ठीक नहीं है।"),

    # Help & Emergency
    ("HELP",): ("Help me please!", "कृपया मेरी मदद करें!"),
    ("HELP", "ME"): ("Please help me!", "मेरी मदद कीजिए!"),
    ("PLEASE", "HELP"): ("Please help me!", "कृपया मेरी सहायता करें!"),
    ("PLEASE", "HELP", "ME"): ("Please help me!", "कृपया मेरी मदद कीजिए!"),
    ("I", "HELP", "NEED"): ("I need help.", "मुझे मदद की ज़रूरत है।"),
    ("ME", "HELP", "NEED"): ("I need help.", "मुझे मदद चाहिए।"),
    ("I", "NEED", "HELP"): ("I need help.", "मुझे मदद की ज़रूरत है।"),
    ("I", "PAIN"): ("I am in pain.", "मुझे दर्द हो रहा है।"),
    ("I", "PAIN", "HAVE"): ("I am having pain.", "मुझे बहुत दर्द हो रहा है।"),
    ("I", "MEDICINE", "NEED"): ("I need medicine.", "मुझे दवा चाहिए।"),
    ("I", "DOCTOR", "NEED"): ("I need a doctor.", "मुझे डॉक्टर की ज़रूरत है।"),
    ("I", "DOCTOR", "GO"): ("I need to go to the doctor.", "मुझे डॉक्टर के पास जाना है।"),
    ("I", "HOSPITAL", "GO"): ("I need to go to the hospital.", "मुझे अस्पताल जाना है।"),

    # Wants, Needs & Actions (SOV -> SVO)
    ("I", "FOOD", "WANT"): ("I want food.", "मुझे खाना चाहिए।"),
    ("I", "FOOD", "EAT"): ("I want to eat food.", "मैं खाना खाना चाहता हूँ।"),
    ("I", "EAT", "FOOD"): ("I want to eat food.", "मैं भोजन करना चाहता हूँ।"),
    ("I", "WATER", "WANT"): ("I want water.", "मुझे पानी चाहिए।"),
    ("I", "WATER", "DRINK"): ("I want to drink water.", "मैं पानी पीना चाहता हूँ।"),
    ("I", "DRINK", "WATER"): ("I want to drink water.", "मैं पानी पीना चाहता हूँ।"),
    ("I", "HOME", "GO"): ("I want to go home.", "मैं घर जाना चाहता हूँ।"),
    ("I", "SCHOOL", "GO"): ("I am going to school.", "मैं स्कूल जा रहा हूँ।"),
    ("I", "WORK", "GO"): ("I am going to work.", "मैं काम पर जा रहा हूँ।"),
    ("I", "FRIEND", "MEET"): ("I am meeting my friend.", "मैं अपने दोस्त से मिल रहा हूँ।"),
    ("I", "LEARN", "SIGN"): ("I am learning sign language.", "मैं सांकेतिक भाषा सीख रहा हूँ।"),
    ("I", "HAPPY"): ("I am happy.", "मैं खुश हूँ।"),
    ("I", "SAD"): ("I am sad.", "मैं उदास हूँ।"),

    # Questions
    ("YOU", "HOW"): ("How are you?", "आप कैसे हैं?"),
    ("HOW", "YOU"): ("How are you?", "आप कैसे हैं?"),
    ("YOU", "NAME", "WHAT"): ("What is your name?", "आपका नाम क्या है?"),
    ("WHAT", "NAME", "YOU"): ("What is your name?", "आपका नाम क्या है?"),
    ("YOU", "WHERE", "GO"): ("Where are you going?", "आप कहाँ जा रहे हैं?"),
    ("YOU", "GO", "WHERE"): ("Where are you going?", "आप कहाँ जा रहे हैं?"),
    ("YOU", "WHAT", "WANT"): ("What do you want?", "आपको क्या चाहिए?"),
    ("WHAT", "YOU", "WANT"): ("What do you want?", "आप क्या चाहते हैं?"),
    ("TIME", "WHAT"): ("What time is it?", "क्या समय हुआ है?"),
    ("WHAT", "TIME"): ("What time is it?", "क्या समय हुआ है?"),
    ("WHERE", "HOSPITAL"): ("Where is the hospital?", "अस्पताल कहाँ है?"),
    ("HOSPITAL", "WHERE"): ("Where is the hospital?", "अस्पताल कहाँ है?"),
    ("WHERE", "HOME"): ("Where is your home?", "घर कहाँ है?"),
    ("HOME", "WHERE"): ("Where is home?", "घर कहाँ है?"),
    ("WHO", "YOU"): ("Who are you?", "आप कौन हैं?"),
    ("YOU", "WHO"): ("Who are you?", "आप कौन हैं?"),
    ("WHY", "YOU", "SAD"): ("Why are you sad?", "आप उदास क्यों हैं?"),

    # Sentence food & essentials
    ("I", "NEED", "FOOD"): ("I need food.", "मुझे खाना चाहिए।"),
    ("I", "FOOD", "NEED"): ("I need food.", "मुझे खाना चाहिए।"),
    ("I", "WANT", "FOOD"): ("I want food.", "मुझे खाना चाहिए।"),
    ("I", "NEED", "WATER"): ("I need water.", "मुझे पानी चाहिए।"),
    ("I", "WATER", "NEED"): ("I need water.", "मुझे पानी चाहिए।"),
    ("CAT",): ("Cat.", "बिल्ली।"),
    ("DOG",): ("Dog.", "कुत्ता।"),
    ("NAME",): ("Name.", "नाम।"),
    ("SIGN",): ("Sign language.", "सांकेतिक भाषा।")
}

def _segment_fused_word(word_str: str) -> List[str]:
    """
    Greedy/DP segmentation of fused uppercase strings into known dictionary words.
    e.g. 'INEEDFOOD' -> ['I', 'NEED', 'FOOD']
         'CAT' -> ['CAT']
         'HELP' -> ['HELP']
    """
    from CORE.sign_knowledge import ALL_SIGNS
    vocab = set(ALL_SIGNS.keys()) | {
        "I", "A", "AN", "THE", "IN", "ON", "AT", "TO", "FOR", "OF", "WITH",
        "IS", "AM", "ARE", "WAS", "WERE", "CAT", "DOG", "FOOD", "WATER",
        "HELP", "NEED", "WANT", "HOME", "NAME", "ME"
    }
    w = word_str.strip().upper()
    if not w:
        return []
    if w in vocab:
        return [w]

    n = len(w)
    dp = [None] * (n + 1)
    dp[0] = []

    for i in range(n):
        if dp[i] is None:
            continue
        for j in range(i + 1, n + 1):
            sub = w[i:j]
            if sub in vocab:
                if dp[j] is None or len(dp[i]) + 1 < len(dp[j]):
                    dp[j] = dp[i] + [sub]

    if dp[n] is not None and len(dp[n]) > 0:
        return dp[n]

    return [w]

class SentenceSynthesizer:
    def __init__(self):
        pass

    def aggregate_fingerspelling(self, raw_tokens: List[str]) -> List[str]:
        """
        Group consecutive alphanumeric characters into fingerspelled words,
        segment multi-word strings into vocabulary tokens,
        while maintaining standalone words and numbers cleanly.
        Example: ['H', 'E', 'L', 'P'] -> ['HELP']
                 ['C', 'A', 'T'] -> ['CAT']
                 ['I', 'N', 'E', 'E', 'D', 'F', 'O', 'O', 'D'] -> ['I', 'NEED', 'FOOD']
        """
        if not raw_tokens:
            return []

        aggregated: List[str] = []
        char_buffer: List[str] = []

        def flush_buffer():
            nonlocal char_buffer
            if char_buffer:
                fused = "".join(char_buffer)
                segmented = _segment_fused_word(fused)
                aggregated.extend(segmented)
                char_buffer = []

        for token in raw_tokens:
            clean = token.strip().upper()
            if not clean:
                continue

            # If it's a full multi-character ISL word
            if is_word(clean) and len(clean) > 1:
                flush_buffer()
                aggregated.append(clean)
            elif is_alphanumeric(clean):
                if clean.isdigit():
                    flush_buffer()
                    aggregated.append(clean)
                else:
                    char_buffer.append(clean)
            else:
                flush_buffer()
                aggregated.append(clean)

        flush_buffer()
        return aggregated

    def _apply_rule_patterns(self, tokens: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """Match exact token tuple against known ISL sentence patterns."""
        key = tuple(tokens)
        if key in ISL_PATTERNS:
            return ISL_PATTERNS[key]
        return None, None

    def _synthesize_sov_to_svo(self, tokens: List[str]) -> Tuple[str, str]:
        """
        General syntactic rearrangement for arbitrary ISL sequences:
        ISL (SOV) -> English (SVO) and Hindi (SOV naturally).
        """
        if not tokens:
            return "", ""

        # Map each token to Hindi word and English term
        eng_words: List[str] = []
        hindi_words: List[str] = []

        has_question = any(t in QUESTIONS for t in tokens)

        # Separate Subject, Object, Verb if present
        subject = None
        obj = None
        verb = None
        question_word = None
        other_tokens: List[str] = []

        for t in tokens:
            info = get_sign_info(t)
            hindi_repr = info.get("hindi", t) if info else t

            if t in PRONOUNS and subject is None:
                subject = t
            elif t in OBJECTS and obj is None:
                obj = t
            elif t in VERBS and verb is None:
                verb = t
            elif t in QUESTIONS and question_word is None:
                question_word = t
            else:
                other_tokens.append(t)

        # Construct English SVO:
        if subject and verb and obj:
            # SVO order
            subj_en = "I" if subject in ("I", "ME") else subject.capitalize()
            verb_en = verb.lower()
            obj_en = obj.lower()
            if verb_en in ("eat", "drink", "want", "need", "like", "love"):
                eng_sentence = f"{subj_en} {verb_en}s {obj_en}." if subj_en in ("He", "She") else f"{subj_en} {verb_en} {obj_en}."
            elif verb_en == "go":
                eng_sentence = f"{subj_en} goes to {obj_en}." if subj_en in ("He", "She") else f"{subj_en} go to {obj_en}."
            else:
                eng_sentence = f"{subj_en} {verb_en} {obj_en}."
            
            # Natural Hindi SOV order:
            s_info = get_sign_info(subject)
            o_info = get_sign_info(obj)
            v_info = get_sign_info(verb)
            s_hi = s_info.get("hindi", subject) if s_info else subject
            o_hi = o_info.get("hindi", obj) if o_info else obj
            v_hi = v_info.get("hindi", verb) if v_info else verb

            if verb in ("WANT", "NEED"):
                s_pronoun = "मुझे" if subject in ("I", "ME") else ("आपको" if subject == "YOU" else f"{s_hi} को")
                hindi_sentence = f"{s_pronoun} {o_hi} चाहिए।"
            elif verb == "EAT":
                s_pronoun = "मैं" if subject in ("I", "ME") else s_hi
                hindi_sentence = f"{s_pronoun} {o_hi} खाना चाहता हूँ।"
            elif verb == "DRINK":
                s_pronoun = "मैं" if subject in ("I", "ME") else s_hi
                hindi_sentence = f"{s_pronoun} {o_hi} पीना चाहता हूँ।"
            elif verb == "GO":
                s_pronoun = "मैं" if subject in ("I", "ME") else s_hi
                hindi_sentence = f"{s_pronoun} {o_hi} जाना चाहता हूँ।"
            else:
                hindi_sentence = f"{s_hi} {o_hi} {v_hi}।"
            return eng_sentence, hindi_sentence

        # Generalized joining with vocabulary lookup
        for t in tokens:
            info = get_sign_info(t)
            if info:
                # Format english display name
                eng_words.append(t.replace("_", " ").capitalize())
                hindi_words.append(info.get("hindi", t))
            else:
                eng_words.append(t)
                hindi_words.append(t)

        eng_raw = " ".join(eng_words).strip()
        hindi_raw = " ".join(hindi_words).strip()

        # Add punctuation
        punct = "?" if has_question else "."
        hindi_punct = "?" if has_question else "।"

        eng_sentence = eng_raw[0].upper() + eng_raw[1:] + punct if eng_raw else ""
        hindi_sentence = hindi_raw + hindi_punct if hindi_raw else ""

        return eng_sentence, hindi_sentence

    def synthesize(self, raw_tokens: List[str]) -> Dict[str, Any]:
        """
        Complete end-to-end synthesis pipeline:
        1. Fingerspell aggregation
        2. Rule pattern matching
        3. SOV -> SVO grammar smoothing
        Returns structured payload.
        """
        if not raw_tokens:
            return {
                "raw_tokens": [],
                "aggregated_tokens": [],
                "english_sentence": "",
                "hindi_sentence": "",
                "has_question": False
            }

        aggregated = self.aggregate_fingerspelling(raw_tokens)

        # Check exact patterns first
        eng_match, hi_match = self._apply_rule_patterns(aggregated)
        if eng_match and hi_match:
            return {
                "raw_tokens": raw_tokens,
                "aggregated_tokens": aggregated,
                "english_sentence": eng_match,
                "hindi_sentence": hi_match,
                "has_question": "?" in eng_match
            }

        # Check raw tokens pattern match as fallback before aggregation if single word
        if len(raw_tokens) == 1:
            eng_m, hi_m = self._apply_rule_patterns(raw_tokens)
            if eng_m and hi_m:
                return {
                    "raw_tokens": raw_tokens,
                    "aggregated_tokens": aggregated,
                    "english_sentence": eng_m,
                    "hindi_sentence": hi_m,
                    "has_question": "?" in eng_m
                }

        # Apply general SOV to SVO translation
        eng_sentence, hindi_sentence = self._synthesize_sov_to_svo(aggregated)

        return {
            "raw_tokens": raw_tokens,
            "aggregated_tokens": aggregated,
            "english_sentence": eng_sentence,
            "hindi_sentence": hindi_sentence,
            "has_question": "?" in eng_sentence
        }

"""
ECHOHANDS - Sign Knowledge Base
Comprehensive Indian Sign Language (ISL) dictionary containing:
- 35 Alphanumeric classes (1-9, A-Z)
- 60+ Essential ISL Vocabulary Words
Includes Hindi translations, transliterations, phonetics, handedness, and contact signatures.
"""

from typing import Dict, List, Optional, Any

# 35 Alphanumeric classes (9 digits: 1-9, 26 letters: A-Z)
ALPHANUMERIC_CLASSES: List[str] = [
    "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "A", "B", "C", "D", "E", "F", "G", "H", "I",
    "J", "K", "L", "M", "N", "O", "P", "Q", "R",
    "S", "T", "U", "V", "W", "X", "Y", "Z"
]

CLASS_TO_INDEX: Dict[str, int] = {cls: idx for idx, cls in enumerate(ALPHANUMERIC_CLASSES)}
INDEX_TO_CLASS: Dict[int, str] = {idx: cls for idx, cls in enumerate(ALPHANUMERIC_CLASSES)}

ALPHANUMERIC_METADATA: Dict[str, Dict[str, Any]] = {
    "1": {"hindi": "एक", "translit": "Ek", "phonetic": "one", "handedness": "one-handed", "contact": "index-extended", "desc": "Index finger extended upwards vertically"},
    "2": {"hindi": "दो", "translit": "Do", "phonetic": "two", "handedness": "one-handed", "contact": "v-shape", "desc": "Index and middle fingers extended in V-shape"},
    "3": {"hindi": "तीन", "translit": "Teen", "phonetic": "three", "handedness": "one-handed", "contact": "three-finger", "desc": "Thumb, index, and middle fingers extended"},
    "4": {"hindi": "चार", "translit": "Chaar", "phonetic": "four", "handedness": "one-handed", "contact": "four-finger", "desc": "Four fingers extended, thumb folded across palm"},
    "5": {"hindi": "पाँच", "translit": "Paanch", "phonetic": "five", "handedness": "one-handed", "contact": "open-palm", "desc": "All five fingers fully spread and extended"},
    "6": {"hindi": "छह", "translit": "Chhah", "phonetic": "six", "handedness": "two-handed", "contact": "thumb-touch", "desc": "Dominant hand shows 5, secondary shows 1"},
    "7": {"hindi": "सात", "translit": "Saat", "phonetic": "seven", "handedness": "two-handed", "contact": "palm-touch", "desc": "Dominant hand shows 5, secondary shows 2"},
    "8": {"hindi": "आठ", "translit": "Aath", "phonetic": "eight", "handedness": "two-handed", "contact": "palm-touch", "desc": "Dominant hand shows 5, secondary shows 3"},
    "9": {"hindi": "नौ", "translit": "Nau", "phonetic": "nine", "handedness": "two-handed", "contact": "palm-touch", "desc": "Dominant hand shows 5, secondary shows 4"},
    "A": {"hindi": "ए", "translit": "A", "phonetic": "ay", "handedness": "two-handed", "contact": "index-to-thumb", "desc": "Both index fingertips meet at top like peak of letter A"},
    "B": {"hindi": "बी", "translit": "B", "phonetic": "bee", "handedness": "two-handed", "contact": "double-o", "desc": "Thumbs and index fingers of both hands form twin loops"},
    "C": {"hindi": "सी", "translit": "C", "phonetic": "see", "handedness": "one-handed", "contact": "curved-c", "desc": "Curved fingers and thumb form letter C profile"},
    "D": {"hindi": "डी", "translit": "D", "phonetic": "dee", "handedness": "two-handed", "contact": "index-loop", "desc": "Secondary hand index forms upright stem, dominant forms loop"},
    "E": {"hindi": "ई", "translit": "E", "phonetic": "ee", "handedness": "two-handed", "contact": "three-horizontal", "desc": "Index points to tip of index finger on other hand"},
    "F": {"hindi": "एफ", "translit": "F", "phonetic": "eff", "handedness": "two-handed", "contact": "cross-fingers", "desc": "Two index fingers crossed across each other"},
    "G": {"hindi": "जी", "translit": "G", "phonetic": "jee", "handedness": "two-handed", "contact": "fist-stack", "desc": "Two closed fists placed one on top of the other"},
    "H": {"hindi": "एच", "translit": "H", "phonetic": "aych", "handedness": "two-handed", "contact": "palm-cross", "desc": "Dominant palm strokes horizontal palm of secondary hand"},
    "I": {"hindi": "आई", "translit": "I", "phonetic": "eye", "handedness": "one-handed", "contact": "pinky-up", "desc": "Little finger (pinky) extended vertically upwards"},
    "J": {"hindi": "जे", "translit": "J", "phonetic": "jay", "handedness": "one-handed", "contact": "pinky-trace", "desc": "Pinky traces curved J stroke in air"},
    "K": {"hindi": "के", "translit": "K", "phonetic": "kay", "handedness": "two-handed", "contact": "v-on-index", "desc": "Dominant index forms diagonal stroke on upright index"},
    "L": {"hindi": "एल", "translit": "L", "phonetic": "el", "handedness": "one-handed", "contact": "l-shape", "desc": "Thumb and index finger form 90-degree right angle L"},
    "M": {"hindi": "एम", "translit": "M", "phonetic": "em", "handedness": "two-handed", "contact": "three-on-palm", "desc": "Three fingers of dominant hand rest across secondary palm"},
    "N": {"hindi": "एन", "translit": "N", "phonetic": "en", "handedness": "two-handed", "contact": "two-on-palm", "desc": "Two fingers of dominant hand rest across secondary palm"},
    "O": {"hindi": "ओ", "translit": "O", "phonetic": "oh", "handedness": "one-handed", "contact": "circle-o", "desc": "Fingers and thumb curved touching to form circular O"},
    "P": {"hindi": "पी", "translit": "P", "phonetic": "pee", "handedness": "two-handed", "contact": "index-circle", "desc": "Dominant hand forms loop on top of upright secondary index"},
    "Q": {"hindi": "क्यू", "translit": "Q", "phonetic": "kyoo", "handedness": "two-handed", "contact": "circle-hook", "desc": "Dominant hand hooks thumb into loop formed on secondary palm"},
    "R": {"hindi": "आर", "translit": "R", "phonetic": "aar", "handedness": "two-handed", "contact": "curved-hook", "desc": "Dominant curved index hooked over secondary index"},
    "S": {"hindi": "एस", "translit": "S", "phonetic": "ess", "handedness": "two-handed", "contact": "pinky-interlock", "desc": "Little fingers of both hands hooked together"},
    "T": {"hindi": "टी", "translit": "T", "phonetic": "tee", "handedness": "two-handed", "contact": "t-junction", "desc": "Dominant index touches side of vertical secondary index at midpoint"},
    "U": {"hindi": "यू", "translit": "U", "phonetic": "yoo", "handedness": "one-handed", "contact": "parallel-up", "desc": "Index and middle fingers held closely together pointing up"},
    "V": {"hindi": "वी", "translit": "V", "phonetic": "vee", "handedness": "one-handed", "contact": "spread-v", "desc": "Index and middle fingers spread in distinct V shape"},
    "W": {"hindi": "डब्ल्यू", "translit": "W", "phonetic": "double-yoo", "handedness": "one-handed", "contact": "spread-w", "desc": "Index, middle, and ring fingers spread upwards in W shape"},
    "X": {"hindi": "एक्स", "translit": "X", "phonetic": "ex", "handedness": "two-handed", "contact": "index-cross", "desc": "Both index fingers crossed horizontally to form an X"},
    "Y": {"hindi": "वाई", "translit": "Y", "phonetic": "wye", "handedness": "one-handed", "contact": "thumb-pinky", "desc": "Thumb and little finger extended outwards, other fingers curled"},
    "Z": {"hindi": "ज़ेड", "translit": "Zed", "phonetic": "zed", "handedness": "one-handed", "contact": "z-trace", "desc": "Index finger traces Z trajectory in air"}
}

ISL_WORDS_METADATA: Dict[str, Dict[str, Any]] = {
    # Greetings & Courtesies
    "NAMASTE": {"hindi": "नमस्ते", "translit": "Namaste", "phonetic": "nuh-muh-STAY", "handedness": "two-handed", "contact": "palms-together", "category": "greeting", "desc": "Both palms pressed flat together at chest level in traditional greeting gesture"},
    "HELLO": {"hindi": "नमस्ते", "translit": "Hello", "phonetic": "heh-LOH", "handedness": "one-handed", "contact": "temple-wave", "category": "greeting", "desc": "Open hand salutatory wave outward from side of forehead/temple"},
    "GOOD_MORNING": {"hindi": "सुप्रभात", "translit": "Suprabhat", "phonetic": "suh-pruh-BHAAT", "handedness": "two-handed", "contact": "chest-to-sun", "category": "greeting", "desc": "Sign for GOOD followed by rising sun gesture with spreading fingers"},
    "GOOD_AFTERNOON": {"hindi": "शुभ दोपहर", "translit": "Shubh Dopahar", "phonetic": "shubh doh-puh-HAR", "handedness": "two-handed", "contact": "mid-arc", "category": "greeting", "desc": "Sign for GOOD followed by hand positioned overhead representing midday sun"},
    "GOOD_NIGHT": {"hindi": "शुभ रात्रि", "translit": "Shubh Ratri", "phonetic": "shubh RAA-tree", "handedness": "two-handed", "contact": "sunset-arc", "category": "greeting", "desc": "Sign for GOOD followed by dominant hand descending over horizon palm"},
    "THANK_YOU": {"hindi": "धन्यवाद", "translit": "Dhanyavad", "phonetic": "DHUN-yuh-vaad", "handedness": "one-handed", "contact": "chin-forward", "category": "courtesy", "desc": "Fingertips touch chin and hand moves smoothly outward toward recipient with open palm"},
    "WELCOME": {"hindi": "स्वागत", "translit": "Swagat", "phonetic": "swaa-GUT", "handedness": "two-handed", "contact": "inward-sweep", "category": "courtesy", "desc": "Both open palms sweep inward towards body in welcoming arc"},
    "PLEASE": {"hindi": "कृपया", "translit": "Kripaya", "phonetic": "krih-puh-YAA", "handedness": "one-handed", "contact": "chest-circle", "category": "courtesy", "desc": "Flat open palm rubs center of chest in gentle circular motion"},
    "SORRY": {"hindi": "माफ़ कीजिए", "translit": "Maaf Kijiye", "phonetic": "maaf kee-jee-YAY", "handedness": "one-handed", "contact": "fist-circle", "category": "courtesy", "desc": "Closed fist with thumb upright rubs center of chest in contrite circular motion"},
    "EXCUSE_ME": {"hindi": "क्षमा करें", "translit": "Kshama Karein", "phonetic": "kshu-MAA kuh-REIN", "handedness": "two-handed", "contact": "fingertip-brush", "category": "courtesy", "desc": "Fingertips brush across secondary open palm twice politely"},
    
    # Pronouns & People
    "I": {"hindi": "मैं", "translit": "Main", "phonetic": "mye", "handedness": "one-handed", "contact": "point-chest", "category": "pronoun", "desc": "Index finger points directly to speaker's own chest"},
    "ME": {"hindi": "मुझे", "translit": "Mujhe", "phonetic": "MOO-jhay", "handedness": "one-handed", "contact": "touch-chest", "category": "pronoun", "desc": "Flat palm or index gently rests on center of chest"},
    "YOU": {"hindi": "आप", "translit": "Aap", "phonetic": "aap", "handedness": "one-handed", "contact": "point-forward", "category": "pronoun", "desc": "Index finger points forward toward conversational partner"},
    "WE": {"hindi": "हम", "translit": "Hum", "phonetic": "hum", "handedness": "one-handed", "contact": "chest-arc", "category": "pronoun", "desc": "Index finger moves from dominant shoulder across chest in arc to secondary shoulder"},
    "THEY": {"hindi": "वे", "translit": "Ve", "phonetic": "vay", "handedness": "one-handed", "contact": "side-sweep", "category": "pronoun", "desc": "Index finger sweeps horizontally across peripheral group space"},
    "HE": {"hindi": "वह", "translit": "Vah", "phonetic": "vuh", "handedness": "one-handed", "contact": "point-lateral", "category": "pronoun", "desc": "Index finger points laterally to third person reference point"},
    "SHE": {"hindi": "वह", "translit": "Vah", "phonetic": "vuh", "handedness": "one-handed", "contact": "point-lateral", "category": "pronoun", "desc": "Index finger points laterally to female third person reference point"},
    "FRIEND": {"hindi": "दोस्त", "translit": "Dost", "phonetic": "dohst", "handedness": "two-handed", "contact": "hook-interlock", "category": "people", "desc": "Curved index fingers hook into each other and reverse positions in mutual bond"},
    "FAMILY": {"hindi": "परिवार", "translit": "Parivar", "phonetic": "puh-ree-VAAR", "handedness": "two-handed", "contact": "f-circle", "category": "people", "desc": "F-handshapes start touching and sweep outwards forming an embracing circle"},
    "MOTHER": {"hindi": "माँ", "translit": "Maa", "phonetic": "maa", "handedness": "one-handed", "contact": "chin-thumb", "category": "people", "desc": "Thumb of open 5-hand taps side of chin twice gently"},
    "FATHER": {"hindi": "पिता", "translit": "Pita", "phonetic": "pih-TAA", "handedness": "one-handed", "contact": "forehead-thumb", "category": "people", "desc": "Thumb of open 5-hand taps forehead twice firmly"},
    "BROTHER": {"hindi": "भाई", "translit": "Bhai", "phonetic": "bhaaye", "handedness": "two-handed", "contact": "horizontal-bars", "category": "people", "desc": "Male forehead indicator followed by index fingers meeting in parallel alignment"},
    "SISTER": {"hindi": "बहन", "translit": "Behan", "phonetic": "beh-HUN", "handedness": "two-handed", "contact": "horizontal-bars", "category": "people", "desc": "Female chin indicator followed by index fingers meeting in parallel alignment"},
    "TEACHER": {"hindi": "अध्यापक", "translit": "Adhyapak", "phonetic": "ud-HYAA-puk", "handedness": "two-handed", "contact": "temple-forward", "category": "people", "desc": "Flattened O hands at temples move forward opening up into knowledge dispersal"},
    "DOCTOR": {"hindi": "डॉक्टर", "translit": "Doctor", "phonetic": "DOK-ter", "handedness": "two-handed", "contact": "wrist-tap", "category": "people", "desc": "M or D hand fingertips tap inner pulse point of secondary wrist"},
    "POLICE": {"hindi": "पुलिस", "translit": "Police", "phonetic": "puh-LEES", "handedness": "one-handed", "contact": "chest-badge", "category": "people", "desc": "C-handshape taps left chest where police badge sits"},
    
    # Common Actions & Needs
    "HELP": {"hindi": "मदद", "translit": "Madad", "phonetic": "muh-DUD", "handedness": "two-handed", "contact": "fist-on-palm", "category": "action", "desc": "Closed fist with thumb extended rests atop secondary open palm and lifts upward together"},
    "WANT": {"hindi": "चाहिए", "translit": "Chahiye", "phonetic": "chaa-HEE-yay", "handedness": "two-handed", "contact": "claw-pull", "category": "action", "desc": "Both open clawed hands pull backwards toward torso expressing desire"},
    "NEED": {"hindi": "ज़रूरत", "translit": "Zaroorat", "phonetic": "zuh-ROO-rut", "handedness": "one-handed", "contact": "x-down", "category": "action", "desc": "Bent index finger nods downwards emphatically once or twice"},
    "EAT": {"hindi": "खाना", "translit": "Khana", "phonetic": "KHAA-naa", "handedness": "one-handed", "contact": "mouth-pinch", "category": "action", "desc": "Flattened O hand brings fingers repeatedly to mouth simulating eating"},
    "DRINK": {"hindi": "पीना", "translit": "Peena", "phonetic": "PEE-naa", "handedness": "one-handed", "contact": "c-cup", "category": "action", "desc": "C-shaped hand tilts back towards lips simulating drinking from glass"},
    "GO": {"hindi": "जाना", "translit": "Jaana", "phonetic": "JAA-naa", "handedness": "two-handed", "contact": "point-arc", "category": "action", "desc": "Index fingers roll over each other and point outward away from body"},
    "COME": {"hindi": "आना", "translit": "Aana", "phonetic": "AA-naa", "handedness": "two-handed", "contact": "inward-beckon", "category": "action", "desc": "Both index fingers beckon inwards towards the body"},
    "STOP": {"hindi": "रुको", "translit": "Ruko", "phonetic": "roo-KOH", "handedness": "two-handed", "contact": "palm-chop", "category": "action", "desc": "Dominant open hand with sharp edge chops down vertically onto open flat secondary palm"},
    "LIKE": {"hindi": "पसंद", "translit": "Pasand", "phonetic": "puh-SUND", "handedness": "one-handed", "contact": "chest-pinch", "category": "action", "desc": "Thumb and middle finger contact chest and pull forward closing together"},
    "LOVE": {"hindi": "प्यार", "translit": "Pyaar", "phonetic": "pyaar", "handedness": "two-handed", "contact": "arms-cross", "category": "action", "desc": "Both arms crossed over chest in heartfelt embrace clasping shoulders"},
    "LEARN": {"hindi": "सीखना", "translit": "Seekhna", "phonetic": "SEEKH-naa", "handedness": "two-handed", "contact": "palm-to-forehead", "category": "action", "desc": "Dominant fingers gather knowledge from secondary open palm and place it onto forehead"},
    "MEET": {"hindi": "मिलना", "translit": "Milna", "phonetic": "MIL-naa", "handedness": "two-handed", "contact": "index-converge", "category": "action", "desc": "Both index fingers upright converge from distance until knuckles touch"},
    "WORK": {"hindi": "काम", "translit": "Kaam", "phonetic": "kaam", "handedness": "two-handed", "contact": "fist-tap-fist", "category": "action", "desc": "Dominant fist taps heel of secondary fist twice with solid downward motion"},
    
    # Question Words
    "WHAT": {"hindi": "क्या", "translit": "Kya", "phonetic": "kyaa", "handedness": "two-handed", "contact": "open-palms-shrug", "category": "question", "desc": "Both open palms face up, moving side-to-side with questioning facial expression"},
    "WHERE": {"hindi": "कहाँ", "translit": "Kahan", "phonetic": "kuh-HAAN", "handedness": "one-handed", "contact": "index-wag", "category": "question", "desc": "Upright index finger wags left and right side to side in searching motion"},
    "WHEN": {"hindi": "कब", "translit": "Kab", "phonetic": "kub", "handedness": "two-handed", "contact": "index-circle", "category": "question", "desc": "Dominant index circles around stationary secondary index finger and lands on tip"},
    "WHY": {"hindi": "क्यों", "translit": "Kyon", "phonetic": "kyon", "handedness": "one-handed", "contact": "forehead-pull", "category": "question", "desc": "Fingers touch forehead and pull down into Y handshape"},
    "HOW": {"hindi": "कैसे", "translit": "Kaise", "phonetic": "KYE-say", "handedness": "two-handed", "contact": "curved-roll", "category": "question", "desc": "Backs of curved fingers touch and roll forward to reveal upturned open palms"},
    "WHO": {"hindi": "कौन", "translit": "Kaun", "phonetic": "kown", "handedness": "one-handed", "contact": "chin-circle", "category": "question", "desc": "Index finger circles around mouth or wiggles near lip corner"},
    
    # Nouns, Places & Essentials
    "FOOD": {"hindi": "भोजन", "translit": "Bhojan", "phonetic": "BHO-jun", "handedness": "one-handed", "contact": "fingertip-mouth", "category": "essential", "desc": "Flattened O hand repeatedly taps lips indicating nourishment"},
    "WATER": {"hindi": "पानी", "translit": "Paani", "phonetic": "PAA-nee", "handedness": "one-handed", "contact": "w-chin", "category": "essential", "desc": "W-handshape index finger taps chin or side of mouth twice"},
    "HOME": {"hindi": "घर", "translit": "Ghar", "phonetic": "ghur", "handedness": "two-handed", "contact": "roof-peak", "category": "place", "desc": "Flat open hands form triangular slanted roof peak touching at fingertips"},
    "SCHOOL": {"hindi": "स्कूल", "translit": "School", "phonetic": "skool", "handedness": "two-handed", "contact": "palm-clap", "category": "place", "desc": "Dominant palm claps horizontally twice onto stationary secondary palm"},
    "HOSPITAL": {"hindi": "अस्पताल", "translit": "Aspataal", "phonetic": "us-puh-TAAL", "handedness": "one-handed", "contact": "cross-shoulder", "category": "place", "desc": "H-handshape traces red cross on opposite upper arm/shoulder"},
    "MEDICINE": {"hindi": "दवा", "translit": "Dawa", "phonetic": "duh-VAA", "handedness": "two-handed", "contact": "palm-grind", "category": "essential", "desc": "Middle finger twists inside secondary palm simulating mortar and pestle"},
    "MONEY": {"hindi": "पैसा", "translit": "Paisa", "phonetic": "PYE-saa", "handedness": "one-handed", "contact": "thumb-rub", "category": "essential", "desc": "Thumb rubs tips of index and middle fingers in universal currency sign"},
    "BOOK": {"hindi": "किताब", "translit": "Kitaab", "phonetic": "kih-TAAB", "handedness": "two-handed", "contact": "palms-open", "category": "object", "desc": "Palms held together vertically open outward like opening covers of book"},
    "CAT": {"hindi": "बिल्ली", "translit": "Billi", "phonetic": "BIL-lee", "handedness": "one-handed", "contact": "whiskers", "category": "object", "desc": "Fingers sweep across cheek mimicking feline whiskers"},
    "DOG": {"hindi": "कुत्ता", "translit": "Kutta", "phonetic": "KOOT-taa", "handedness": "one-handed", "contact": "thigh-pat", "category": "object", "desc": "Hand pats thigh then snaps fingers calling canine"},
    "NAME": {"hindi": "नाम", "translit": "Naam", "phonetic": "naam", "handedness": "two-handed", "contact": "h-tap", "category": "essential", "desc": "H-handshapes of both hands tap each other across knuckles twice"},
    "SIGN": {"hindi": "संकेत", "translit": "Sanket", "phonetic": "sun-KAYT", "handedness": "two-handed", "contact": "alternating-circles", "category": "action", "desc": "Both open hands move in alternating circular paths in front of chest"},
    
    # States & Responses
    "YES": {"hindi": "हाँ", "translit": "Haan", "phonetic": "haan", "handedness": "one-handed", "contact": "fist-nod", "category": "response", "desc": "Closed S-fist nods up and down at wrist like nodding head"},
    "NO": {"hindi": "नहीं", "translit": "Nahin", "phonetic": "nuh-HEEN", "handedness": "one-handed", "contact": "three-snap", "category": "response", "desc": "Index and middle fingers snap shut against thumb firmly"},
    "GOOD": {"hindi": "अच्छा", "translit": "Achha", "phonetic": "UCHH-aa", "handedness": "one-handed", "contact": "chin-forward", "category": "state", "desc": "Flat hand touches chin and moves forward and down into open palm"},
    "BAD": {"hindi": "बुरा", "translit": "Bura", "phonetic": "BOO-raa", "handedness": "one-handed", "contact": "chin-flip", "category": "state", "desc": "Flat hand touches chin and flips palm sharply downward facing the floor"},
    "HAPPY": {"hindi": "खुश", "translit": "Khush", "phonetic": "khoosh", "handedness": "two-handed", "contact": "chest-brush-up", "category": "state", "desc": "Open palms brush upward repeatedly across chest radiating joy"},
    "SAD": {"hindi": "उदास", "translit": "Udaas", "phonetic": "oo-DAAS", "handedness": "two-handed", "contact": "face-droop", "category": "state", "desc": "Open hands in front of face droop downwards while facial posture sags"},
    "PAIN": {"hindi": "दर्द", "translit": "Dard", "phonetic": "durd", "handedness": "two-handed", "contact": "index-twist", "category": "state", "desc": "Both index fingers point at each other and twist sharply with furrowed brow"},
    
    # Time
    "TIME": {"hindi": "समय", "translit": "Samay", "phonetic": "suh-MYE", "handedness": "one-handed", "contact": "wrist-tap", "category": "time", "desc": "Index finger taps wrist where wristwatch is worn"},
    "TODAY": {"hindi": "आज", "translit": "Aaj", "phonetic": "aaj", "handedness": "two-handed", "contact": "y-down", "category": "time", "desc": "Both Y-hands drop downward smoothly in front of body"},
    "TOMORROW": {"hindi": "कल", "translit": "Kal", "phonetic": "kul", "handedness": "one-handed", "contact": "cheek-roll", "category": "time", "desc": "A-hand thumb touches cheek and rolls forward indicating future day"},
    "YESTERDAY": {"hindi": "बीता कल", "translit": "Beeta Kal", "phonetic": "BEE-taa kul", "handedness": "one-handed", "contact": "chin-to-ear", "category": "time", "desc": "Y or A hand moves backward from chin to behind ear indicating past day"}
}

ALL_SIGNS: Dict[str, Dict[str, Any]] = {}

# Merge into unified knowledge catalog
for sign, meta in ALPHANUMERIC_METADATA.items():
    category = "number" if sign.isdigit() else "alphabet"
    ALL_SIGNS[sign] = {
        "label": sign,
        "type": category,
        "category": category,
        "is_alphanumeric": True,
        **meta
    }

for sign, meta in ISL_WORDS_METADATA.items():
    ALL_SIGNS[sign] = {
        "label": sign,
        "type": "word",
        "is_alphanumeric": False,
        **meta
    }

def get_sign_info(sign_name: str) -> Optional[Dict[str, Any]]:
    """Retrieve structured metadata for any alphanumeric or ISL word."""
    norm = sign_name.strip().upper()
    return ALL_SIGNS.get(norm)

def is_alphanumeric(sign_name: str) -> bool:
    """Check if sign is an alphanumeric class (1-9, A-Z)."""
    norm = sign_name.strip().upper()
    return norm in ALPHANUMERIC_CLASSES

def is_word(sign_name: str) -> bool:
    """Check if sign is a recognized ISL vocabulary word."""
    norm = sign_name.strip().upper()
    return norm in ISL_WORDS_METADATA

def get_all_alphanumeric_classes() -> List[str]:
    """Return ordered list of 35 alphanumeric classes."""
    return list(ALPHANUMERIC_CLASSES)

def get_all_words() -> List[str]:
    """Return ordered list of all ISL vocabulary words."""
    return list(ISL_WORDS_METADATA.keys())

def get_class_index(label: str) -> int:
    """Return 0-indexed classification id for alphanumeric class."""
    norm = label.strip().upper()
    if norm not in CLASS_TO_INDEX:
        raise ValueError(f"Label '{label}' not in 35 alphanumeric classes.")
    return CLASS_TO_INDEX[norm]

def get_label_from_index(idx: int) -> str:
    """Return alphanumeric label from index."""
    if idx not in INDEX_TO_CLASS:
        raise ValueError(f"Index {idx} out of bounds for 35 classes [0..34].")
    return INDEX_TO_CLASS[idx]

def search_signs(query: str) -> List[Dict[str, Any]]:
    """Search knowledge base by English label, Hindi word, or transliteration."""
    q = query.strip().lower()
    results = []
    for k, v in ALL_SIGNS.items():
        if (q in k.lower() or 
            q in v.get("hindi", "") or 
            q in v.get("translit", "").lower() or 
            q in v.get("desc", "").lower()):
            results.append(v)
    return results

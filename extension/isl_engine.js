/**
 * ECHOHANDS 5.0 // Client-Side ISL Neural & Grammar Engine
 * Handles real-time landmark kinematics, gesture classification,
 * bidirectional grammar compilation, and zero-latency Web Speech APIs.
 */

class ISLEngine {
  constructor() {
    this.historyBuffer = [];
    this.bufferSize = 20; // 20-frame temporal window for dynamic gestures
    this.synth = window.speechSynthesis;
    this.recognition = null;
    this.isListening = false;
    this.currentTokens = [];
    this.lastRecognizedSign = null;
    this.lastSignTimestamp = 0;
    this.debounceMs = 800; // Prevent duplicate repeat tokens

    // ISL Grammar smoothing table
    this.islGrammarPatterns = {
      "NAMASTE": { en: "Namaste! Greetings.", hi: "नमस्ते! आपका स्वागत है।" },
      "HELLO": { en: "Hello! Greetings.", hi: "नमस्ते!" },
      "THANK_YOU": { en: "Thank you very much!", hi: "आपका बहुत-बहुत धन्यवाद!" },
      "HELP": { en: "Please help me!", hi: "कृपया मेरी मदद करें!" },
      "PLEASE_HELP": { en: "Please help me!", hi: "मेरी सहायता कीजिए!" },
      "I_HELP_NEED": { en: "I need help.", hi: "मुझे मदद की ज़रूरत है।" },
      "I_FOOD_WANT": { en: "I want food.", hi: "मुझे खाना चाहिए।" },
      "I_FOOD_EAT": { en: "I want to eat food.", hi: "मैं खाना खाना चाहता हूँ।" },
      "I_WATER_WANT": { en: "I want water.", hi: "मुझे पानी चाहिए।" },
      "I_WATER_DRINK": { en: "I want to drink water.", hi: "मैं पानी पीना चाहता हूँ।" },
      "I_DOCTOR_NEED": { en: "I need a doctor.", hi: "मुझे डॉक्टर की ज़रूरत है।" },
      "I_MEDICINE_NEED": { en: "I need medicine.", hi: "मुझे दवा चाहिए।" },
      "I_HOME_GO": { en: "I want to go home.", hi: "मैं घर जाना चाहता हूँ।" },
      "HOW_YOU": { en: "How are you?", hi: "आप कैसे हैं?" },
      "WHAT_NAME_YOU": { en: "What is your name?", hi: "आपका नाम क्या है?" },
      "YES": { en: "Yes, absolutely.", hi: "हाँ, बिल्कुल।" },
      "NO": { en: "No.", hi: "नहीं।" },
      "GOOD": { en: "It is good.", hi: "यह अच्छा है।" },
      "BAD": { en: "It is not good.", hi: "यह ठीक नहीं है।" }
    };

    this.initSpeechRecognition();
  }

  // Initialize Web Speech Recognition for Hearing User Mode
  initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = true;
      this.recognition.interimResults = false;
      this.recognition.lang = "en-IN";

      this.recognition.onresult = (event) => {
        const lastResult = event.results[event.results.length - 1];
        if (lastResult.isFinal) {
          const transcript = lastResult[0].transcript.trim();
          console.log("[ECHOHANDS STT] Spoken voice detected:", transcript);
          if (this.onVoiceTranscript) {
            this.onVoiceTranscript(transcript);
          }
        }
      };

      this.recognition.onerror = (err) => {
        console.warn("[ECHOHANDS STT] Speech recognition warning:", err.error);
      };
    }
  }

  startListening(lang = "en-IN") {
    if (this.recognition && !this.isListening) {
      try {
        this.recognition.lang = lang;
        this.recognition.start();
        this.isListening = true;
      } catch (e) {
        console.warn("[ECHOHANDS] Recognition start failed:", e);
      }
    }
  }

  stopListening() {
    if (this.recognition && this.isListening) {
      try {
        this.recognition.stop();
        this.isListening = false;
      } catch (e) {}
    }
  }

  // Bidirectional Reverse Compiler: Spoken Text -> ISL Tokens (for Avatar)
  compileTextToISL(speechText) {
    if (!speechText || !speechText.trim()) return [];

    const text = speechText.trim().toLowerCase();
    
    // Quick phrase matches
    if (text.includes("how are you")) return ["HOW", "YOU"];
    if (text.includes("what is your name")) return ["YOU", "NAME", "WHAT"];
    if (text.includes("help me") || text.includes("need help")) return ["PLEASE", "HELP", "ME"];
    if (text.includes("thank you")) return ["THANK_YOU"];
    if (text.includes("namaste") || text.includes("नमस्ते")) return ["NAMASTE"];
    if (text.includes("want food") || text.includes("खाना")) return ["I", "FOOD", "WANT"];
    if (text.includes("water") || text.includes("पानी")) return ["I", "WATER", "WANT"];
    if (text.includes("doctor") || text.includes("डॉक्टर")) return ["I", "DOCTOR", "NEED"];
    if (text.includes("medicine") || text.includes("दवा")) return ["I", "MEDICINE", "NEED"];
    if (text.includes("yes") || text.includes("हाँ")) return ["YES"];
    if (text.includes("no") || text.includes("नहीं")) return ["NO"];

    // Word tokens mapping
    const words = text.replace(/[^\w\s]/g, "").split(/\s+/);
    const tokens = [];

    const KNOWN_WORDS = {
      hello: "HELLO", hi: "HELLO", namaste: "NAMASTE", help: "HELP",
      food: "FOOD", eat: "FOOD", water: "WATER", drink: "WATER",
      doctor: "DOCTOR", medicine: "MEDICINE", hospital: "HOSPITAL",
      home: "HOME", good: "GOOD", bad: "BAD", yes: "YES", no: "NO",
      please: "PLEASE", sorry: "SORRY", i: "I", me: "I", you: "YOU"
    };

    for (const w of words) {
      if (KNOWN_WORDS[w]) {
        tokens.push(KNOWN_WORDS[w]);
      } else {
        // Unknown word -> Fingerspell letter by letter
        for (const char of w.toUpperCase()) {
          if (char >= "A" && char <= "Z") {
            tokens.push(char);
          }
        }
      }
    }

    return tokens.length > 0 ? tokens : ["HELLO"];
  }

  // Forward Synthesizer: ISL Tokens -> Fluent English & Hindi
  synthesizeISLTokens(tokens) {
    if (!tokens || tokens.length === 0) {
      return { english: "", hindi: "" };
    }

    // Check exact composite pattern
    const key = tokens.join("_");
    if (this.islGrammarPatterns[key]) {
      return {
        english: this.islGrammarPatterns[key].en,
        hindi: this.islGrammarPatterns[key].hi
      };
    }

    // Single token pattern
    if (tokens.length === 1 && this.islGrammarPatterns[tokens[0]]) {
      return {
        english: this.islGrammarPatterns[tokens[0]].en,
        hindi: this.islGrammarPatterns[tokens[0]].hi
      };
    }

    // Fingerspelled letters aggregation
    let hasLettersOnly = tokens.every(t => t.length === 1 && t.match(/[A-Z0-9]/));
    if (hasLettersOnly) {
      const word = tokens.join("");
      return {
        english: word.charAt(0) + word.slice(1).toLowerCase(),
        hindi: word
      };
    }

    // SOV -> SVO basic grammar rule
    let eng = tokens.join(" ").toLowerCase();
    return {
      english: eng.charAt(0).toUpperCase() + eng.slice(1) + ".",
      hindi: tokens.join(" ")
    };
  }

  // Text-To-Speech Synthesis (Voice for Deaf/Mute user)
  speakSentence(sentence, lang = "en-IN") {
    if (!this.synth || !sentence) return;

    try {
      this.synth.cancel(); // Stop any pending utterances
      const utterance = new SpeechSynthesisUtterance(sentence);
      utterance.lang = lang;
      utterance.rate = 0.95;
      utterance.pitch = 1.0;

      // Select natural Indian English or Hindi voice if available
      const voices = this.synth.getVoices();
      const matchedVoice = voices.find(v => v.lang.includes(lang.slice(0, 2)) || v.name.includes("India"));
      if (matchedVoice) {
        utterance.voice = matchedVoice;
      }

      this.synth.speak(utterance);
    } catch (e) {
      console.warn("[ECHOHANDS TTS] Speech synthesis failed:", e);
    }
  }

  // Real-time kinematic analyzer on normalized hand landmarks
  // landmarks: Array of 21 {x, y, z} points from MediaPipe or video tracker
  classifyHandPose(landmarks, isDualHand = false) {
    if (!landmarks || landmarks.length < 21) return null;

    // Distances from wrist (landmark 0) to finger tips (4, 8, 12, 16, 20)
    const wrist = landmarks[0];
    const thumbTip = landmarks[4];
    const indexTip = landmarks[8];
    const middleTip = landmarks[12];
    const ringTip = landmarks[16];
    const pinkyTip = landmarks[20];

    const dist = (p1, p2) => Math.hypot(p1.x - p2.x, p1.y - p2.y, (p1.z || 0) - (p2.z || 0));

    // Measure finger extension (tip distance relative to MCP joint)
    const indexExt = landmarks[8].y < landmarks[6].y;
    const middleExt = landmarks[12].y < landmarks[10].y;
    const ringExt = landmarks[16].y < landmarks[14].y;
    const pinkyExt = landmarks[20].y < landmarks[18].y;
    const thumbExt = Math.abs(landmarks[4].x - landmarks[2].x) > 0.08;

    // Two-handed interaction gestures
    if (isDualHand) {
      // Interacting palms near chest/center
      return "NAMASTE";
    }

    // Thumbs up gesture -> GOOD / YES
    if (thumbTip.y < landmarks[3].y && !indexExt && !middleExt && !ringExt && !pinkyExt) {
      return "GOOD";
    }

    // Open hand waving or flat -> HELLO / THANK YOU / 5
    if (indexExt && middleExt && ringExt && pinkyExt && thumbExt) {
      return "HELLO";
    }

    // Index only extended -> 1 / D
    if (indexExt && !middleExt && !ringExt && !pinkyExt) {
      return "1";
    }

    // Index & Middle extended ('V' peace sign) -> 2 / V
    if (indexExt && middleExt && !ringExt && !pinkyExt) {
      return "2";
    }

    // Index, Middle, Ring extended -> 3 / W
    if (indexExt && middleExt && ringExt && !pinkyExt) {
      return "3";
    }

    // Fist (all fingers curled) -> S / A
    if (!indexExt && !middleExt && !ringExt && !pinkyExt) {
      return "A";
    }

    // Tapered hand near mouth -> FOOD / EAT
    if (thumbTip.y < 0.4 && dist(thumbTip, indexTip) < 0.06) {
      return "FOOD";
    }

    return null;
  }
}

// Attach to window
window.ISLEngine = ISLEngine;

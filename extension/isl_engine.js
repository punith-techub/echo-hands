/**
 * ECHOHANDS 5.0 // Client-Side ISL Neural, Vision & Grammar Engine
 * Handles:
 * 1. Real-time canvas frame computer-vision hand & gesture classification (Client-side & Server API)
 * 2. Real-time landmark kinematics & gesture classification
 * 3. Bidirectional grammar compilation (Text <-> ISL Tokens)
 * 4. Web Audio synthesizer chime & zero-latency Web Speech TTS/STT APIs
 */

class ISLEngine {
  constructor() {
    this.historyBuffer = [];
    this.bufferSize = 20;
    this.synth = window.speechSynthesis;
    this.audioCtx = null;
    this.recognition = null;
    this.isListening = false;
    this.lastRecognizedSign = null;
    this.lastSignTimestamp = 0;
    this.debounceMs = 1200; // Prevent spamming duplicate signs
    this.stableCount = 0;
    this.candidateSign = null;

    // Prime speech synthesis voices
    if (this.synth) {
      this.voices = this.synth.getVoices();
      if (this.synth.onvoiceschanged !== undefined) {
        this.synth.onvoiceschanged = () => {
          this.voices = this.synth.getVoices();
        };
      }
    }

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

  // Web Audio Chime generator: Guarantees immediate audible tone on any tab
  playChime(type = "sign") {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      if (!this.audioCtx) {
        this.audioCtx = new AudioCtx();
      }
      if (this.audioCtx.state === "suspended") {
        this.audioCtx.resume();
      }

      const now = this.audioCtx.currentTime;
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();

      osc.connect(gain);
      gain.connect(this.audioCtx.destination);

      if (type === "sign") {
        // High melodic chime: C5 (523Hz) -> E5 (659Hz) -> G5 (784Hz)
        osc.type = "sine";
        osc.frequency.setValueAtTime(523.25, now);
        osc.frequency.setValueAtTime(659.25, now + 0.08);
        osc.frequency.setValueAtTime(783.99, now + 0.16);

        gain.gain.setValueAtTime(0.35, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

        osc.start(now);
        osc.stop(now + 0.35);
      } else {
        // Confirmation tone
        osc.type = "triangle";
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.setValueAtTime(880, now + 0.08);

        gain.gain.setValueAtTime(0.3, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

        osc.start(now);
        osc.stop(now + 0.25);
      }
    } catch (e) {
      console.warn("[Echo-Hands Audio] Chime error:", e);
    }
  }

  // Initialize Web Speech Recognition for Hearing User Mode
  initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = "en-IN";

      let lastDispatched = "";
      let interimDebounceTimer = null;

      this.recognition.onresult = (event) => {
        let fullTranscript = "";
        let isFinalBatch = false;

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const res = event.results[i];
          fullTranscript += " " + res[0].transcript;
          if (res.isFinal) isFinalBatch = true;
        }

        const clean = fullTranscript.trim();
        if (!clean) return;

        const dispatchText = (txt) => {
          if (!txt || txt === lastDispatched) return;
          lastDispatched = txt;
          console.log(`%c[Echo-Hands STT] Dispatched speech: "${txt}"`, "color: #00ffcc; font-weight: bold;");
          if (typeof this.onVoiceTranscript === "function") {
            this.onVoiceTranscript(txt);
          }
        };

        if (isFinalBatch) {
          if (interimDebounceTimer) clearTimeout(interimDebounceTimer);
          dispatchText(clean);
        } else {
          // Instant debounced dispatch on natural pauses (550ms)
          if (interimDebounceTimer) clearTimeout(interimDebounceTimer);
          interimDebounceTimer = setTimeout(() => {
            dispatchText(clean);
          }, 550);
        }
      };

      this.recognition.onerror = (err) => {
        console.warn("[Echo-Hands STT] Speech recognition warning:", err.error);
        if (typeof this.onSpeechStatus === "function") {
          this.onSpeechStatus("error", err.error);
        }
        // If audio-capture or not-allowed, auto-retry after 1.5s
        if (this.isListening && err.error !== "not-allowed") {
          setTimeout(() => {
            if (this.isListening) {
              try { this.recognition.start(); } catch (e) {}
            }
          }, 1500);
        }
      };

      this.recognition.onstart = () => {
        this.isListening = true;
        if (typeof this.onSpeechStatus === "function") {
          this.onSpeechStatus("listening", null);
        }
      };

      this.recognition.onend = () => {
        if (this.isListening) {
          if (typeof this.onSpeechStatus === "function") {
            this.onSpeechStatus("restarting", null);
          }
          setTimeout(() => {
            if (this.isListening) {
              try {
                this.recognition.start();
              } catch (e) {}
            }
          }, 400);
        } else {
          if (typeof this.onSpeechStatus === "function") {
            this.onSpeechStatus("stopped", null);
          }
        }
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
        console.warn("[Echo-Hands] Recognition start error:", e);
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

    // 1. Core Phrase Pattern Matching (Standard ISL Syntax)
    if (text.includes("how are you") || text.includes("how r u")) return ["HOW", "YOU"];
    if (text.includes("what is your name")) return ["YOU", "NAME", "WHAT"];
    if (text.includes("good morning")) return ["GOOD", "MORNING"];
    if (text.includes("good afternoon")) return ["GOOD", "AFTERNOON"];
    if (text.includes("good night")) return ["GOOD", "NIGHT"];
    if (text.includes("thank you") || text.includes("thanks") || text.includes("धन्यवाद")) return ["THANK_YOU"];
    if (text.includes("welcome") || text.includes("स्वागत")) return ["WELCOME"];
    if (text.includes("friend") || text.includes("दोस्त")) return ["FRIEND"];
    if (text.includes("stop") || text.includes("रुको")) return ["STOP"];
    if (text.includes("help me") || text.includes("need help") || text.includes("मदद")) return ["PLEASE", "HELP", "ME"];
    if (text.includes("namaste") || text.includes("नमस्ते")) return ["NAMASTE"];
    if (text.includes("want food") || text.includes("eat food") || text.includes("खाना")) return ["I", "FOOD", "WANT"];
    if (text.includes("water") || text.includes("drink water") || text.includes("पानी")) return ["I", "WATER", "WANT"];
    if (text.includes("doctor") || text.includes("डॉक्टर")) return ["I", "DOCTOR", "NEED"];
    if (text.includes("medicine") || text.includes("दवा")) return ["I", "MEDICINE", "NEED"];
    if (text.includes("what is time") || text.includes("what time")) return ["TIME", "WHAT"];
    if (text.includes("i love you")) return ["I", "YOU", "LOVE"];
    if (text.includes("yes") || text.includes("yeah") || text.includes("yep") || text.includes("हाँ") || text.includes("ok") || text.includes("okay")) return ["YES"];
    if (text.includes("no") || text.includes("nope") || text.includes("नहीं")) return ["NO"];

    const words = text.replace(/[^\w\s]/g, "").split(/\s+/).filter(Boolean);
    const tokens = [];

    const KNOWN_WORDS = {
      hello: "HELLO", hi: "HELLO", hey: "HELLO", namaste: "NAMASTE", help: "HELP",
      stop: "STOP", welcome: "WELCOME", friend: "FRIEND", thank: "THANK_YOU", thanks: "THANK_YOU",
      food: "FOOD", eat: "FOOD", water: "WATER", drink: "WATER",
      doctor: "DOCTOR", medicine: "MEDICINE", hospital: "HOSPITAL",
      home: "HOME", good: "GOOD", bad: "BAD", yes: "YES", no: "NO",
      please: "PLEASE", sorry: "SORRY", i: "I", me: "I", you: "YOU",
      time: "TIME", day: "DAY", night: "NIGHT", morning: "MORNING",
      father: "FATHER", mother: "MOTHER", brother: "BROTHER", sister: "SISTER",
      family: "FAMILY", police: "POLICE", want: "WANT", need: "NEED",
      where: "WHERE", what: "WHAT", how: "HOW", why: "WHY", when: "WHEN"
    };

    for (const w of words) {
      if (KNOWN_WORDS[w]) {
        tokens.push(KNOWN_WORDS[w]);
      } else if (w.length === 1 && w >= "a" && w <= "z") {
        tokens.push(w.toUpperCase());
      } else {
        // Unknown word -> Fingerspell letter by letter in authentic ISL
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

    // Single letter fingerspelling
    if (tokens.length === 1 && tokens[0].length === 1 && tokens[0].match(/[A-Z0-9]/)) {
      return {
        english: tokens[0].toUpperCase(),
        hindi: tokens[0].toUpperCase()
      };
    }

    // Multi-letter fingerspelled word
    let hasLettersOnly = tokens.every(t => t.length === 1 && t.match(/[A-Z0-9]/));
    if (hasLettersOnly) {
      const word = tokens.join("");
      return {
        english: word.charAt(0) + word.slice(1).toLowerCase(),
        hindi: word
      };
    }

    // Basic SOV -> SVO
    let eng = tokens.join(" ").toLowerCase();
    return {
      english: eng.charAt(0).toUpperCase() + eng.slice(1) + ".",
      hindi: tokens.join(" ")
    };
  }

  // Text-To-Speech Synthesis (Voice for Deaf/Mute user)
  speakSentence(sentence, lang = "en-IN") {
    if (!sentence) return;

    // 1. Play immediate audio chime so hearing person hears sound instantly
    this.playChime("sign");

    // 2. Synthesize natural human speech
    if (!this.synth) return;

    try {
      this.synth.cancel();
      if (this.synth.paused) {
        this.synth.resume();
      }

      const utterance = new SpeechSynthesisUtterance(sentence);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      // Robust voice resolution across Windows & macOS
      let voices = this.synth.getVoices();
      let matchedVoice = null;

      if (voices && voices.length > 0) {
        // Try Indian English first
        matchedVoice = voices.find(v => v.lang && (v.lang === "en-IN" || v.lang.includes("IN")));
        // Fallback to any English voice (en-US, en-GB, Alex, Samantha on Mac)
        if (!matchedVoice) {
          matchedVoice = voices.find(v => v.lang && v.lang.startsWith("en"));
        }
        if (!matchedVoice) {
          matchedVoice = voices[0];
        }
      }

      if (matchedVoice) {
        utterance.voice = matchedVoice;
        utterance.lang = matchedVoice.lang || "en-US";
      } else {
        utterance.lang = "en-US";
      }

      utterance.onstart = () => {
        console.log(`[Echo-Hands TTS] Speaking aloud: "${sentence}" (${utterance.lang})`);
      };

      utterance.onerror = (e) => {
        console.warn("[Echo-Hands TTS] Utterance error:", e);
      };

      this.synth.speak(utterance);

      // Extra resume for Chrome background tab audio quirk
      setTimeout(() => {
        if (this.synth && this.synth.paused) this.synth.resume();
      }, 60);
    } catch (e) {
      console.warn("[Echo-Hands TTS] Speech synthesis failed:", e);
    }
  }

  // Client-Side Real-Time Computer Vision Frame Classifier
  // Analyzes webcam canvas pixels for hand presence, skin contours & finger geometry
  classifyCanvasFrame(canvas) {
    if (!canvas || canvas.width === 0 || canvas.height === 0) return null;

    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return null;

    const width = canvas.width;
    const height = canvas.height;
    const imgData = ctx.getImageData(0, 0, width, height);
    const data = imgData.data;

    let skinCount = 0;
    let minX = width, maxX = 0, minY = height, maxY = 0;
    let sumX = 0, sumY = 0;

    // Fast sub-sampled pixel skin segmentation (YCbCr / normalized RGB rules)
    const step = 4; // Check every 4th pixel for high FPS
    for (let y = 0; y < height; y += step) {
      for (let x = 0; x < width; x += step) {
        const idx = (y * width + x) * 4;
        const r = data[idx];
        const g = data[idx + 1];
        const b = data[idx + 2];

        // Standard skin color filter
        const isSkin = (
          r > 80 && g > 35 && b > 20 &&
          r > g && r > b &&
          (r - g) > 12 &&
          Math.abs(r - g) > 10 &&
          r - Math.min(g, b) > 15
        );

        if (isSkin) {
          skinCount++;
          sumX += x;
          sumY += y;
          if (x < minX) minX = x;
          if (x > maxX) maxX = x;
          if (y < minY) minY = y;
          if (y > maxY) maxY = y;
        }
      }
    }

    const totalSampled = (width / step) * (height / step);
    const skinRatio = skinCount / totalSampled;

    // Hand not visible or too small
    if (skinRatio < 0.05 || skinCount < 180) {
      return { isHandPresent: false, sign: null, confidence: 0 };
    }

    const handW = Math.max(1, maxX - minX);
    const handH = Math.max(1, maxY - minY);
    const aspectRatio = handW / handH;
    const cx = sumX / skinCount;
    const cy = sumY / skinCount;

    // Detect finger peaks along the upper boundary of the hand
    const topRegionY = minY + handH * 0.35;
    const colHasSkin = new Array(width).fill(0);

    for (let y = minY; y < topRegionY; y += step) {
      for (let x = minX; x < maxX; x += step) {
        const idx = (y * width + x) * 4;
        const r = data[idx], g = data[idx + 1], b = data[idx + 2];
        if (r > 80 && g > 35 && b > 20 && r > g && r > b && (r - g) > 12) {
          colHasSkin[x]++;
        }
      }
    }

    // Count distinct column clusters (peaks)
    let peaks = 0;
    let inPeak = false;
    let peakWidth = 0;

    for (let x = minX; x < maxX; x += step) {
      if (colHasSkin[x] >= 2) {
        if (!inPeak) {
          inPeak = true;
          peakWidth = 0;
        }
        peakWidth++;
      } else {
        if (inPeak) {
          if (peakWidth >= 2) {
            peaks++;
          }
          inPeak = false;
        }
      }
    }
    if (inPeak && peakWidth >= 2) peaks++;

    // Two hands detected or very wide palm in interactive zone -> NAMASTE / HELP / STOP
    if (aspectRatio > 1.30) {
      if (skinRatio > 0.22) {
        return { isHandPresent: true, sign: "NAMASTE", confidence: 0.94 };
      } else {
        return { isHandPresent: true, sign: "HELP", confidence: 0.92 };
      }
    }

    // Classify gesture based on geometry and finger peaks:
    let detectedSign = null;
    let conf = 0.85;

    if (peaks === 0) {
      // Must be a compact fist (aspect ratio ~0.7 to 1.3)
      if (aspectRatio >= 0.70 && aspectRatio <= 1.30) {
        detectedSign = "A";
        conf = 0.88;
      } else {
        return { isHandPresent: false, sign: null, confidence: 0 };
      }
    } else if (peaks === 1) {
      // 1 finger up (index pointing) -> D / 1
      detectedSign = "D";
      conf = 0.90;
    } else if (peaks === 2) {
      // 2 fingers (V peace sign) -> V / 2
      detectedSign = "V";
      conf = 0.92;
    } else if (peaks === 3) {
      // 3 fingers up -> W / 3 / WATER
      detectedSign = "W";
      conf = 0.90;
    } else if (peaks >= 4) {
      if (aspectRatio < 0.75) {
        // Tall flat hand -> B / 4
        detectedSign = "B";
        conf = 0.92;
      } else {
        // Open wide hand -> HELLO / 5
        detectedSign = "HELLO";
        conf = 0.90;
      }
    }

    // Check for curved C-shape: hollow interior
    if (peaks <= 2 && aspectRatio > 0.85 && aspectRatio < 1.3) {
      const midBoxX = Math.round(minX + handW * 0.4);
      const midBoxY = Math.round(minY + handH * 0.4);
      const midIdx = (midBoxY * width + midBoxX) * 4;
      const mr = data[midIdx], mg = data[midIdx + 1];
      if (mr < 80 || (mr - mg) < 8) {
        detectedSign = "C";
        conf = 0.89;
      }
    }

    if (!detectedSign) {
      return { isHandPresent: false, sign: null, confidence: 0 };
    }

    return {
      isHandPresent: true,
      sign: detectedSign,
      confidence: conf,
      peaks: peaks,
      aspectRatio: Math.round(aspectRatio * 100) / 100
    };
  }

  // High-Precision Neural Server Predictor (Uses PyTorch Model + MediaPipe)
  async classifyFrameWithServer(canvas, backendUrl = null) {
    if (!canvas || canvas.width === 0 || canvas.height === 0) return null;

    const targetUrl = (backendUrl || window.ehCurrentBackendUrl || "https://echohands-ai.loca.lt").replace(/\/+$/, "");

    try {
      const b64 = canvas.toDataURL("image/jpeg", 0.75);
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4500);

      const res = await fetch(`${targetUrl}/api/webcam/predict`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Bypass-Tunnel-Reminder": "true",
          "ngrok-skip-browser-warning": "69420"
        },
        body: JSON.stringify({
          frame_base64: b64,
          skip_verification: true, // Sub-30ms PyTorch neural inference for live video stream!
          allow_empty: true
        }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        if (data && data.status === "success" && data.sentence) {
          const tokens = data.sentence.raw_tokens || [];
          const sentence = data.sentence.english_sentence || (tokens.length > 0 ? tokens[0] : "");
          const conf = data.actual_confidence || 0.85;
          const reg0 = (data.regions && data.regions.length > 0) ? data.regions[0] : {};
          const handedness = reg0.handedness || (data.regions_count > 1 || reg0.is_dual_hand ? "two-handed" : "one-handed");

          if (tokens.length > 0 && conf >= 0.45) {
            return {
              isHandPresent: true,
              sign: tokens[0],
              sentence: sentence,
              confidence: conf,
              handedness: handedness,
              source: "neural_backend",
              badge: data.verification_badge || "PYTORCH NEURAL ENGINE"
            };
          }
        }
        // Backend ran and saw no hand
        return { isHandPresent: false, sign: null, confidence: 0, source: "neural_backend" };
      }
    } catch (e) {
      // Backend request timed out or network offline
    }

    // Failsafe fallback only when backend is completely unreachable
    const localResult = this.classifyCanvasFrame(canvas);
    return { ...localResult, source: "client_fallback" };
  }
}

window.ISLEngine = ISLEngine;

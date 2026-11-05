/**
 * Echo-Hands // Video Call Sign Language Overlay Controller
 * Bidirectional Real-Time Communication:
 * 1. Deaf Person (ISL Signs / Camera / Typing / Buttons) -> Normal Person hears real human voice + chime.
 * 2. Normal Person (Speaks into Mic / Typing / Buttons) -> Deaf Person sees live 3D articulated ISL avatar.
 * Works seamlessly on Google Meet, Zoom, WhatsApp Web, Teams.
 */

(function () {
  console.log("%c[Echo-Hands] Overlay script loaded on: " + window.location.href, "color: #00e6b4; font-weight: bold;");

  let meetingDetected = false;
  let userChoice = null; // 'sleep', 'deaf_mute', 'normal'
  let promptCard = null;
  let transparentOverlay = null;
  let normalBar = null;

  let avatarInstance = null;
  let islEngine = null;
  let peerSync = null;
  let cameraStream = null;
  let captureIntervalId = null;

  // Aggressive key event trap to prevent Google Meet from intercepting typing
  function stopMeetKeyCapture(el) {
    if (!el) return;
    const events = ["keydown", "keyup", "keypress"];
    events.forEach((eventType) => {
      el.addEventListener(eventType, (e) => {
        e.stopPropagation();
        e.stopImmediatePropagation();
      }, true); // TRUE = capture phase, runs BEFORE Google Meet's window hotkey listeners!
    });
  }

  // Initialize background engines & multi-layer peer sync
  function initEngines() {
    if (!islEngine && window.ISLEngine) {
      islEngine = new ISLEngine();
    }

    if (!peerSync && window.PeerSyncManager) {
      peerSync = new PeerSyncManager();

      // 1. Normal person receives sign -> Speaks real voice aloud + chime!
      peerSync.onPeerSignReceived = (data) => {
        console.log("%c[Echo-Hands] Normal person received sign event:", "color: #00e6b4;", data);
        const sentence = data.english_sentence || (data.tokens ? data.tokens.join(" ") : "");

        const statusEl = document.getElementById("eh-normal-status-txt");
        if (statusEl) {
          statusEl.textContent = `🔊 Heard: "${sentence}"`;
          statusEl.style.borderColor = "#00ffcc";
          statusEl.style.color = "#00ffcc";
          setTimeout(() => {
            if (statusEl) {
              statusEl.style.borderColor = "rgba(0, 230, 180, 0.2)";
              statusEl.style.color = "#94a3b8";
            }
          }, 3500);
        }

        if (islEngine && sentence) {
          islEngine.speakSentence(sentence, "en-IN");
        }
      };

      // 2. Deaf person receives voice -> 3D Avatar animates live!
      peerSync.onPeerVoiceReceived = (data) => {
        console.log("%c[Echo-Hands] Deaf person received voice event:", "color: #00e6b4;", data);

        const subEl = document.getElementById("eh-deaf-sub-txt");
        const badgeEl = document.getElementById("eh-current-badge");

        if (subEl) {
          subEl.textContent = `Hearing partner: "${data.text}"`;
          subEl.style.color = "#00ffcc";
          setTimeout(() => {
            if (subEl) subEl.style.color = "#94a3b8";
          }, 3500);
        }

        if (avatarInstance && data.isl_tokens && data.isl_tokens.length > 0) {
          avatarInstance.playSequence(
            data.isl_tokens,
            (activeToken) => {
              if (badgeEl) {
                badgeEl.textContent = `AVATAR SIGNING: ${activeToken}`;
                badgeEl.style.borderColor = "#00ffcc";
              }
            },
            () => {
              if (badgeEl) {
                badgeEl.textContent = `AVATAR: READY`;
                badgeEl.style.borderColor = "#00e6b4";
              }
            }
          );
        }
      };
    }
  }

  // Pre-initialize engines so listeners are armed immediately
  initEngines();

  function appendToRoot(el) {
    const target = document.documentElement || document.body;
    if (target) {
      target.appendChild(el);
    }
  }

  // Step 1: Detect Meeting & Ask to Enable
  function promptEnable() {
    if (promptCard || userChoice || document.getElementById("echohands-prompt-container")) return;

    promptCard = document.createElement("div");
    promptCard.id = "echohands-prompt-container";
    promptCard.innerHTML = `
      <div class="eh-prompt-box">
        <div class="eh-prompt-title">
          <span class="eh-dot"></span>
          <span>Enable Echo-Hands for this meeting?</span>
        </div>
        <div class="eh-prompt-btns">
          <button class="eh-btn-main" id="eh-btn-enable">Enable Echo-Hands</button>
          <button class="eh-btn-sub" id="eh-btn-sleep">No / Sleep</button>
        </div>
      </div>
    `;

    appendToRoot(promptCard);

    document.getElementById("eh-btn-sleep").onclick = () => {
      userChoice = "sleep";
      promptCard.remove();
      promptCard = null;
      console.log("[Echo-Hands] Slept for this call.");
    };

    document.getElementById("eh-btn-enable").onclick = () => {
      promptDisabilityRole();
    };
  }

  // Step 2: Ask if physically disabled (deaf and mute)
  function promptDisabilityRole() {
    if (!promptCard) return;

    promptCard.innerHTML = `
      <div class="eh-prompt-box">
        <div class="eh-prompt-title">
          <span class="eh-dot"></span>
          <span>Are you physically disabled (Deaf and Mute)?</span>
        </div>
        <div class="eh-prompt-btns">
          <button class="eh-btn-main" id="eh-btn-yes-deaf">Yes</button>
          <button class="eh-btn-sub" id="eh-btn-no-normal">No</button>
        </div>
      </div>
    `;

    // Branch A: Deaf and Mute -> Spawn simple transparent overlay with 3D Avatar
    document.getElementById("eh-btn-yes-deaf").onclick = () => {
      userChoice = "deaf_mute";
      promptCard.remove();
      promptCard = null;
      initEngines();
      spawnTransparentSignOverlay();
    };

    // Branch B: Normal Person -> Floating Voice Relay Bar
    document.getElementById("eh-btn-no-normal").onclick = () => {
      userChoice = "normal";
      promptCard.remove();
      promptCard = null;
      initEngines();
      spawnNormalPersonRelay();
    };
  }

  // 1. Deaf Person: Transparent Overlay with 3D Avatar, Sign Actions & Keyboard Input
  function spawnTransparentSignOverlay() {
    if (transparentOverlay || document.getElementById("echohands-sign-overlay")) return;

    transparentOverlay = document.createElement("div");
    transparentOverlay.id = "echohands-sign-overlay";
    transparentOverlay.innerHTML = `
      <div class="eh-overlay-header" id="eh-overlay-drag">
        <span class="eh-overlay-label">🤟 Echo-Hands // ISL Overlay</span>
        <button class="eh-overlay-close" id="eh-close-overlay">✕</button>
      </div>
      <div class="eh-avatar-viewport" id="eh-avatar-canvas-wrap">
        <div class="eh-overlay-badge" id="eh-current-badge">AVATAR: READY</div>
        <!-- PIP Webcam Video Preview -->
        <div class="eh-cam-pip" id="eh-cam-pip-container" title="Camera Gesture Tracker">
          <video id="eh-pip-video" autoplay playsinline muted></video>
          <div class="eh-pip-status" id="eh-pip-status-txt">AI VISION: ON</div>
        </div>
      </div>
      <!-- Quick Sign Action Buttons for Deaf User -->
      <div class="eh-quick-sign-bar">
        <button class="eh-sign-pill-btn" data-sign="NAMASTE">NAMASTE</button>
        <button class="eh-sign-pill-btn" data-sign="HELP">HELP</button>
        <button class="eh-sign-pill-btn" data-sign="WATER">WATER</button>
        <button class="eh-sign-pill-btn" data-sign="FOOD">FOOD</button>
        <button class="eh-sign-pill-btn" data-sign="YES">YES</button>
        <button class="eh-sign-pill-btn" data-sign="NO">NO</button>
        <button class="eh-sign-pill-btn" data-sign="A">A</button>
        <button class="eh-sign-pill-btn" data-sign="B">B</button>
        <button class="eh-sign-pill-btn" data-sign="C">C</button>
        <button class="eh-sign-pill-btn" data-sign="D">D</button>
        <button class="eh-sign-pill-btn" data-sign="V">V</button>
        <button class="eh-sign-pill-btn" id="eh-toggle-alphabet">A-Z ▾</button>
      </div>
      <!-- Expandable A-Z Keyboard Strip -->
      <div class="eh-alphabet-tray" id="eh-alphabet-tray" style="display:none;">
        ${"ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").map(c => `<button class="eh-alpha-btn" data-sign="${c}">${c}</button>`).join("")}
      </div>
      <!-- Text Typing Bar for Deaf Person (No key interception by Google Meet) -->
      <div class="eh-deaf-input-wrap">
        <input type="text" id="eh-deaf-input" class="eh-hud-input" placeholder="Type letters/words (e.g. A, B, HELP)...">
        <button id="eh-deaf-send" class="eh-hud-send-btn">Sign / Speak</button>
      </div>
      <!-- Subtitles of what the normal hearing person says -->
      <div class="eh-deaf-subtitles" id="eh-deaf-sub-txt">
        Awaiting voice from hearing partner...
      </div>
      <canvas id="eh-offscreen-canvas" width="480" height="360" style="display:none;"></canvas>
    `;

    appendToRoot(transparentOverlay);

    // Initialize Three.js 3D Avatar
    const mount = document.getElementById("eh-avatar-canvas-wrap");
    if (window.THREE && window.ISL3DAvatar && mount) {
      avatarInstance = new ISL3DAvatar(mount);
    }

    makeOverlayDraggable();

    // Prevent Google Meet from intercepting keys typed into Deaf input
    const deafInput = document.getElementById("eh-deaf-input");
    const deafSendBtn = document.getElementById("eh-deaf-send");
    stopMeetKeyCapture(deafInput);

    const doDeafSend = () => {
      const val = (deafInput.value || "").trim();
      if (val) {
        sendDeafSign(val.toUpperCase());
        deafInput.value = "";
      }
    };
    if (deafSendBtn) deafSendBtn.onclick = doDeafSend;
    if (deafInput) {
      deafInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          doDeafSend();
        }
      });
    }

    document.getElementById("eh-close-overlay").onclick = () => {
      transparentOverlay.style.display = "none";
      if (captureIntervalId) {
        clearInterval(captureIntervalId);
        captureIntervalId = null;
      }
    };

    // Toggle alphabet tray
    const toggleAlphaBtn = document.getElementById("eh-toggle-alphabet");
    const alphaTray = document.getElementById("eh-alphabet-tray");
    if (toggleAlphaBtn && alphaTray) {
      toggleAlphaBtn.onclick = () => {
        alphaTray.style.display = alphaTray.style.display === "none" ? "flex" : "none";
        toggleAlphaBtn.textContent = alphaTray.style.display === "none" ? "A-Z ▾" : "A-Z ▴";
      };
    }

    // Attach click events to quick sign buttons
    const signBtns = transparentOverlay.querySelectorAll(".eh-sign-pill-btn, .eh-alpha-btn");
    signBtns.forEach((btn) => {
      btn.onclick = () => {
        const sign = btn.getAttribute("data-sign");
        if (sign) sendDeafSign(sign);
      };
    });

    // Start Webcam Capture & Computer Vision Detection Loop
    startDeafSignCapturing();
  }

  // Deaf Person transmits a sign to the normal person
  function sendDeafSign(sign, customSentence = null) {
    if (!sign) return;
    const res = customSentence ? { english: customSentence, hindi: customSentence } : islEngine.synthesizeISLTokens([sign]);
    const badgeEl = document.getElementById("eh-current-badge");
    if (badgeEl) {
      badgeEl.textContent = `🤟 SIGNED: ${sign}`;
      badgeEl.style.borderColor = "#00ffcc";
      setTimeout(() => {
        if (badgeEl) {
          badgeEl.textContent = "AVATAR: READY";
          badgeEl.style.borderColor = "#00e6b4";
        }
      }, 1500);
    }

    // Instantly animate the 3D avatar on the deaf user's viewport too!
    if (avatarInstance) {
      avatarInstance.playSequence([sign]);
    }

    console.log("[Echo-Hands] Deaf person signed:", sign, "-> Spoken sentence:", res.english);

    // Broadcast across tabs/devices to normal person
    peerSync.broadcastSign({
      tokens: [sign],
      english_sentence: res.english,
      hindi_sentence: res.hindi
    });
  }

  // 2. Normal Person: Floating Voice Relay Bar with Keyboard Interception Trap
  function spawnNormalPersonRelay() {
    if (normalBar || document.getElementById("echohands-normal-bar")) return;

    normalBar = document.createElement("div");
    normalBar.id = "echohands-normal-bar";
    normalBar.innerHTML = `
      <div class="eh-normal-row1">
        <span style="display:flex; align-items:center; gap:6px;">
          <span class="eh-mic-indicator" id="eh-mic-led"></span>
          <span>🎙️ Echo-Hands Voice Relay</span>
        </span>
        <div style="display:flex; gap:6px;">
          <button id="eh-normal-test-voice" class="eh-test-voice-btn" title="Click to test audio playback">🔊 Sound Ready</button>
          <button id="eh-normal-close" style="background:none; border:none; color:#94a3b8; cursor:pointer;">✕</button>
        </div>
      </div>
      <div class="eh-normal-status" id="eh-normal-status-txt">
        Awaiting signs from deaf partner...
      </div>
      <!-- Quick Speech Test Buttons -->
      <div class="eh-normal-quick-btns">
        <button class="eh-voice-pill-btn" data-text="A">Say: "A"</button>
        <button class="eh-voice-pill-btn" data-text="B">Say: "B"</button>
        <button class="eh-voice-pill-btn" data-text="C">Say: "C"</button>
        <button class="eh-voice-pill-btn" data-text="Hello">Say: "Hello"</button>
        <button class="eh-voice-pill-btn" data-text="Namaste">Say: "Namaste"</button>
        <button class="eh-voice-pill-btn" data-text="Do you need help?">Say: "Help?"</button>
      </div>
      <div class="eh-normal-input-wrap">
        <input type="text" id="eh-normal-input" class="eh-normal-input" placeholder="Type text to sign & press Enter...">
        <button id="eh-normal-send" class="eh-normal-send-btn">Send</button>
      </div>
    `;

    appendToRoot(normalBar);

    document.getElementById("eh-normal-close").onclick = () => {
      normalBar.style.display = "none";
    };

    // Voice playback test button (unlocks browser audio policy on Mac & Windows)
    const testVoiceBtn = document.getElementById("eh-normal-test-voice");
    if (testVoiceBtn) {
      testVoiceBtn.onclick = () => {
        if (islEngine) {
          islEngine.speakSentence("Echo-Hands audio system active and ready!", "en-IN");
          const statusEl = document.getElementById("eh-normal-status-txt");
          if (statusEl) statusEl.textContent = "🔊 Audio playback verified!";
        }
      };
    }

    // Quick speech buttons
    const voiceBtns = normalBar.querySelectorAll(".eh-voice-pill-btn");
    voiceBtns.forEach((btn) => {
      btn.onclick = () => {
        const text = btn.getAttribute("data-text");
        sendNormalSpeech(text);
      };
    });

    // Prevent Google Meet from intercepting keys typed into Normal input
    const sendBtn = document.getElementById("eh-normal-send");
    const inputEl = document.getElementById("eh-normal-input");
    stopMeetKeyCapture(inputEl);

    const doSend = () => {
      const val = (inputEl.value || "").trim();
      if (val) {
        sendNormalSpeech(val);
        inputEl.value = "";
      }
    };
    sendBtn.onclick = doSend;
    inputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        doSend();
      }
    });

    // Continuous Speech Recognition with Live Indicator
    if (islEngine) {
      const micLed = document.getElementById("eh-mic-led");
      islEngine.onSpeechStatus = (status) => {
        if (micLed) {
          if (status === "listening") {
            micLed.className = "eh-mic-indicator eh-mic-active";
            micLed.title = "Microphone listening";
          } else if (status === "error") {
            micLed.className = "eh-mic-indicator eh-mic-err";
            micLed.title = "Microphone permission needed";
          } else {
            micLed.className = "eh-mic-indicator";
          }
        }
      };

      islEngine.onVoiceTranscript = (spokenText) => {
        console.log("[Echo-Hands] Spoken speech detected:", spokenText);
        sendNormalSpeech(spokenText);
      };
      islEngine.startListening("en-IN");
    }
  }

  // Normal Person transmits voice to the deaf person's avatar
  function sendNormalSpeech(text) {
    if (!text) return;

    // 1. Instant client-side compiler (0ms latency!)
    const tokens = islEngine ? islEngine.compileTextToISL(text) : [text.toUpperCase()];

    console.log("[Echo-Hands] Spoken:", text, "-> Tokens:", tokens);

    const statusEl = document.getElementById("eh-normal-status-txt");
    if (statusEl) {
      statusEl.textContent = `🎙️ Sent: "${text}"`;
      statusEl.style.borderColor = "#00e6b4";
      setTimeout(() => {
        if (statusEl) statusEl.style.borderColor = "rgba(0, 230, 180, 0.2)";
      }, 1500);
    }

    // 2. Broadcast immediately across tabs & internet (Zero delay!)
    if (peerSync) {
      peerSync.broadcastVoice({
        text: text,
        isl_tokens: tokens,
        language: "en-IN"
      });
    }

    // 3. Asynchronous background sync to Python engine (non-blocking)
    if (peerSync && peerSync.backendUrl) {
      fetch(`${peerSync.backendUrl}/api/text-to-isl`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Bypass-Tunnel-Reminder": "true",
          "ngrok-skip-browser-warning": "69420"
        },
        body: JSON.stringify({ text: text })
      }).catch(() => {});
    }
  }

  // Deaf Person gesture capture & computer-vision recognition loop
  async function startDeafSignCapturing() {
    const video = document.getElementById("eh-pip-video");
    const offCanvas = document.getElementById("eh-offscreen-canvas");
    const pipStatus = document.getElementById("eh-pip-status-txt");
    if (!video || !offCanvas) return;

    try {
      if (!cameraStream) {
        cameraStream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480, facingMode: "user" }
        });
      }
      video.srcObject = cameraStream;
    } catch (e) {
      // Fallback: look for Google Meet's active video stream
      const allVideos = Array.from(document.querySelectorAll("video"));
      const meetVid = allVideos.find(v => v !== video && v.srcObject);
      if (meetVid && meetVid.srcObject) {
        video.srcObject = meetVid.srcObject;
      } else {
        if (pipStatus) pipStatus.textContent = "AI VISION: TAP SIGN";
      }
    }

    // Recognition loop variables
    let lastStableSign = null;
    let candidateSign = null;
    let candidateSentence = null;
    let consecutiveCount = 0;
    let lastSentTimestamp = 0;

    if (captureIntervalId) clearInterval(captureIntervalId);

    // Frame capture every 350ms -> directly to Python PyTorch backend!
    captureIntervalId = setInterval(async () => {
      if (!video || video.readyState < 2 || video.videoWidth === 0) return;

      const ctx = offCanvas.getContext("2d", { willReadFrequently: true });
      if (!ctx) return;

      // Draw high-resolution 480x360 frame
      ctx.drawImage(video, 0, 0, offCanvas.width, offCanvas.height);

      if (islEngine) {
        // Run PyTorch model + MediaPipe on Python backend!
        const bUrl = peerSync ? peerSync.backendUrl : null;
        const result = await islEngine.classifyFrameWithServer(offCanvas, bUrl);

        if (result && result.isHandPresent && result.sign) {
          if (pipStatus) {
            pipStatus.textContent = `AI: ${result.sign} (${Math.round(result.confidence * 100)}%)`;
            pipStatus.style.color = "#00ffcc";
          }

          // Gesture stabilization logic (2 consecutive frames with 1.2s debounce)
          if (result.sign === candidateSign) {
            consecutiveCount++;
          } else {
            candidateSign = result.sign;
            candidateSentence = result.sentence || null;
            consecutiveCount = 1;
          }

          const now = Date.now();
          if (consecutiveCount >= 2 && now - lastSentTimestamp > 1200) {
            lastSentTimestamp = now;
            lastStableSign = candidateSign;
            sendDeafSign(candidateSign, candidateSentence);
          }
        } else {
          if (pipStatus) {
            pipStatus.textContent = "AI VISION: READY";
            pipStatus.style.color = "#00e6b4";
          }
          candidateSign = null;
          consecutiveCount = 0;
        }
      }
    }, 350);
  }

  // Drag function for transparent overlay
  function makeOverlayDraggable() {
    const handle = document.getElementById("eh-overlay-drag");
    if (!handle || !transparentOverlay) return;

    let isDrag = false;
    let startX = 0, startY = 0;
    let initLeft = 0, initTop = 0;

    handle.onmousedown = (e) => {
      if (e.target.tagName === "BUTTON") return;
      isDrag = true;
      startX = e.clientX;
      startY = e.clientY;
      const rect = transparentOverlay.getBoundingClientRect();
      initLeft = rect.left;
      initTop = rect.top;
      transparentOverlay.style.right = "auto";
      transparentOverlay.style.bottom = "auto";
      transparentOverlay.style.left = `${initLeft}px`;
      transparentOverlay.style.top = `${initTop}px`;
    };

    window.onmousemove = (e) => {
      if (!isDrag) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      transparentOverlay.style.left = `${initLeft + dx}px`;
      transparentOverlay.style.top = `${initTop + dy}px`;
    };

    window.onmouseup = () => {
      isDrag = false;
    };
  }

  // Meeting Detection across Google Meet, Zoom, WhatsApp Web, Teams
  function checkCallActive() {
    const callDomains = [
      "meet.google.com",
      "zoom.us",
      "teams.microsoft.com",
      "teams.live.com",
      "web.whatsapp.com",
      "whatsapp.com",
      "meet.jit.si"
    ];

    const isDomain = callDomains.some(d => window.location.href.includes(d));
    const hasVideo = document.querySelector("video") !== null;

    if (isDomain || hasVideo) {
      if (!meetingDetected) {
        meetingDetected = true;
        console.log("[Echo-Hands] Active meeting detected on: " + window.location.href);
      }
      if (!userChoice && !document.getElementById("echohands-prompt-container")) {
        promptEnable();
      }
    }
  }

  checkCallActive();
  setInterval(checkCallActive, 1000);
})();

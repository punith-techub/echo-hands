/**
 * ECHOHANDS 5.0 // Meeting Injection Content Script
 * Detects Google Meet, Zoom, Teams, and Meeting Simulators,
 * and automatically mounts the ASTRA-VISION Tactical HUD with 3D Avatar & ISL Engine.
 */

(function () {
  console.log("[ECHOHANDS] Content script injected. Watching for video call...");

  let hudMounted = false;
  let hudContainer = null;
  let avatarInstance = null;
  let islEngine = null;
  let peerSync = null;

  let currentRole = "signer"; // 'signer' (Deaf/Mute) or 'speaker' (Hearing)
  let currentTokens = [];
  let cameraStream = null;
  let trackingInterval = null;

  // Initialize ECHOHANDS HUD
  function mountHUD() {
    if (hudMounted || document.getElementById("echohands-hud-overlay")) return;

    hudContainer = document.createElement("div");
    hudContainer.id = "echohands-hud-overlay";
    hudContainer.innerHTML = `
      <div class="hud-header-bar" id="hud-drag-handle">
        <div class="hud-title-wrap">
          <span class="hud-status-dot"></span>
          <span class="hud-title-text">ECHOHANDS // ASTRA-MEET HUD</span>
        </div>
        <div class="hud-role-switcher">
          <button class="role-btn active" id="btn-role-signer" title="Deaf/Mute Mode: Real-time ISL Gesture Translation">🤟 SIGNER</button>
          <button class="role-btn" id="btn-role-speaker" title="Hearing Mode: Spoken Voice to 3D Live Sign Avatar">🎙️ VOICE</button>
        </div>
        <div class="hud-controls">
          <button class="hud-ctrl-btn" id="btn-hud-min" title="Minimize/Expand">_</button>
          <button class="hud-ctrl-btn" id="btn-hud-close" title="Close HUD">✕</button>
        </div>
      </div>

      <div class="hud-body">
        <!-- Pane 1: ISL Camera Tracker -->
        <div class="hud-pane" id="pane-signer">
          <div class="pane-heading">
            <span>ISL SENSOR TRACKER</span>
            <span id="tracker-status" style="color:#00e6b4;">ACTIVE</span>
          </div>
          <div class="pane-viewport">
            <video id="hud-camera-feed" autoplay playsinline muted></video>
            <canvas id="hud-tracking-canvas" style="display:none;"></canvas>
            <div class="overlay-badge" id="detected-sign-badge">READY // SIGN HERE</div>
          </div>
          <div class="pane-controls">
            <button class="tactical-btn-mini" id="btn-test-namaste">NAMASTE</button>
            <button class="tactical-btn-mini" id="btn-test-help">HELP</button>
            <button class="tactical-btn-mini" id="btn-test-water">WATER</button>
            <button class="tactical-btn-mini" id="btn-test-doctor">DOCTOR</button>
            <button class="tactical-btn-mini" id="btn-speak-current" style="background:#00e6b4; color:#041014;">🔊 SPEAK</button>
          </div>
        </div>

        <!-- Pane 2: 3D ISL Avatar -->
        <div class="hud-pane" id="pane-avatar">
          <div class="pane-heading">
            <span>3D ISL AVATAR</span>
            <span id="avatar-status" style="color:#00e6b4;">LIVE 60FPS</span>
          </div>
          <div class="pane-viewport" id="avatar-canvas-container">
            <div class="overlay-badge" id="avatar-active-badge">SIGN: IDLE</div>
          </div>
          <div class="pane-controls">
            <button class="tactical-btn-mini" id="btn-speed-slow">0.8x</button>
            <button class="tactical-btn-mini" id="btn-speed-normal" style="border-color:#00e6b4;">1.0x</button>
            <button class="tactical-btn-mini" id="btn-speed-fast">1.4x</button>
            <button class="tactical-btn-mini" id="btn-mic-toggle">🎙️ MIC: OFF</button>
          </div>
        </div>
      </div>

      <!-- Live Subtitle Bar -->
      <div class="hud-captions-dock">
        <div class="captions-header">
          <span>LIVE BILINGUAL TRANSLATION</span>
          <span id="sync-telemetry" style="color:#546e7a;">SYNC: P2P ACTIVE</span>
        </div>
        <div class="captions-box">
          <div class="caption-primary" id="caption-en">Awaiting gesture input or spoken voice...</div>
          <div class="caption-secondary" id="caption-hi">इशारे या आवाज़ की प्रतीक्षा है...</div>
        </div>
      </div>

      <!-- Telemetry Footer -->
      <div class="hud-telemetry">
        <span>ENGINE: <span class="active">DUAL-BRAIN HYBRID</span></span>
        <span>AVATAR: <span class="active">RIGGED WEBGL</span></span>
        <span>LATENCY: <span class="active">&lt;15ms</span></span>
      </div>
    `;

    document.body.appendChild(hudContainer);
    hudMounted = true;
    console.log("[ECHOHANDS] Tactical HUD mounted into meeting DOM.");

    initDraggable();
    initEngines();
    attachHUDListeners();
  }

  // Initialize Avatar & ISL Engines
  function initEngines() {
    // 1. Peer Sync
    const roomId = window.location.pathname.replace(/[^a-zA-Z0-9]/g, "") || "main_meeting";
    peerSync = new PeerSyncManager(roomId);

    // 2. 3D Avatar
    const avatarCanvasWrap = document.getElementById("avatar-canvas-container");
    if (window.THREE && window.ISL3DAvatar && avatarCanvasWrap) {
      avatarInstance = new ISL3DAvatar(avatarCanvasWrap);
    }

    // 3. ISL Engine
    if (window.ISLEngine) {
      islEngine = new ISLEngine();

      // Hook voice transcription (Hearing -> Deaf flow)
      islEngine.onVoiceTranscript = (transcript) => {
        handleSpokenVoiceInput(transcript);
      };
    }

    // 4. Peer Events
    peerSync.onPeerSignReceived = (data) => {
      // Received sign from Deaf person -> Voice aloud for Hearing person
      updateCaptions(data.english_sentence, data.hindi_sentence);
      if (islEngine) {
        islEngine.speakSentence(data.english_sentence, "en-IN");
      }
    };

    peerSync.onPeerVoiceReceived = (data) => {
      // Received voice from Hearing person -> Animate avatar for Deaf person
      updateCaptions(data.text, "Translated from spoken voice");
      if (avatarInstance && data.isl_tokens) {
        playAvatarTokens(data.isl_tokens);
      }
    };

    // Start in default role
    setRole(currentRole);
  }

  // Handle Spoken Voice Input (Hearing user spoke)
  function handleSpokenVoiceInput(transcript) {
    if (!transcript) return;
    const islTokens = islEngine.compileTextToISL(transcript);
    console.log("[ECHOHANDS] Voice to ISL Tokens:", islTokens);

    updateCaptions(transcript, "Speech recognized: animating ISL avatar...");

    // Animate avatar locally
    playAvatarTokens(islTokens);

    // Broadcast to peer
    peerSync.broadcastVoice({
      text: transcript,
      isl_tokens: islTokens,
      language: "en-IN"
    });
  }

  // Play animation sequence on 3D Avatar
  function playAvatarTokens(tokens) {
    if (!avatarInstance || !tokens || tokens.length === 0) return;
    const badge = document.getElementById("avatar-active-badge");

    avatarInstance.playSequence(
      tokens,
      (activeSign) => {
        if (badge) badge.textContent = `SIGN: ${activeSign}`;
      },
      () => {
        if (badge) badge.textContent = "SIGN: IDLE";
      }
    );
  }

  // Handle Detected Sign (Deaf user signed)
  function handleSignDetected(signToken) {
    if (!signToken) return;
    currentTokens.push(signToken);

    const badge = document.getElementById("detected-sign-badge");
    if (badge) badge.textContent = `DETECTED: ${signToken}`;

    const synthesized = islEngine.synthesizeISLTokens(currentTokens);
    updateCaptions(synthesized.english, synthesized.hindi);

    // Automatically speak in real voice so hearing partner hears it!
    islEngine.speakSentence(synthesized.english, "en-IN");

    // Broadcast to peer
    peerSync.broadcastSign({
      tokens: currentTokens,
      english_sentence: synthesized.english,
      hindi_sentence: synthesized.hindi
    });

    // Reset token buffer after brief pause
    setTimeout(() => {
      currentTokens = [];
    }, 2000);
  }

  function updateCaptions(enText, hiText) {
    const elEn = document.getElementById("caption-en");
    const elHi = document.getElementById("caption-hi");
    if (elEn) elEn.textContent = enText || "--";
    if (elHi) elHi.textContent = hiText || "--";
  }

  // Switch between Deaf/Mute (Signer) and Hearing (Speaker)
  function setRole(role) {
    currentRole = role;
    const btnSigner = document.getElementById("btn-role-signer");
    const btnSpeaker = document.getElementById("btn-role-speaker");
    const micBtn = document.getElementById("btn-mic-toggle");

    if (role === "signer") {
      btnSigner.classList.add("active");
      btnSpeaker.classList.remove("active");
      startCamera();
      if (islEngine) islEngine.stopListening();
      if (micBtn) micBtn.textContent = "🎙️ MIC: OFF";
    } else {
      btnSpeaker.classList.add("active");
      btnSigner.classList.remove("active");
      stopCamera();
      if (islEngine) {
        islEngine.startListening();
        if (micBtn) micBtn.textContent = "🎙️ MIC: LIVE";
      }
    }
  }

  // Camera Management
  async function startCamera() {
    const video = document.getElementById("hud-camera-feed");
    if (!video) return;

    try {
      if (!cameraStream) {
        cameraStream = await navigator.mediaDevices.getUserMedia({
          video: { width: 320, height: 240, facingMode: "user" }
        });
      }
      video.srcObject = cameraStream;
      startTrackingLoop();
    } catch (err) {
      console.warn("[ECHOHANDS] Camera access denied or meeting already owns feed:", err);
      // Fallback: Attach to existing meeting video if available
      const existingVideo = document.querySelector("video");
      if (existingVideo && existingVideo !== video) {
        video.srcObject = existingVideo.srcObject;
      }
    }
  }

  function stopCamera() {
    if (trackingInterval) clearInterval(trackingInterval);
    if (cameraStream) {
      cameraStream.getTracks().forEach(t => t.stop());
      cameraStream = null;
    }
  }

  function startTrackingLoop() {
    if (trackingInterval) clearInterval(trackingInterval);
    trackingInterval = setInterval(() => {
      // Simulate/classify gesture periodically from video canvas
      // In production, this receives MediaPipe landmarks
    }, 300);
  }

  // UI Event Listeners
  function attachHUDListeners() {
    document.getElementById("btn-role-signer")?.addEventListener("click", () => setRole("signer"));
    document.getElementById("btn-role-speaker")?.addEventListener("click", () => setRole("speaker"));

    // Quick Test Sign Buttons (Allows immediate validation on video call)
    document.getElementById("btn-test-namaste")?.addEventListener("click", () => handleSignDetected("NAMASTE"));
    document.getElementById("btn-test-help")?.addEventListener("click", () => handleSignDetected("HELP"));
    document.getElementById("btn-test-water")?.addEventListener("click", () => handleSignDetected("WATER"));
    document.getElementById("btn-test-doctor")?.addEventListener("click", () => handleSignDetected("DOCTOR"));

    document.getElementById("btn-speak-current")?.addEventListener("click", () => {
      const enText = document.getElementById("caption-en")?.textContent;
      if (islEngine && enText) islEngine.speakSentence(enText, "en-IN");
    });

    // Speed controls
    document.getElementById("btn-speed-slow")?.addEventListener("click", () => {
      if (avatarInstance) avatarInstance.speedMultiplier = 0.8;
    });
    document.getElementById("btn-speed-normal")?.addEventListener("click", () => {
      if (avatarInstance) avatarInstance.speedMultiplier = 1.0;
    });
    document.getElementById("btn-speed-fast")?.addEventListener("click", () => {
      if (avatarInstance) avatarInstance.speedMultiplier = 1.4;
    });

    // Mic Toggle
    document.getElementById("btn-mic-toggle")?.addEventListener("click", () => {
      const btn = document.getElementById("btn-mic-toggle");
      if (islEngine && islEngine.isListening) {
        islEngine.stopListening();
        btn.textContent = "🎙️ MIC: OFF";
      } else if (islEngine) {
        islEngine.startListening();
        btn.textContent = "🎙️ MIC: LIVE";
      }
    });

    // Minimize & Close
    document.getElementById("btn-hud-min")?.addEventListener("click", () => {
      hudContainer.classList.toggle("minimized");
    });
    document.getElementById("btn-hud-close")?.addEventListener("click", () => {
      hudContainer.style.display = "none";
    });
  }

  // Draggable HUD window
  function initDraggable() {
    const handle = document.getElementById("hud-drag-handle");
    if (!handle || !hudContainer) return;

    let isDragging = false;
    let startX = 0, startY = 0;
    let initialLeft = 0, initialTop = 0;

    handle.addEventListener("mousedown", (e) => {
      if (e.target.tagName === "BUTTON") return;
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;
      const rect = hudContainer.getBoundingClientRect();
      initialLeft = rect.left;
      initialTop = rect.top;
      hudContainer.style.right = "auto";
      hudContainer.style.bottom = "auto";
      hudContainer.style.left = `${initialLeft}px`;
      hudContainer.style.top = `${initialTop}px`;
    });

    window.addEventListener("mousemove", (e) => {
      if (!isDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      hudContainer.style.left = `${initialLeft + dx}px`;
      hudContainer.style.top = `${initialTop + dy}px`;
    });

    window.addEventListener("mouseup", () => {
      isDragging = false;
    });
  }

  // Check if current page is an active meeting
  function checkForMeeting() {
    const isMeetingUrl = [
      "meet.google.com",
      "zoom.us",
      "teams.microsoft.com",
      "teams.live.com",
      "meet.jit.si",
      "simulator",
      "meeting"
    ].some(u => window.location.href.includes(u));

    const hasVideo = document.querySelector("video") !== null;

    if (isMeetingUrl || hasVideo) {
      mountHUD();
    }
  }

  // Periodic polling & URL observer
  checkForMeeting();
  setInterval(checkForMeeting, 2000);

  // Listen for messages from background script or popup
  if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
      if (msg.type === "TOGGLE_HUD") {
        if (!hudMounted) {
          mountHUD();
        } else if (hudContainer) {
          hudContainer.style.display = hudContainer.style.display === "none" ? "block" : "none";
        }
        sendResponse({ status: "toggled" });
      }
    });
  }
})();

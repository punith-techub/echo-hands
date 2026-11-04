/**
 * ECHOHANDS 5.0 // ASTRA-VISION Tactical ISL Neural HUD Controller
 * Live Webcam Gesture Tracking, Real-Time Tactical Caption Overlay,
 * Multi-Key AI Verification Arbiter with Zero-Context-Loss Fallback,
 * Online Self-Learning Reward/Punishment Engine, and Offline Web Speech Synthesis.
 */

class WebGpuGlAccelerator {
  constructor() {
    this.backend = "CPU (Initializing)";
    this.gl = null;
    this.gpuDevice = null;
    this.init();
  }

  async init() {
    // 1. Try WebGPU Compute
    if (navigator.gpu) {
      try {
        const adapter = await navigator.gpu.requestAdapter();
        if (adapter) {
          this.gpuDevice = await adapter.requestDevice();
          this.backend = "WebGPU (Direct Compute)";
          this.updateBadge();
          return;
        }
      } catch (e) {
        console.warn("[WebGPU] Fallback to WebGL:", e);
      }
    }

    // 2. Fallback to WebGL 2.0 / WebGL 1.0
    try {
      const c = document.createElement("canvas");
      this.gl = c.getContext("webgl2") || c.getContext("webgl") || c.getContext("experimental-webgl");
      if (this.gl) {
        const ext = this.gl.getExtension("WEBGL_debug_renderer_info");
        const renderer = ext ? this.gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : "Hardware GPU";
        const shortName = renderer.split("/")[0].replace("ANGLE (", "").trim();
        this.backend = `WebGL 2.0 (${shortName.slice(0, 16)})`;
      } else {
        this.backend = "Hardware 2D Canvas";
      }
    } catch (e) {
      this.backend = "Hardware 2D Canvas";
    }
    this.updateBadge();
  }

  updateBadge() {
    const el = document.getElementById("gpu-telemetry");
    if (el) el.textContent = this.backend;
  }
}

class AstraVisionApp {
  constructor() {
    this.currentMode = "auto";
    this.currentResponse = null;
    this.currentImage = null;
    this.selectedRegionIdx = 0;
    this.isSpeaking = false;
    this.animationFrameId = null;
    this.currentView = "optical";

    // WebGPU / WebGL hardware accelerator
    this.gpu = new WebGpuGlAccelerator();

    // Webcam streaming state (High-speed 10-15 FPS inference, 60 FPS HUD)
    this.isWebcamStreaming = false;
    this.webcamStream = null;
    this.captureTimer = null;
    this.renderLoopId = null;
    this.isProcessingFrame = false;
    this.captureIntervalMs = 100;
    this.fpsCounter = 0;
    this.fpsLastTime = performance.now();
    this.currentFps = 0;
    this.sessionId = "webcam_session_" + Date.now();
    this.currentRegions = [];

    // Compact Off-screen canvas for frame capture (320x240 for 10x network speedup)
    this.offscreenCanvas = document.createElement("canvas");
    this.offscreenCanvas.width = 320;
    this.offscreenCanvas.height = 240;
    this.offscreenCtx = this.offscreenCanvas.getContext("2d");

    // Web Speech API
    this.synth = window.speechSynthesis;
    this.availableVoices = [];
    this.selectedVoice = null;

    this.initDOMElements();
    this.initEventListeners();
    this.initVoices();
    this.initWaveformVisualizer();
    this.startClock();
    this.checkHealth();
    this.pollVerifierStatus();

    // Periodic verifier polling (every 10s)
    setInterval(() => this.pollVerifierStatus(), 10000);
  }

  initDOMElements() {
    // Live Webcam Elements
    this.webcamVideo = document.getElementById("webcam-video");
    this.webcamHudCanvas = document.getElementById("webcam-hud-canvas");
    this.webcamHudCtx = this.webcamHudCanvas ? this.webcamHudCanvas.getContext("2d") : null;
    this.webcamPlaceholder = document.getElementById("webcam-placeholder");
    this.webcamLaser = document.getElementById("webcam-laser");
    this.camStatusDot = document.getElementById("cam-status-dot");
    this.camStatusText = document.getElementById("cam-status-text");
    this.camFpsText = document.getElementById("cam-fps-text");
    this.btnToggleWebcam = document.getElementById("btn-toggle-webcam");
    this.btnSnapFrame = document.getElementById("btn-snap-frame");
    this.cameraSelect = document.getElementById("camera-select");
    this.camIntervalSlider = document.getElementById("cam-interval-slider");
    this.valCamInterval = document.getElementById("val-cam-interval");

    // Verifier Telemetry
    this.vtStatus = document.getElementById("vt-status");
    this.vtActiveKey = document.getElementById("vt-active-key");
    this.vtFallbackChain = document.getElementById("vt-fallback-chain");
    this.btnResetSession = document.getElementById("btn-reset-session");
    this.telemetryVerifier = document.getElementById("telemetry-verifier");

    // Tactical Live Caption Box
    this.captionBox = document.getElementById("tactical-caption-box");
    this.captionConfBadge = document.getElementById("caption-conf-badge");
    this.captionVerifBadge = document.getElementById("caption-verif-badge");
    this.captionEnText = document.getElementById("caption-en-text");
    this.captionHiText = document.getElementById("caption-hi-text");
    this.captionTokenTrail = document.getElementById("caption-token-trail");
    this.captionFeedbackIndicator = document.getElementById("caption-feedback-indicator");

    // Quick Chips & Mode Switch
    this.quickChips = document.querySelectorAll(".chip-btn");
    this.modeBtns = document.querySelectorAll(".mode-btn");

    // Canvases & Views (Column 2)
    this.opticalCanvas = document.getElementById("optical-canvas");
    this.opticalCtx = this.opticalCanvas ? this.opticalCanvas.getContext("2d") : null;
    this.opticalPlaceholder = document.getElementById("optical-placeholder");
    this.gradcamImg = document.getElementById("gradcam-img");
    this.gradcamPlaceholder = document.getElementById("gradcam-placeholder");
    this.tabSegmentation = document.getElementById("tab-segmentation");
    this.tabGradcam = document.getElementById("tab-gradcam");
    this.paneOptical = document.getElementById("pane-optical");
    this.paneGradcam = document.getElementById("pane-gradcam");

    // Strip Inspector
    this.stripCarousel = document.getElementById("strip-carousel");
    this.stripCount = document.getElementById("strip-count");

    // Translations & Speech (Column 3)
    this.transEnglish = document.getElementById("trans-english");
    this.transHindi = document.getElementById("trans-hindi");
    this.transPhonetic = document.getElementById("trans-phonetic");
    this.voiceSelect = document.getElementById("voice-select");
    this.rateSlider = document.getElementById("rate-slider");
    this.pitchSlider = document.getElementById("pitch-slider");
    this.valRate = document.getElementById("val-rate");
    this.valPitch = document.getElementById("val-pitch");
    this.btnSpeak = document.getElementById("btn-speak");
    this.ttsAudioStatus = document.getElementById("tts-audio-status");
    this.waveformCanvas = document.getElementById("waveform-canvas");
    this.waveformCtx = this.waveformCanvas ? this.waveformCanvas.getContext("2d") : null;

    // Telemetry & Signatures
    this.telemetryLatency = document.getElementById("telemetry-latency");
    this.sigConf = document.getElementById("sig-conf");
    this.sigMargin = document.getElementById("sig-margin");
    this.sigHandedness = document.getElementById("sig-handedness");
    this.protoCount = document.getElementById("proto-count");
    this.deviceAccel = document.getElementById("device-accel");

    // Modals
    this.btnOpenMetrics = document.getElementById("btn-open-metrics");
    this.btnCloseMetrics = document.getElementById("btn-close-metrics");
    this.modalMetrics = document.getElementById("modal-metrics");
    this.btnOpenLearn = document.getElementById("btn-open-learn");
    this.btnCloseLearn = document.getElementById("btn-close-learn");
    this.modalLearn = document.getElementById("modal-learn");
    this.btnSubmitLearn = document.getElementById("btn-submit-learn");
    this.learnStatus = document.getElementById("learn-status");

    // Utility
    this.btnClearAll = document.getElementById("btn-clear-all");
    this.btnCopyEn = document.getElementById("btn-copy-en");
    this.btnCopyHi = document.getElementById("btn-copy-hi");
    this.footerTime = document.getElementById("footer-time");

    // Self-Learning Interactive Feedback
    this.btnThumbsUp = document.getElementById("btn-thumbs-up");
    this.btnThumbsDown = document.getElementById("btn-thumbs-down");
    this.correctionDrawer = document.getElementById("correction-drawer");
    this.btnCloseCorrection = document.getElementById("btn-close-correction");
    this.correctionInput = document.getElementById("correction-input");
    this.knownSignsList = document.getElementById("known-signs-list");
    this.btnSubmitCorrection = document.getElementById("btn-submit-correction");
    this.correctionStatus = document.getElementById("correction-status");
  }

  initEventListeners() {
    // 1. Live Webcam Toggle & Controls
    if (this.btnToggleWebcam) {
      this.btnToggleWebcam.addEventListener("click", () => this.toggleWebcam());
    }
    if (this.btnSnapFrame) {
      this.btnSnapFrame.addEventListener("click", () => this.snapSingleFrame());
    }
    if (this.camIntervalSlider) {
      this.camIntervalSlider.addEventListener("input", (e) => {
        this.captureIntervalMs = parseInt(e.target.value, 10);
        const estFps = Math.round(1000 / this.captureIntervalMs);
        if (this.valCamInterval) this.valCamInterval.textContent = `${this.captureIntervalMs}ms (~${estFps} FPS)`;
        if (this.isWebcamStreaming) {
          this.stopCaptureLoop();
          this.startCaptureLoop();
        }
      });
    }
    if (this.cameraSelect) {
      this.cameraSelect.addEventListener("change", () => {
        if (this.isWebcamStreaming) {
          this.stopWebcam();
          this.startWebcam();
        }
      });
    }
    if (this.btnResetSession) {
      this.btnResetSession.addEventListener("click", () => this.resetSessionContext());
    }

    // 2. Self-Learning Online Feedback
    if (this.btnThumbsUp) {
      this.btnThumbsUp.addEventListener("click", () => this.handleThumbsUp());
    }
    if (this.btnThumbsDown) {
      this.btnThumbsDown.addEventListener("click", () => this.handleThumbsDown());
    }
    if (this.btnCloseCorrection) {
      this.btnCloseCorrection.addEventListener("click", () => this.correctionDrawer.classList.add("hidden"));
    }
    if (this.btnSubmitCorrection) {
      this.btnSubmitCorrection.addEventListener("click", () => this.submitCorrection());
    }
    if (this.correctionInput) {
      this.correctionInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") this.submitCorrection();
      });
    }

    // 3. Quick-Target Benchmark Chips
    this.quickChips.forEach(chip => {
      chip.addEventListener("click", () => {
        const target = chip.getAttribute("data-target");
        this.loadSampleTarget(target);
      });
    });

    // 4. Mode Switch
    this.modeBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        this.modeBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.currentMode = btn.getAttribute("data-mode");
      });
    });

    // 5. View Tabs (Optical / Grad-CAM)
    if (this.tabSegmentation) this.tabSegmentation.addEventListener("click", () => this.switchView("optical"));
    if (this.tabGradcam) this.tabGradcam.addEventListener("click", () => this.switchView("gradcam"));

    // 6. Speech Controls
    if (this.btnSpeak) this.btnSpeak.addEventListener("click", () => this.speakTranslation());
    if (this.rateSlider && this.valRate) this.rateSlider.addEventListener("input", (e) => this.valRate.textContent = `${e.target.value}x`);
    if (this.pitchSlider && this.valPitch) this.pitchSlider.addEventListener("input", (e) => this.valPitch.textContent = e.target.value);

    // 7. Copy Buttons
    if (this.btnCopyEn) this.btnCopyEn.addEventListener("click", () => this.copyToClipboard(this.transEnglish.textContent));
    if (this.btnCopyHi) this.btnCopyHi.addEventListener("click", () => this.copyToClipboard(this.transHindi.textContent));

    // 8. Clear Workspace
    if (this.btnClearAll) this.btnClearAll.addEventListener("click", () => this.resetWorkspace());

    // 9. Modals
    if (this.btnOpenMetrics) this.btnOpenMetrics.addEventListener("click", () => this.openMetricsModal());
    if (this.btnCloseMetrics) this.btnCloseMetrics.addEventListener("click", () => this.modalMetrics.classList.remove("active"));
    if (this.btnOpenLearn) this.btnOpenLearn.addEventListener("click", () => this.modalLearn.classList.add("active"));
    if (this.btnCloseLearn) this.btnCloseLearn.addEventListener("click", () => this.modalLearn.classList.remove("active"));
    if (this.btnSubmitLearn) this.btnSubmitLearn.addEventListener("click", () => this.submitContinuousLearn());
  }

  /* ===================================================================
     WEBCAM STREAMING & CAPTURE PIPELINE
     =================================================================== */

  async toggleWebcam() {
    if (this.isWebcamStreaming) {
      await this.stopWebcam();
    } else {
      await this.startWebcam();
    }
  }

  async startWebcam() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert("Webcam API not supported in this browser. Please use Chrome/Firefox/Edge.");
      return;
    }

    try {
      this.btnToggleWebcam.disabled = true;
      this.btnToggleWebcam.innerHTML = `<span class="btn-icon">⏳</span> INITIALIZING...`;

      const deviceId = this.cameraSelect ? this.cameraSelect.value : null;
      const constraints = {
        video: deviceId 
          ? { deviceId: { exact: deviceId } } 
          : { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.webcamStream = stream;
      this.webcamVideo.srcObject = stream;
      await this.webcamVideo.play();

      this.isWebcamStreaming = true;
      this.webcamPlaceholder.classList.add("hidden");
      this.webcamVideo.classList.add("active");
      if (this.webcamLaser) this.webcamLaser.classList.add("active");

      // Update Button & Status
      this.btnToggleWebcam.innerHTML = `<span class="btn-icon">⏹</span> STOP LIVE WEBCAM`;
      this.btnToggleWebcam.classList.add("streaming");
      this.camStatusDot.className = "cam-status-dot live";
      this.camStatusText.textContent = "LIVE STREAMING";
      this.camStatusText.style.color = "#00ff9d";

      // Populate available camera devices
      await this.enumerateCameras();

      // Adjust HUD Canvas dimensions to match video stream
      if (this.webcamHudCanvas) {
        this.webcamHudCanvas.width = this.webcamVideo.videoWidth || 640;
        this.webcamHudCanvas.height = this.webcamVideo.videoHeight || 480;
      }

      // Start continuous sampling loop and 60 FPS HUD render loop
      this.startRenderLoop();
      this.startCaptureLoop();
      this.showToast("⚡ LIVE WEBCAM ACTIVE: GPU/WebGL acceleration online.", "success");

    } catch (err) {
      console.error("Webcam initialization failed:", err);
      alert(`Could not start webcam: ${err.message}. Please check browser camera permissions.`);
      this.btnToggleWebcam.innerHTML = `<span class="btn-icon">▶</span> START LIVE WEBCAM`;
      this.btnToggleWebcam.classList.remove("streaming");
      this.camStatusDot.className = "cam-status-dot offline";
      this.camStatusText.textContent = "OFFLINE";
    } finally {
      this.btnToggleWebcam.disabled = false;
    }
  }

  async stopWebcam() {
    this.stopCaptureLoop();
    this.stopRenderLoop();
    if (this.webcamStream) {
      this.webcamStream.getTracks().forEach(track => track.stop());
      this.webcamStream = null;
    }
    if (this.webcamVideo) {
      this.webcamVideo.srcObject = null;
      this.webcamVideo.classList.remove("active");
    }
    this.isWebcamStreaming = false;
    this.currentRegions = [];
    if (this.webcamPlaceholder) this.webcamPlaceholder.classList.remove("hidden");
    if (this.webcamLaser) this.webcamLaser.classList.remove("active");

    if (this.webcamHudCtx && this.webcamHudCanvas) {
      this.webcamHudCtx.clearRect(0, 0, this.webcamHudCanvas.width, this.webcamHudCanvas.height);
    }

    this.btnToggleWebcam.innerHTML = `<span class="btn-icon">▶</span> START LIVE WEBCAM`;
    this.btnToggleWebcam.classList.remove("streaming");
    this.camStatusDot.className = "cam-status-dot offline";
    this.camStatusText.textContent = "OFFLINE";
    this.camStatusText.style.color = "";
    this.camFpsText.textContent = "0 FPS";
  }

  startRenderLoop() {
    this.stopRenderLoop();
    const render = () => {
      if (this.isWebcamStreaming) {
        this.drawWebcamHudOverlay(this.currentRegions || []);
        this.renderLoopId = requestAnimationFrame(render);
      }
    };
    this.renderLoopId = requestAnimationFrame(render);
  }

  stopRenderLoop() {
    if (this.renderLoopId) {
      cancelAnimationFrame(this.renderLoopId);
      this.renderLoopId = null;
    }
  }

  startCaptureLoop() {
    this.stopCaptureLoop();
    this.captureTimer = setInterval(() => {
      this.captureAndPredictFrame();
    }, this.captureIntervalMs);
  }

  stopCaptureLoop() {
    if (this.captureTimer) {
      clearInterval(this.captureTimer);
      this.captureTimer = null;
    }
  }

  async snapSingleFrame() {
    if (!this.isWebcamStreaming) {
      // If camera not yet started, start it
      await this.startWebcam();
      return;
    }
    await this.captureAndPredictFrame();
  }

  async captureAndPredictFrame() {
    if (!this.isWebcamStreaming || !this.webcamVideo || this.webcamVideo.readyState < 2) return;
    if (this.isProcessingFrame) return; // Prevent network queue congestion

    this.isProcessingFrame = true;

    // 1. Ultra-fast GPU / Canvas downscaling to 320x240 for 8x smaller payload & 10x faster cv2
    const targetW = 320;
    const targetH = 240;
    this.offscreenCanvas.width = targetW;
    this.offscreenCanvas.height = targetH;
    this.offscreenCtx.drawImage(this.webcamVideo, 0, 0, targetW, targetH);

    // 2. High-speed base64 JPEG (compact 0.65 quality ~10KB payload)
    const frameBase64 = this.offscreenCanvas.toDataURL("image/jpeg", 0.65);

    // Mirror to optical canvas
    const snapImage = new Image();
    snapImage.src = frameBase64;
    this.currentImage = snapImage;

    // 3. True Client-side FPS calculation
    this.fpsCounter++;
    const now = performance.now();
    if (now - this.fpsLastTime >= 1000) {
      this.currentFps = Math.round((this.fpsCounter * 1000) / (now - this.fpsLastTime));
      this.camFpsText.textContent = `${this.currentFps} FPS`;
      this.fpsCounter = 0;
      this.fpsLastTime = now;
    }

    try {
      const resp = await fetch("/api/webcam/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          frame_base64: frameBase64,
          session_id: this.sessionId,
          preferred_brain: this.currentMode !== "auto" ? this.currentMode : null,
          allow_empty: true,
          include_gradcam: this.currentView === "gradcam"
        })
      });

      if (!resp.ok) {
        throw new Error(`Server returned ${resp.status}: ${resp.statusText}`);
      }

      const data = await resp.json();

      // Rescale bounding boxes from 320x240 back to display video dimensions
      const origW = this.webcamVideo.videoWidth || 640;
      const origH = this.webcamVideo.videoHeight || 480;
      const scaleX = origW / targetW;
      const scaleY = origH / targetH;

      if (data.regions && data.regions.length > 0) {
        data.regions.forEach(reg => {
          reg.bbox = [
            Math.round(reg.bbox[0] * scaleX),
            Math.round(reg.bbox[1] * scaleY),
            Math.round(reg.bbox[2] * scaleX),
            Math.round(reg.bbox[3] * scaleY)
          ];
        });
      }

      this.currentRegions = data.regions || [];
      this.handlePredictionResponse(data, snapImage);

    } catch (err) {
      console.warn("[WebcamPredict] Warning:", err);
    } finally {
      this.isProcessingFrame = false;
    }
  }

  async enumerateCameras() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices || !this.cameraSelect) return;
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(d => d.kind === "videoinput");
      
      const currentVal = this.cameraSelect.value;
      this.cameraSelect.innerHTML = "";

      videoDevices.forEach((dev, idx) => {
        const opt = document.createElement("option");
        opt.value = dev.deviceId;
        opt.textContent = dev.label || `Camera ${idx + 1}`;
        if (dev.deviceId === currentVal) opt.selected = true;
        this.cameraSelect.appendChild(opt);
      });
    } catch (e) {
      console.warn("Could not enumerate cameras:", e);
    }
  }

  async resetSessionContext() {
    try {
      const res = await fetch("/api/webcam/reset-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: this.sessionId })
      });
      this.sessionId = "webcam_session_" + Date.now();
      if (this.captionTokenTrail) {
        this.captionTokenTrail.innerHTML = `<span class="trail-token-empty">Session context reset</span>`;
      }
      this.showToast("✓ Verification dialogue context cleared (Zero context loss ready)", "info");
    } catch (e) {
      console.warn("Reset session context error:", e);
    }
  }

  /* ===================================================================
     UNIFIED PREDICTION RESPONSE & TACTICAL CAPTION HANDLER
     =================================================================== */

  handlePredictionResponse(data, sourceImage = null) {
    this.currentResponse = data;
    this.telemetryLatency.textContent = `${data.inference_time_ms} ms`;

    // 1. Calculate and format ACTUAL confidence score (NOT dummy)
    const actualConfPercent = (data.actual_confidence * 100).toFixed(1);
    this.sigConf.textContent = `${actualConfPercent}%`;

    // 2. Render Optical Canvas with Bounding Boxes
    const imgToRender = sourceImage || this.currentImage;
    if (imgToRender) {
      this.renderOpticalCanvas(imgToRender, data.regions);
    }

    // 3. Render Tactical HUD Canvas over Webcam Video
    this.drawWebcamHudOverlay(data.regions);

    // 4. Update Strip Carousel
    this.populateStripCarousel(data.regions);

    // 5. Update Translation Cards (Column 3)
    const enText = data.sentence.english_sentence || "(Awaiting hand gesture)";
    const hiText = data.sentence.hindi_sentence || "(अनुवाद की प्रतीक्षा)";
    this.transEnglish.textContent = enText;
    this.transHindi.textContent = hiText;
    this.transPhonetic.textContent = `Phonetic: ${data.speech.primary.phonetic_hint || "--"}`;

    // 6. Update Tactical Live Caption Box (Prominent Subtitle Bar)
    this.updateCaptionBox(data, actualConfPercent, enText, hiText);

    // 7. Update Grad-CAM view for top region
    if (data.regions && data.regions.length > 0) {
      this.selectRegion(0);
    }

    // 8. Auto-speak synthesized translation if significant gesture detected
    if (data.sentence && data.sentence.raw_tokens && data.sentence.raw_tokens.length > 0) {
      // Optional speech trigger
    }
  }

  updateCaptionBox(data, confPercent, enSentence, hiSentence) {
    if (!this.captionBox) return;

    // Standby when no hand is in frame
    if (data.regions_count === 0) {
      this.captionConfBadge.textContent = "ACTUAL CONF: 0.0%";
      this.captionVerifBadge.className = "caption-badge badge-verif offline";
      this.captionVerifBadge.textContent = "STANDBY (AWAITING GESTURE)";
      this.captionFeedbackIndicator.textContent = "";
      this.captionEnText.innerHTML = `<span class="caption-cursor">▌</span> Awaiting live gesture actions...`;
      this.captionHiText.textContent = "लाइव सांकेतिक भाषा इशारे शुरू करें...";
      this.captionTokenTrail.innerHTML = `<span class="trail-token-empty">Scanning for gesture actions in camera...</span>`;
      return;
    }

    // Actual Confidence Badge
    this.captionConfBadge.textContent = `ACTUAL CONF: ${confPercent}%`;

    // Verification Badge & Status
    const v = data.verification || {};
    this.captionVerifBadge.className = "caption-badge badge-verif";

    if (v.is_verified) {
      if (data.feedback_action === "reward") {
        this.captionVerifBadge.classList.add("rewarded");
        this.captionVerifBadge.textContent = `🟢 AI VERIFIED // REWARDED (${v.key_name || 'AI'})`;
        this.captionFeedbackIndicator.textContent = `[+0.10 REWARDED]`;
        this.captionFeedbackIndicator.style.color = "#00ff9d";
      } else if (data.feedback_action === "punish_and_train") {
        this.captionVerifBadge.classList.add("punished");
        this.captionVerifBadge.textContent = `🟣 TRAINED & ADAPTED (${v.key_name || 'AI'})`;
        this.captionFeedbackIndicator.textContent = `[CORRECTION TRAINED]`;
        this.captionFeedbackIndicator.style.color = "#ff0055";
      } else {
        this.captionVerifBadge.textContent = `🟢 VERIFIED (${v.key_name || 'AI'})`;
        this.captionFeedbackIndicator.textContent = "";
      }
    } else {
      this.captionVerifBadge.classList.add("offline");
      this.captionVerifBadge.textContent = v.fallback_to_local 
        ? `🟡 LOCAL (KEYS EXHAUSTED)` 
        : `🟡 LOCAL ONLY (OFFLINE)`;
      this.captionFeedbackIndicator.textContent = "[LOCAL PREDICTION]";
      this.captionFeedbackIndicator.style.color = "#ffb800";
    }

    // Live Subtitles
    this.captionEnText.innerHTML = `<span class="caption-cursor">▌</span> ${enSentence}`;
    this.captionHiText.textContent = hiSentence;

    // Token Trail
    const tokens = (data.sentence && data.sentence.raw_tokens) || data.raw_tokens || [];
    this.captionTokenTrail.innerHTML = "";
    if (tokens.length === 0) {
      this.captionTokenTrail.innerHTML = `<span class="trail-token-empty">Scanning for gesture actions...</span>`;
    } else {
      tokens.forEach(tok => {
        const pill = document.createElement("span");
        pill.className = "cap-token-pill" + (tok.length > 1 ? " word" : "");
        pill.textContent = tok;
        this.captionTokenTrail.appendChild(pill);
      });
    }
  }

  drawWebcamHudOverlay(regions = []) {
    if (!this.webcamHudCtx || !this.webcamHudCanvas) return;
    const ctx = this.webcamHudCtx;
    const cw = this.webcamHudCanvas.width;
    const ch = this.webcamHudCanvas.height;

    ctx.clearRect(0, 0, cw, ch);
    if (!this.isWebcamStreaming) return;

    // Subtle tactical corner brackets around live feed
    ctx.strokeStyle = "rgba(0, 240, 255, 0.4)";
    ctx.lineWidth = 2;
    const m = 12;
    const len = 20;

    // Top-left
    ctx.beginPath();
    ctx.moveTo(m, m + len); ctx.lineTo(m, m); ctx.lineTo(m + len, m);
    ctx.stroke();
    // Top-right
    ctx.beginPath();
    ctx.moveTo(cw - m - len, m); ctx.lineTo(cw - m, m); ctx.lineTo(cw - m, m + len);
    ctx.stroke();
    // Bottom-left
    ctx.beginPath();
    ctx.moveTo(m, ch - m - len); ctx.lineTo(m, ch - m); ctx.lineTo(m + len, ch - m);
    ctx.stroke();
    // Bottom-right
    ctx.beginPath();
    ctx.moveTo(cw - m - len, ch - m); ctx.lineTo(cw - m, ch - m); ctx.lineTo(cw - m, ch - m - len);
    ctx.stroke();

    // Center reticle
    const cx = cw / 2;
    const cy = ch / 2;
    ctx.strokeStyle = "rgba(0, 240, 255, 0.25)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(cx, cy, 28, 0, Math.PI * 2);
    ctx.stroke();

    // Draw detected hand bounding boxes
    if (regions && regions.length > 0) {
      regions.forEach((reg, i) => {
        const [bx, by, bw, bh] = reg.bbox;
        // Notice: mirrored video means x coordinate is reflected for overlay
        const rx = cw - (bx + bw);
        const ry = by;

        ctx.strokeStyle = "#00ff9d";
        ctx.lineWidth = 2;
        ctx.strokeRect(rx, ry, bw, bh);

        // Label
        const txt = `[${reg.predicted_sign}] ${(reg.confidence * 100).toFixed(0)}%`;
        ctx.font = "bold 11px monospace";
        ctx.fillStyle = "rgba(0, 0, 0, 0.75)";
        ctx.fillRect(rx, Math.max(0, ry - 18), 85, 18);
        ctx.fillStyle = "#00ff9d";
        ctx.fillText(txt, rx + 4, Math.max(14, ry - 5));
      });
    }
  }

  async pollVerifierStatus() {
    try {
      const res = await fetch("/api/verifier/status");
      if (!res.ok) return;
      const data = await res.json();

      if (this.telemetryVerifier) {
        if (data.is_available) {
          this.telemetryVerifier.textContent = "ONLINE (ACTIVE)";
          this.telemetryVerifier.className = "telemetry-val text-green";
        } else {
          this.telemetryVerifier.textContent = "OFFLINE (LOCAL)";
          this.telemetryVerifier.className = "telemetry-val text-amber";
        }
      }

      if (this.vtStatus) {
        this.vtStatus.textContent = data.is_available ? "ONLINE & ARMED" : "OFFLINE FALLBACK";
        this.vtStatus.className = data.is_available ? "vt-val text-green" : "vt-val text-amber";
      }

      if (this.vtActiveKey) {
        this.vtActiveKey.textContent = data.active_slot || "--";
      }

      if (this.vtFallbackChain && data.key_slots) {
        const chain = data.key_slots.map(s => `${s.provider.toUpperCase()}${s.is_exhausted ? ' (Exhausted)' : ''}`).join(" → ") + " → Offline";
        this.vtFallbackChain.textContent = chain;
      }

    } catch (e) {
      console.warn("Could not poll verifier status:", e);
    }
  }

  /* ===================================================================
     BENCHMARK SAMPLE CHIPS TARGETING (ONE-CLICK SIMULATION)
     =================================================================== */

  async loadSampleTarget(filename) {
    if (this.webcamLaser) this.webcamLaser.classList.add("active");
    try {
      const url = `/api/sample-images/${filename}`;
      const imgRes = await fetch(url);
      if (!imgRes.ok) throw new Error("Sample image not found on server");
      const blob = await imgRes.blob();

      // Convert blob to base64
      const reader = new FileReader();
      reader.onload = async (e) => {
        const frameBase64 = e.target.result;
        const snapImage = new Image();
        snapImage.onload = async () => {
          this.currentImage = snapImage;
          try {
            const resp = await fetch("/api/webcam/predict", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                frame_base64: frameBase64,
                session_id: this.sessionId,
                preferred_brain: this.currentMode !== "auto" ? this.currentMode : null,
                allow_empty: false
              })
            });
            if (!resp.ok) throw new Error(`Prediction error: ${resp.statusText}`);
            const data = await resp.json();
            this.handlePredictionResponse(data, snapImage);
          } catch (err) {
            console.error(err);
            alert("Prediction failure: " + err.message);
          } finally {
            if (this.webcamLaser) this.webcamLaser.classList.remove("active");
          }
        };
        snapImage.src = frameBase64;
      };
      reader.readAsDataURL(blob);

    } catch (e) {
      console.error(e);
      alert("Could not load sample: " + e.message);
      if (this.webcamLaser) this.webcamLaser.classList.remove("active");
    }
  }

  /* ===================================================================
     CANVAS, GRAD-CAM & STRIP VISUALIZERS
     =================================================================== */

  renderOpticalCanvas(img, regions = []) {
    if (!this.opticalCtx || !this.opticalCanvas) return;
    if (this.opticalPlaceholder) this.opticalPlaceholder.style.display = "none";
    const container = document.getElementById("canvas-container");
    const maxW = container ? container.clientWidth - 10 : 400;
    const maxH = container ? container.clientHeight - 10 : 300;

    const scale = Math.min(maxW / img.width, maxH / img.height, 1.0);
    const w = img.width * scale;
    const h = img.height * scale;

    this.opticalCanvas.width = w;
    this.opticalCanvas.height = h;
    this.opticalCtx.clearRect(0, 0, w, h);
    this.opticalCtx.drawImage(img, 0, 0, w, h);

    regions.forEach((reg, idx) => {
      const [bx, by, bw, bh] = reg.bbox;
      const rx = bx * scale;
      const ry = by * scale;
      const rw = bw * scale;
      const rh = bh * scale;

      const isSelected = idx === this.selectedRegionIdx;
      const strokeColor = isSelected ? "#00ff9d" : "#00f0ff";

      this.opticalCtx.save();
      this.opticalCtx.strokeStyle = strokeColor;
      this.opticalCtx.lineWidth = isSelected ? 3 : 2;
      this.opticalCtx.shadowColor = strokeColor;
      this.opticalCtx.shadowBlur = 8;
      this.opticalCtx.strokeRect(rx, ry, rw, rh);

      const tagText = `#${idx + 1} [${reg.predicted_sign}] ${(reg.confidence * 100).toFixed(0)}%`;
      this.opticalCtx.font = "bold 11px monospace";
      this.opticalCtx.fillStyle = "rgba(4, 7, 12, 0.9)";
      this.opticalCtx.fillRect(rx, Math.max(0, ry - 18), 90, 18);
      this.opticalCtx.strokeStyle = strokeColor;
      this.opticalCtx.lineWidth = 1;
      this.opticalCtx.strokeRect(rx, Math.max(0, ry - 18), 90, 18);
      this.opticalCtx.fillStyle = strokeColor;
      this.opticalCtx.fillText(tagText, rx + 4, Math.max(0, ry - 18) + 13);
      this.opticalCtx.restore();
    });
  }

  populateStripCarousel(regions) {
    if (!this.stripCarousel) return;
    this.stripCarousel.innerHTML = "";
    if (!regions || regions.length === 0) {
      if (this.stripCount) this.stripCount.textContent = "0 TOKENS DETECTED";
      this.stripCarousel.innerHTML = `<div class="strip-empty-hint">No multi-sign sequence loaded</div>`;
      return;
    }

    if (this.stripCount) this.stripCount.textContent = `${regions.length} TOKENS DETECTED`;

    regions.forEach((reg, idx) => {
      const card = document.createElement("div");
      card.className = "strip-card" + (idx === this.selectedRegionIdx ? " active" : "");
      card.innerHTML = `
        <span class="strip-badge">#${idx + 1}</span>
        <img class="strip-thumb" src="${reg.gradcam_heatmap || reg.crop_base64 || ''}" alt="Sign ${reg.predicted_sign}">
        <span class="strip-pred-tag">${reg.predicted_sign}</span>
        <div class="strip-conf-bar">
          <div class="strip-conf-fill" style="width: ${(reg.confidence * 100).toFixed(0)}%"></div>
        </div>
      `;
      card.addEventListener("click", () => this.selectRegion(idx));
      this.stripCarousel.appendChild(card);
    });
  }

  selectRegion(idx) {
    if (!this.currentResponse || !this.currentResponse.regions || !this.currentResponse.regions[idx]) return;
    this.selectedRegionIdx = idx;
    const reg = this.currentResponse.regions[idx];

    const cards = this.stripCarousel ? this.stripCarousel.querySelectorAll(".strip-card") : [];
    cards.forEach((c, i) => c.classList.toggle("active", i === idx));

    if (this.gradcamImg && reg.gradcam_heatmap) {
      this.gradcamImg.src = reg.gradcam_heatmap;
      this.gradcamImg.style.display = "block";
      if (this.gradcamPlaceholder) this.gradcamPlaceholder.style.display = "none";
    }

    if (this.sigConf) this.sigConf.textContent = `${(reg.confidence * 100).toFixed(1)}%`;
    if (this.sigMargin) this.sigMargin.textContent = `+${(reg.decision_margin * 100).toFixed(1)}%`;
    if (this.sigHandedness) this.sigHandedness.textContent = reg.handedness ? reg.handedness.toUpperCase() : "ONE-HANDED";

    if (this.currentImage) {
      this.renderOpticalCanvas(this.currentImage, this.currentResponse.regions);
    }
  }

  switchView(view) {
    this.currentView = view;
    if (view === "optical") {
      if (this.tabSegmentation) this.tabSegmentation.classList.add("active");
      if (this.tabGradcam) this.tabGradcam.classList.remove("active");
      if (this.paneOptical) this.paneOptical.classList.add("active");
      if (this.paneGradcam) this.paneGradcam.classList.remove("active");
    } else {
      if (this.tabGradcam) this.tabGradcam.classList.add("active");
      if (this.tabSegmentation) this.tabSegmentation.classList.remove("active");
      if (this.paneGradcam) this.paneGradcam.classList.add("active");
      if (this.paneOptical) this.paneOptical.classList.remove("active");
    }
  }

  /* ===================================================================
     AUDIO TTS & WAVEFORM VISUALIZER
     =================================================================== */

  initVoices() {
    if (!this.synth) return;
    const populate = () => {
      this.availableVoices = this.synth.getVoices();
      this.updateVoiceDropdown();
    };
    populate();
    if (this.synth.onvoiceschanged !== undefined) {
      this.synth.onvoiceschanged = populate;
    }
  }

  updateVoiceDropdown() {
    if (!this.availableVoices.length || !this.voiceSelect) return;
    const enInVoice = this.availableVoices.find(v => v.lang === "en-IN" || v.lang.startsWith("en-IN") || v.name.includes("India"));
    const hiInVoice = this.availableVoices.find(v => v.lang === "hi-IN" || v.lang.startsWith("hi"));

    this.voiceSelect.innerHTML = "";
    const enOpt = document.createElement("option");
    enOpt.value = "en-IN";
    enOpt.textContent = enInVoice ? `Indian English (${enInVoice.name})` : "English (System)";
    this.voiceSelect.appendChild(enOpt);

    const hiOpt = document.createElement("option");
    hiOpt.value = "hi-IN";
    hiOpt.textContent = hiInVoice ? `Hindi (${hiInVoice.name})` : "Hindi (System Devanagari)";
    this.voiceSelect.appendChild(hiOpt);
  }

  speakTranslation() {
    if (!this.synth || !this.currentResponse) return;
    this.synth.cancel();

    const selectedLang = this.voiceSelect ? this.voiceSelect.value : "en-IN";
    const isHindi = selectedLang.startsWith("hi");
    const textToSpeak = isHindi 
      ? this.currentResponse.sentence.hindi_sentence 
      : this.currentResponse.sentence.english_sentence;

    if (!textToSpeak) return;

    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.lang = selectedLang;
    utterance.rate = this.rateSlider ? parseFloat(this.rateSlider.value) : 1.0;
    utterance.pitch = this.pitchSlider ? parseFloat(this.pitchSlider.value) : 1.0;

    const targetVoice = this.availableVoices.find(v => v.lang === selectedLang || v.lang.startsWith(selectedLang));
    if (targetVoice) utterance.voice = targetVoice;

    utterance.onstart = () => {
      this.isSpeaking = true;
      if (this.ttsAudioStatus) {
        this.ttsAudioStatus.textContent = `SYNTHESIZING [${selectedLang.toUpperCase()}]`;
        this.ttsAudioStatus.style.color = "#00ff9d";
      }
    };

    utterance.onend = () => {
      this.isSpeaking = false;
      if (this.ttsAudioStatus) {
        this.ttsAudioStatus.textContent = "STANDBY";
        this.ttsAudioStatus.style.color = "#00f0ff";
      }
    };

    utterance.onerror = () => {
      this.isSpeaking = false;
      if (this.ttsAudioStatus) {
        this.ttsAudioStatus.textContent = "STANDBY";
      }
    };

    this.synth.speak(utterance);
  }

  initWaveformVisualizer() {
    if (!this.waveformCanvas || !this.waveformCtx) return;
    const canvas = this.waveformCanvas;
    const ctx = this.waveformCtx;
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const numBars = 32;
      const barWidth = canvas.width / numBars - 2;

      for (let i = 0; i < numBars; i++) {
        let height = 4;
        if (this.isSpeaking) {
          const wave1 = Math.sin(phase * 0.15 + i * 0.4);
          const wave2 = Math.cos(phase * 0.22 - i * 0.3);
          const energy = Math.abs(wave1 * wave2);
          height = Math.max(6, energy * (canvas.height - 12) + 4);
        } else {
          height = Math.max(3, Math.sin(phase * 0.03 + i * 0.2) * 4 + 4);
        }

        const x = i * (barWidth + 2);
        const y = canvas.height - height;

        const grad = ctx.createLinearGradient(0, y, 0, canvas.height);
        grad.addColorStop(0, this.isSpeaking ? "#00ff9d" : "#00f0ff");
        grad.addColorStop(1, "rgba(0, 240, 255, 0.15)");

        ctx.fillStyle = grad;
        ctx.fillRect(x, y, barWidth, height);

        ctx.fillStyle = this.isSpeaking ? "#ffffff" : "#00f0ff";
        ctx.fillRect(x, Math.max(0, y - 2), barWidth, 1.5);
      }

      phase += 1;
      this.animationFrameId = requestAnimationFrame(render);
    };

    render();
  }

  /* ===================================================================
     SELF-LEARNING ONLINE FEEDBACK (THUMBS UP / DOWN)
     =================================================================== */

  async handleThumbsUp() {
    if (!this.currentResponse || !this.currentResponse.regions || this.currentResponse.regions.length === 0) return;
    const reg = this.currentResponse.regions[this.selectedRegionIdx] || this.currentResponse.regions[0];
    const cropB64 = reg.crop_base64 || reg.gradcam_heatmap;

    this.btnThumbsUp.disabled = true;
    this.btnThumbsUp.innerHTML = `<span class="btn-icon">⏳</span> REINFORCING...`;

    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          is_positive: true,
          predicted_sign: reg.predicted_sign,
          crop_base64: cropB64,
          is_dual_hand: reg.is_dual_hand
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Feedback submission failed");

      this.btnThumbsUp.innerHTML = `<span class="btn-icon">✓</span> CONFIRMED!`;
      this.btnThumbsUp.classList.add("btn-success");
      if (this.correctionDrawer) this.correctionDrawer.classList.add("hidden");

      this.showToast(`★ MODEL REWARDED: Gesture [${reg.predicted_sign}] confirmed & reinforced.`, "success");
      this.checkHealth();
    } catch (err) {
      console.error(err);
      this.showToast(`Error rewarding model: ${err.message}`, "error");
      this.btnThumbsUp.innerHTML = `<span class="btn-icon">👍</span> REWARD (CORRECT)`;
    } finally {
      this.btnThumbsUp.disabled = false;
    }
  }

  handleThumbsDown() {
    if (!this.currentResponse || !this.currentResponse.regions || this.currentResponse.regions.length === 0) return;
    const reg = this.currentResponse.regions[this.selectedRegionIdx] || this.currentResponse.regions[0];

    if (!this.correctionDrawer) return;
    this.correctionDrawer.classList.remove("hidden");
    this.correctionInput.value = "";
    this.correctionInput.focus();
    this.correctionStatus.textContent = `Teach the correct sign for token #${this.selectedRegionIdx + 1} (currently recognized as '${reg.predicted_sign}').`;
    this.correctionStatus.className = "correction-status";
  }

  async submitCorrection() {
    const correctSign = this.correctionInput.value.trim().toUpperCase();
    if (!correctSign) {
      this.correctionStatus.textContent = "Please enter the correct sign name (e.g. A, B, 5, NAMASTE, WATER).";
      this.correctionStatus.className = "correction-status error";
      return;
    }

    if (!this.currentResponse || !this.currentResponse.regions || this.currentResponse.regions.length === 0) return;
    const reg = this.currentResponse.regions[this.selectedRegionIdx] || this.currentResponse.regions[0];
    const cropB64 = reg.crop_base64 || reg.gradcam_heatmap;

    this.btnSubmitCorrection.disabled = true;
    this.btnSubmitCorrection.textContent = "PUNISHING & ADAPTING...";

    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          is_positive: false,
          predicted_sign: reg.predicted_sign,
          correct_sign: correctSign,
          crop_base64: cropB64,
          is_dual_hand: reg.is_dual_hand
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Correction failed");

      reg.predicted_sign = correctSign;
      if (data.updated_prediction) Object.assign(reg, data.updated_prediction);

      this.populateStripCarousel(this.currentResponse.regions);
      this.selectRegion(this.selectedRegionIdx);

      if (data.updated_sentence) {
        this.currentResponse.sentence = data.updated_sentence;
        this.transEnglish.textContent = data.updated_sentence.english_sentence;
        this.transHindi.textContent = data.updated_sentence.hindi_sentence;
        this.updateCaptionBox(this.currentResponse, (reg.confidence * 100).toFixed(1), data.updated_sentence.english_sentence, data.updated_sentence.hindi_sentence);
      }
      if (data.updated_speech) this.currentResponse.speech = data.updated_speech;

      this.correctionStatus.textContent = `✓ Severe penalty applied to '${data.previous_sign}'. Prototype registered for '${data.corrected_sign}'. Instant online learning complete!`;
      this.correctionStatus.className = "correction-status success";
      this.showToast(`⚡ MODEL ADAPTED: Penalized '${data.previous_sign}' and reinforced '${data.corrected_sign}'.`, "success");

      this.checkHealth();
      this.speakTranslation();
    } catch (err) {
      console.error(err);
      this.correctionStatus.textContent = `Error: ${err.message}`;
      this.correctionStatus.className = "correction-status error";
      this.showToast(`Correction error: ${err.message}`, "error");
    } finally {
      this.btnSubmitCorrection.disabled = false;
      this.btnSubmitCorrection.textContent = "PUNISH WRONG & TRAIN NEW";
    }
  }

  /* ===================================================================
     HEALTH & VOCABULARY
     =================================================================== */

  startClock() {
    setInterval(() => {
      const now = new Date();
      if (this.footerTime) this.footerTime.textContent = now.toUTCString().replace("GMT", "UTC");
    }, 1000);
  }

  async checkHealth() {
    try {
      const res = await fetch("/api/health");
      if (res.ok) {
        const data = await res.json();
        if (this.protoCount) this.protoCount.textContent = `${data.prototype_memory_words} ISL Prototypes`;
        if (this.deviceAccel) this.deviceAccel.textContent = data.device.toUpperCase();
      }
      await this.loadVocabularyDatalist();
    } catch (e) {
      console.warn("Health check error:", e);
    }
  }

  async loadVocabularyDatalist() {
    try {
      const res = await fetch("/api/vocabulary");
      if (!res.ok) return;
      const data = await res.json();
      if (!this.knownSignsList) return;
      this.knownSignsList.innerHTML = "";
      
      const allSigns = [...(data.alphanumerics || []), ...(data.words || [])];
      allSigns.forEach(s => {
        const opt = document.createElement("option");
        opt.value = typeof s === "object" ? s.class_name : s;
        this.knownSignsList.appendChild(opt);
      });
    } catch (e) {
      console.warn("Could not load vocabulary datalist:", e);
    }
  }

  async openMetricsModal() {
    if (!this.modalMetrics) return;
    this.modalMetrics.classList.add("active");
    try {
      const res = await fetch("/api/metrics");
      if (!res.ok) throw new Error("Metrics not available");
      const m = await res.json();

      document.getElementById("kpi-acc").textContent = `${(m.overall_accuracy * 100).toFixed(1)}%`;
      document.getElementById("kpi-top3").textContent = `${(m.top3_accuracy * 100).toFixed(1)}%`;
      document.getElementById("kpi-f1").textContent = m.macro_f1.toFixed(3);
      document.getElementById("kpi-prec").textContent = m.macro_precision.toFixed(3);
      document.getElementById("kpi-recall").textContent = m.macro_recall.toFixed(3);

      document.getElementById("img-confusion-matrix").src = `/api/metrics/confusion-matrix?t=${Date.now()}`;
      document.getElementById("img-roc-curve").src = `/api/metrics/roc-curve?t=${Date.now()}`;
    } catch (e) {
      console.warn("Could not fetch metrics:", e);
    }
  }

  async submitContinuousLearn() {
    const wordInput = document.getElementById("learn-word");
    const catInput = document.getElementById("learn-category");
    const fileInput = document.getElementById("learn-file");

    if (!wordInput.value.trim()) {
      alert("Please enter a gesture word identifier.");
      return;
    }
    if (!fileInput.files.length) {
      alert("Please select an image file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("word", wordInput.value.trim().toUpperCase());
    formData.append("category", catInput.value);

    this.learnStatus.textContent = "Registering prototype into local memory...";
    this.learnStatus.style.color = "#00f0ff";

    try {
      const res = await fetch("/api/learn", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Learning failure");
      this.learnStatus.textContent = `✓ Success: Registered [${data.word}]. Total prototypes: ${data.total_prototypes}`;
      this.learnStatus.style.color = "#00ff9d";
      this.checkHealth();
    } catch (err) {
      this.learnStatus.textContent = `✗ Error: ${err.message}`;
      this.learnStatus.style.color = "#ff0055";
    }
  }

  showToast(message, type = "info") {
    console.log(`[TOAST ${type.toUpperCase()}]`, message);
    const toast = document.createElement("div");
    toast.className = `hud-toast toast-${type}`;
    toast.style.cssText = `
      position: fixed;
      bottom: 45px;
      right: 25px;
      background: ${type === 'success' ? 'rgba(16, 185, 129, 0.95)' : (type === 'error' ? 'rgba(239, 68, 68, 0.95)' : 'rgba(0, 240, 255, 0.95)')};
      color: #07090e;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 800;
      padding: 10px 16px;
      border-radius: 4px;
      box-shadow: 0 4px 15px rgba(0,0,0,0.5);
      z-index: 9999;
      transition: opacity 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  }

  copyToClipboard(text) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      alert("Copied to clipboard!");
    }).catch(e => console.error(e));
  }

  resetWorkspace() {
    if (this.synth) this.synth.cancel();
    this.currentResponse = null;
    this.currentImage = null;
    if (this.opticalCtx && this.opticalCanvas) {
      this.opticalCtx.clearRect(0, 0, this.opticalCanvas.width, this.opticalCanvas.height);
    }
    if (this.opticalPlaceholder) this.opticalPlaceholder.style.display = "flex";
    if (this.gradcamImg) {
      this.gradcamImg.src = "";
      this.gradcamImg.style.display = "none";
    }
    if (this.gradcamPlaceholder) this.gradcamPlaceholder.style.display = "flex";
    if (this.stripCarousel) this.stripCarousel.innerHTML = `<div class="strip-empty-hint">No multi-sign sequence loaded</div>`;
    if (this.stripCount) this.stripCount.textContent = "0 TOKENS DETECTED";
    if (this.transEnglish) this.transEnglish.textContent = "Awaiting input gesture...";
    if (this.transHindi) this.transHindi.textContent = "अनुवाद की प्रतीक्षा...";
    if (this.transPhonetic) this.transPhonetic.textContent = "Phonetic: --";
    if (this.sigConf) this.sigConf.textContent = "--%";
    if (this.sigMargin) this.sigMargin.textContent = "--";
    if (this.sigHandedness) this.sigHandedness.textContent = "--";
    if (this.telemetryLatency) this.telemetryLatency.textContent = "-- ms";

    if (this.captionEnText) this.captionEnText.innerHTML = `<span class="caption-cursor">▌</span> Awaiting live gesture actions...`;
    if (this.captionHiText) this.captionHiText.textContent = "लाइव सांकेतिक भाषा इशारे शुरू करें...";
    if (this.captionConfBadge) this.captionConfBadge.textContent = "ACTUAL CONF: --%";
    if (this.captionVerifBadge) {
      this.captionVerifBadge.textContent = "STANDBY";
      this.captionVerifBadge.className = "caption-badge badge-verif";
    }
    if (this.captionTokenTrail) this.captionTokenTrail.innerHTML = `<span class="trail-token-empty">No gestures detected yet</span>`;
    if (this.captionFeedbackIndicator) this.captionFeedbackIndicator.textContent = "";
  }
}

// Initialize on DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  window.astraApp = new AstraVisionApp();
});

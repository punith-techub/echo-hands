/**
 * ECHOHANDS 5.0 // ASTRA-VISION Tactical ISL Neural HUD Controller
 * Zero-Latency Web Speech API, Real-Time Waveform Visualizer,
 * Optical Multi-Sign Strip Inspector, and Tactical Telemetry.
 */

class AstraVisionApp {
  constructor() {
    this.currentMode = "auto";
    this.currentResponse = null;
    this.currentImage = null;
    this.selectedRegionIdx = 0;
    this.isSpeaking = false;
    this.animationFrameId = null;

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
  }

  initDOMElements() {
    // Dropzone & Ingestion
    this.dropzone = document.getElementById("dropzone");
    this.fileInput = document.getElementById("file-input");
    this.laser = document.getElementById("scanning-laser");
    this.quickChips = document.querySelectorAll(".chip-btn");
    this.modeBtns = document.querySelectorAll(".mode-btn");

    // Canvases & Views
    this.opticalCanvas = document.getElementById("optical-canvas");
    this.opticalCtx = this.opticalCanvas.getContext("2d");
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

    // Translations & Speech
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
    this.waveformCtx = this.waveformCanvas.getContext("2d");

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
    // Self-Learning Online Feedback
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
    // File Ingestion
    this.dropzone.addEventListener("click", () => this.fileInput.click());
    this.fileInput.addEventListener("change", (e) => {
      if (e.target.files.length) this.uploadFile(e.target.files[0]);
    });

    this.dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      this.dropzone.classList.add("dragover");
    });
    this.dropzone.addEventListener("dragleave", () => this.dropzone.classList.remove("dragover"));
    this.dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      this.dropzone.classList.remove("dragover");
      if (e.dataTransfer.files.length) this.uploadFile(e.dataTransfer.files[0]);
    });

    // Quick Chips
    this.quickChips.forEach(chip => {
      chip.addEventListener("click", () => {
        const target = chip.getAttribute("data-target");
        this.loadSampleTarget(target);
      });
    });

    // Mode Switch
    this.modeBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        this.modeBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.currentMode = btn.getAttribute("data-mode");
      });
    });

    // View Tabs
    this.tabSegmentation.addEventListener("click", () => this.switchView("optical"));
    this.tabGradcam.addEventListener("click", () => this.switchView("gradcam"));

    // Speech Controls
    this.btnSpeak.addEventListener("click", () => this.speakTranslation());
    this.rateSlider.addEventListener("input", (e) => this.valRate.textContent = `${e.target.value}x`);
    this.pitchSlider.addEventListener("input", (e) => this.valPitch.textContent = e.target.value);

    // Copy Buttons
    this.btnCopyEn.addEventListener("click", () => this.copyToClipboard(this.transEnglish.textContent));
    this.btnCopyHi.addEventListener("click", () => this.copyToClipboard(this.transHindi.textContent));

    // Clear
    this.btnClearAll.addEventListener("click", () => this.resetWorkspace());

    // Modals
    this.btnOpenMetrics.addEventListener("click", () => this.openMetricsModal());
    this.btnCloseMetrics.addEventListener("click", () => this.modalMetrics.classList.remove("active"));
    this.btnOpenLearn.addEventListener("click", () => this.modalLearn.classList.add("active"));
    this.btnCloseLearn.addEventListener("click", () => this.modalLearn.classList.remove("active"));
    this.btnSubmitLearn.addEventListener("click", () => this.submitContinuousLearn());
  }

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
    if (!this.availableVoices.length) return;
    // Find best match for en-IN and hi-IN
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

  startClock() {
    setInterval(() => {
      const now = new Date();
      this.footerTime.textContent = now.toUTCString().replace("GMT", "UTC");
    }, 1000);
  }

  async checkHealth() {
    try {
      const res = await fetch("/api/health");
      if (res.ok) {
        const data = await res.json();
        this.protoCount.textContent = `${data.prototype_memory_words} ISL Prototypes`;
        this.deviceAccel.textContent = data.device.toUpperCase();
      }
      await this.loadVocabularyDatalist();
    } catch (e) {
      console.warn("Health check error:", e);
    }
  }

  switchView(view) {
    if (view === "optical") {
      this.tabSegmentation.classList.add("active");
      this.tabGradcam.classList.remove("active");
      this.paneOptical.classList.add("active");
      this.paneGradcam.classList.remove("active");
    } else {
      this.tabGradcam.classList.add("active");
      this.tabSegmentation.classList.remove("active");
      this.paneGradcam.classList.add("active");
      this.paneOptical.classList.remove("active");
    }
  }

  async uploadFile(file) {
    if (!file) return;
    this.laser.classList.add("active");

    // Load file locally for instant canvas render
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        this.currentImage = img;
        this.renderOpticalCanvas(img, []);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);

    // Send to prediction API
    const formData = new FormData();
    formData.append("file", file);
    if (this.currentMode !== "auto") {
      formData.append("preferred_brain", this.currentMode);
    }

    try {
      const resp = await fetch("/api/predict", {
        method: "POST",
        body: formData
      });
      if (!resp.ok) throw new Error(`Inference error: ${resp.statusText}`);
      const data = await resp.json();
      this.handlePredictionResponse(data);
    } catch (err) {
      console.error(err);
      alert("Prediction failure: " + err.message);
    } finally {
      this.laser.classList.remove("active");
    }
  }

  async loadSampleTarget(filename) {
    this.laser.classList.add("active");
    try {
      const url = `/api/sample-images/${filename}`;
      const imgRes = await fetch(url);
      if (!imgRes.ok) throw new Error("Sample image not found on server");
      const blob = await imgRes.blob();
      const file = new File([blob], filename, { type: blob.type });
      await this.uploadFile(file);
    } catch (e) {
      console.error(e);
      alert("Could not load sample: " + e.message);
      this.laser.classList.remove("active");
    }
  }

  handlePredictionResponse(data) {
    this.currentResponse = data;
    this.telemetryLatency.textContent = `${data.inference_time_ms} ms`;

    // 1. Render Optical Canvas with Bounding Boxes
    if (this.currentImage) {
      this.renderOpticalCanvas(this.currentImage, data.regions);
    }

    // 2. Populate Strip Carousel
    this.populateStripCarousel(data.regions);

    // 3. Render Translations
    this.transEnglish.textContent = data.sentence.english_sentence || "(No gestures recognized)";
    this.transHindi.textContent = data.sentence.hindi_sentence || "(अनुवाद अनुपलब्ध)";
    this.transPhonetic.textContent = `Phonetic: ${data.speech.primary.phonetic_hint || "--"}`;

    // 4. Update Grad-CAM view for top/first region
    if (data.regions && data.regions.length > 0) {
      this.selectRegion(0);
    }

    // 5. Trigger Web Speech Auto-playback if available
    this.speakTranslation();
  }

  renderOpticalCanvas(img, regions = []) {
    this.opticalPlaceholder.style.display = "none";
    const container = document.getElementById("canvas-container");
    const maxW = container.clientWidth - 10;
    const maxH = container.clientHeight - 10;

    // Scale to fit while maintaining aspect ratio
    const scale = Math.min(maxW / img.width, maxH / img.height, 1.0);
    const w = img.width * scale;
    const h = img.height * scale;

    this.opticalCanvas.width = w;
    this.opticalCanvas.height = h;
    this.opticalCtx.clearRect(0, 0, w, h);
    this.opticalCtx.drawImage(img, 0, 0, w, h);

    // Draw tactical bounding boxes and sequence badges
    regions.forEach((reg, idx) => {
      const [bx, by, bw, bh] = reg.bbox;
      const rx = bx * scale;
      const ry = by * scale;
      const rw = bw * scale;
      const rh = bh * scale;

      const isSelected = idx === this.selectedRegionIdx;
      const strokeColor = isSelected ? "#00ff9d" : "#00f0ff";

      // Tactical glowing box
      this.opticalCtx.save();
      this.opticalCtx.strokeStyle = strokeColor;
      this.opticalCtx.lineWidth = isSelected ? 3 : 2;
      this.opticalCtx.shadowColor = strokeColor;
      this.opticalCtx.shadowBlur = 8;
      this.opticalCtx.strokeRect(rx, ry, rw, rh);

      // Corner accent brackets
      const bracketLen = Math.min(12, rw / 3);
      this.opticalCtx.lineWidth = 3;
      // Top-left
      this.opticalCtx.beginPath();
      this.opticalCtx.moveTo(rx, ry + bracketLen);
      this.opticalCtx.lineTo(rx, ry);
      this.opticalCtx.lineTo(rx + bracketLen, ry);
      this.opticalCtx.stroke();

      // Badge tag: "#1 [H] 98%"
      const tagText = `#${idx + 1} [${reg.predicted_sign}] ${(reg.confidence * 100).toFixed(0)}%`;
      this.opticalCtx.font = "bold 11px 'JetBrains Mono', monospace";
      const tagMetrics = this.opticalCtx.measureText(tagText);
      const tagW = tagMetrics.width + 10;
      const tagH = 18;

      this.opticalCtx.fillStyle = "rgba(4, 7, 12, 0.9)";
      this.opticalCtx.fillRect(rx, Math.max(0, ry - tagH - 2), tagW, tagH);
      this.opticalCtx.strokeStyle = strokeColor;
      this.opticalCtx.lineWidth = 1;
      this.opticalCtx.strokeRect(rx, Math.max(0, ry - tagH - 2), tagW, tagH);

      this.opticalCtx.fillStyle = strokeColor;
      this.opticalCtx.fillText(tagText, rx + 5, Math.max(0, ry - tagH - 2) + 13);

      this.opticalCtx.restore();
    });
  }

  populateStripCarousel(regions) {
    this.stripCarousel.innerHTML = "";
    if (!regions || regions.length === 0) {
      this.stripCount.textContent = "0 TOKENS DETECTED";
      this.stripCarousel.innerHTML = `<div class="strip-empty-hint">No multi-sign sequence loaded</div>`;
      return;
    }

    this.stripCount.textContent = `${regions.length} TOKENS DETECTED`;

    regions.forEach((reg, idx) => {
      const card = document.createElement("div");
      card.className = "strip-card" + (idx === this.selectedRegionIdx ? " active" : "");
      card.innerHTML = `
        <span class="strip-badge">#${idx + 1}</span>
        <img class="strip-thumb" src="${reg.gradcam_heatmap || ''}" alt="Sign ${reg.predicted_sign}">
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
    if (!this.currentResponse || !this.currentResponse.regions[idx]) return;
    this.selectedRegionIdx = idx;
    const reg = this.currentResponse.regions[idx];

    // Highlight card
    const cards = this.stripCarousel.querySelectorAll(".strip-card");
    cards.forEach((c, i) => c.classList.toggle("active", i === idx));

    // Update Grad-CAM Image
    if (reg.gradcam_heatmap) {
      this.gradcamImg.src = reg.gradcam_heatmap;
      this.gradcamImg.style.display = "block";
      this.gradcamPlaceholder.style.display = "none";
    }

    // Update Signatures
    this.sigConf.textContent = `${(reg.confidence * 100).toFixed(1)}%`;
    this.sigMargin.textContent = `+${(reg.decision_margin * 100).toFixed(1)}%`;
    this.sigHandedness.textContent = reg.handedness ? reg.handedness.toUpperCase() : "ONE-HANDED";

    // Re-draw optical bounding box to highlight selected
    if (this.currentImage) {
      this.renderOpticalCanvas(this.currentImage, this.currentResponse.regions);
    }
  }

  speakTranslation() {
    if (!this.synth || !this.currentResponse) return;
    this.synth.cancel();

    const selectedLang = this.voiceSelect.value;
    const isHindi = selectedLang.startsWith("hi");
    const textToSpeak = isHindi 
      ? this.currentResponse.sentence.hindi_sentence 
      : this.currentResponse.sentence.english_sentence;

    if (!textToSpeak) return;

    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.lang = selectedLang;
    utterance.rate = parseFloat(this.rateSlider.value);
    utterance.pitch = parseFloat(this.pitchSlider.value);

    // Find suitable voice
    const targetVoice = this.availableVoices.find(v => v.lang === selectedLang || v.lang.startsWith(selectedLang));
    if (targetVoice) utterance.voice = targetVoice;

    utterance.onstart = () => {
      this.isSpeaking = true;
      this.ttsAudioStatus.textContent = `SYNTHESIZING [${selectedLang.toUpperCase()}]`;
      this.ttsAudioStatus.style.color = "#00ff9d";
    };

    utterance.onend = () => {
      this.isSpeaking = false;
      this.ttsAudioStatus.textContent = "STANDBY";
      this.ttsAudioStatus.style.color = "#00f0ff";
    };

    utterance.onerror = (e) => {
      console.warn("TTS error:", e);
      this.isSpeaking = false;
      this.ttsAudioStatus.textContent = "STANDBY";
    };

    this.synth.speak(utterance);
  }

  initWaveformVisualizer() {
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
          // Dynamic pulsing audio energy
          const wave1 = Math.sin(phase * 0.15 + i * 0.4);
          const wave2 = Math.cos(phase * 0.22 - i * 0.3);
          const energy = Math.abs(wave1 * wave2);
          height = Math.max(6, energy * (canvas.height - 12) + 4);
        } else {
          // Low standby resting hum
          height = Math.max(3, Math.sin(phase * 0.03 + i * 0.2) * 4 + 4);
        }

        const x = i * (barWidth + 2);
        const y = canvas.height - height;

        // Gradient bar
        const grad = ctx.createLinearGradient(0, y, 0, canvas.height);
        grad.addColorStop(0, this.isSpeaking ? "#00ff9d" : "#00f0ff");
        grad.addColorStop(1, "rgba(0, 240, 255, 0.15)");

        ctx.fillStyle = grad;
        ctx.fillRect(x, y, barWidth, height);

        // Peak cap
        ctx.fillStyle = this.isSpeaking ? "#ffffff" : "#00f0ff";
        ctx.fillRect(x, Math.max(0, y - 2), barWidth, 1.5);
      }

      phase += 1;
      this.animationFrameId = requestAnimationFrame(render);
    };

    render();
  }

  async openMetricsModal() {
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

      // Force refresh images
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
      const res = await fetch("/api/learn", {
        method: "POST",
        body: formData
      });
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

  async loadVocabularyDatalist() {
    try {
      const res = await fetch("/api/vocabulary");
      if (!res.ok) return;
      const data = await res.json();
      if (!this.knownSignsList) return;
      this.knownSignsList.innerHTML = "";
      
      const allSigns = [...(data.alphanumeric || []), ...(data.words || [])];
      allSigns.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s;
        this.knownSignsList.appendChild(opt);
      });
    } catch (e) {
      console.warn("Could not load vocabulary datalist:", e);
    }
  }

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

      this.showToast(`★ MODEL REWARDED: Gesture [${reg.predicted_sign}] confirmed & reinforced in neural memory.`, "success");
      this.refreshPrototypeCount();
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

      // Update current region locally with the corrected prediction
      reg.predicted_sign = correctSign;
      if (data.updated_prediction) {
        Object.assign(reg, data.updated_prediction);
      }

      // Re-render carousel and selections
      this.populateStripCarousel(this.currentResponse.regions);
      this.selectRegion(this.selectedRegionIdx);

      // Update full sentence translations
      if (data.updated_sentence) {
        this.currentResponse.sentence = data.updated_sentence;
        this.transEnglish.textContent = data.updated_sentence.english_sentence;
        this.transHindi.textContent = data.updated_sentence.hindi_sentence;
      }
      if (data.updated_speech) {
        this.currentResponse.speech = data.updated_speech;
      }

      this.correctionStatus.textContent = `✓ Severe penalty applied to '${data.previous_sign}'. Prototype registered for '${data.corrected_sign}'. Instant online learning complete!`;
      this.correctionStatus.className = "correction-status success";
      this.showToast(`⚡ MODEL ADAPTED: Penalized '${data.previous_sign}' and reinforced '${data.corrected_sign}'. Model improves without retraining!`, "success");
      
      this.refreshPrototypeCount();
      // Speak newly learned sign
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

  showToast(message, type = "info") {
    console.log(`[TOAST ${type.toUpperCase()}]`, message);
    const toast = document.createElement("div");
    toast.className = `hud-toast toast-${type}`;
    toast.style.cssText = `
      position: fixed;
      bottom: 45px;
      right: 25px;
      background: ${type === 'success' ? 'rgba(16, 185, 129, 0.95)' : 'rgba(239, 68, 68, 0.95)'};
      color: #fff;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
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

  async refreshPrototypeCount() {
    await this.checkHealth();
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
    this.opticalCtx.clearRect(0, 0, this.opticalCanvas.width, this.opticalCanvas.height);
    this.opticalPlaceholder.style.display = "flex";
    this.gradcamImg.src = "";
    this.gradcamImg.style.display = "none";
    this.gradcamPlaceholder.style.display = "flex";
    this.stripCarousel.innerHTML = `<div class="strip-empty-hint">No multi-sign sequence loaded</div>`;
    this.stripCount.textContent = "0 TOKENS DETECTED";
    this.transEnglish.textContent = "Awaiting input gesture...";
    this.transHindi.textContent = "अनुवाद की प्रतीक्षा...";
    this.transPhonetic.textContent = "Phonetic: --";
    this.sigConf.textContent = "--%";
    this.sigMargin.textContent = "--";
    this.sigHandedness.textContent = "--";
    this.telemetryLatency.textContent = "-- ms";
  }
}

// Initialize on DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  window.astraApp = new AstraVisionApp();
});

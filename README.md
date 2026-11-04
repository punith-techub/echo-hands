# ECHOHANDS 5.0 // ASTRA-VISION TACTICAL NEURAL HUD
**Real-Time Indian Sign Language (ISL) to Voice & Live 3D Sign Avatar Meeting Translator (Phase-3)**

ECHOHANDS is an end-to-end assistive neural system and Manifest V3 Chrome Extension designed for bidirectional communication between Deaf/Mute individuals and Hearing individuals in online video meetings (Google Meet, Zoom, Microsoft Teams, and WebRTC calls).

- **Deaf / Mute User Signs ISL $\longrightarrow$ Hearing User Hears Real Voice**: Converts Indian Sign Language gestures in real time into fluent English and Hindi speech, voiced aloud over the meeting call.
- **Hearing User Speaks Voice $\longrightarrow$ Deaf / Mute User Sees Live 3D Animated Signs**: Continuously transcribes spoken voice and renders a real-time, rigged 3D WebGL Avatar performing Indian Sign Language gestures and finger-spelling directly on screen!

---

## Key Capabilities (Phase-1 to Phase-3)

1. **Manifest V3 Chrome Extension & Video Call Detector**:
   - Detects when the user opens Google Meet (`meet.google.com`), Zoom (`zoom.us`), Microsoft Teams, or WebRTC calls.
   - Spawns the floating **ASTRA-VISION Tactical Meeting HUD** with live draggable controls, mode switching, and real-time captions.

2. **Rigged 3D WebGL ISL Avatar (`extension/avatar.js`)**:
   - Built with Three.js; features articulated shoulders, elbows, wrists, and 10 individually articulated finger joints.
   - Smooth co-articulation animation blending across 35 alphanumerics (A–Z, 1–9) and core ISL words (`NAMASTE`, `HELLO`, `THANK_YOU`, `HELP`, `FOOD`, `WATER`, `DOCTOR`, `WANT`, `YES`, `NO`, `PLEASE`, `SORRY`, etc.).
   - Organic breathing dynamics and adjustable animation speed (0.8x, 1.0x, 1.4x).

3. **Bidirectional Grammar & Reverse Gloss Compiler (`CORE/sentence_synthesizer.py`)**:
   - **Forward**: Transforms ISL Subject-Object-Verb (SOV) signs to natural English Subject-Verb-Object (SVO) and Hindi sentences (`['I', 'FOOD', 'WANT']` → `"I want food."` / `"मुझे खाना चाहिए।"`).
   - **Reverse**: Compiles spoken English/Hindi sentences into ordered ISL Gloss tokens and finger-spelling sequences for the 3D Avatar.

4. **Zero-Latency Web Speech & Peer-to-Peer Synchronization (`extension/peer_sync.js`)**:
   - Web Speech Synthesis (TTS) with native `en-IN` (Indian English) and `hi-IN` (Hindi) voice routing.
   - Continuous Web Speech Recognition (STT) for the hearing participant.
   - Zero-latency synchronization across browser tabs and video calls via BroadcastChannel & WebRTC.

5. **ASTRA-MEET Virtual Meeting Simulator (`/simulator`)**:
   - Split-screen live call simulator accessible directly from the browser/Vercel URL to test both directions instantly without opening external apps.

6. **Dual-Brain Hybrid Neural Architecture & Continuous Learning**:
   - Alphanumeric CNN Backbone (Brain 1) + Continuous Prototype Vector Memory (Brain 2) with negative punishment/reward online learning.
   - Cloud LLM verification arbiter with zero-context-loss fallback (Groq, Gemini, OpenAI).

---

## Directory Structure

```
ECHOHANDS/
├── api/
│   └── index.py                # Vercel serverless cloud entrypoint
├── extension/                  # Manifest V3 Chrome Extension
│   ├── manifest.json           # Chrome MV3 configuration & permissions
│   ├── background.js           # Background service worker & tab meeting tracker
│   ├── content.js              # Meeting injection & tactical HUD manager
│   ├── hud.css                 # Military tactical floating HUD styling
│   ├── avatar.js               # Rigged 3D Three.js humanoid ISL Avatar
│   ├── isl_engine.js           # Client-side kinematics, STT/TTS & grammar compiler
│   ├── peer_sync.js            # BroadcastChannel & WebRTC meeting sync
│   ├── popup.html / js / css   # Extension action toolbar popup
│   ├── libs/three.min.js       # Bundled Three.js (CSP compliant, zero CDN lag)
│   └── icons/                  # Crisp tactical cyan extension icons (16, 48, 128)
├── CORE/
│   ├── sign_knowledge.py       # 35 Alphanumerics + 60+ ISL Words metadata
│   ├── model_arch.py           # ISLNet Residual CNN with 512D neck
│   ├── multi_sign_engine.py    # Skin segmentation, dual-hand merging & reading order
│   ├── sentence_synthesizer.py # Bidirectional fingerspelling & SOV/SVO compiler
│   ├── speech_engine.py        # Web Speech API orchestrator & phonetics
│   ├── isl_trainer.py          # Continuous prototype vector memory
│   ├── vision.py               # Dual-Brain Vision Engine & Grad-CAM
│   ├── train.py                # 80/20 Stratified benchmark training pipeline
│   └── app.py                  # FastAPI server & REST APIs
├── static/
│   ├── index.html              # ASTRA-VISION Tactical Cockpit & Download Center
│   ├── simulator.html          # ASTRA-MEET Live Dual Video Meeting Simulator
│   ├── styles.css              # Cyber-cockpit dark stylesheet
│   └── app.js                  # Frontend HUD telemetry controller
├── models/                     # Trained weights, memory file, confusion matrix, ROC
├── tests/                      # Full 107-test suite (100% pass)
├── requirements.txt            # Lightweight Vercel serverless requirements
├── requirements-dev.txt        # Full local PyTorch & training requirements
├── vercel.json                 # Vercel cloud deployment routing
├── main.py                     # Local server launcher
└── README.md                   # Documentation
```

---

## How to Install the Chrome Extension

1. **Download the Extension**:
   - Open your deployed Vercel link (or `http://localhost:8000`) and click **"DOWNLOAD EXTENSION (.ZIP)"** (or use the `/extension` folder directly from this repo).
   - Extract the `.zip` file into a local folder.
2. **Load into Google Chrome**:
   - Open Google Chrome and navigate to: `chrome://extensions/`
   - In the top-right corner, toggle **Developer mode** to **ON**.
   - Click the **"Load unpacked"** button in the top-left corner.
   - Select the `extension/` directory.
3. **Join a Meeting**:
   - Open [Google Meet](https://meet.google.com/), Zoom Web, or the built-in [ASTRA-MEET Simulator](http://localhost:8000/simulator).
   - The **ASTRA-VISION Meeting HUD** will automatically spawn in the call!

---

## How to Deploy on Vercel

1. Push your repository to **GitHub**:
   ```bash
   git add .
   git commit -m "feat: ECHOHANDS Phase-3 Chrome Extension & 3D ISL Avatar"
   git push origin main
   ```
2. Log into **[Vercel](https://vercel.com/)** and click **"Add New Project"** $\rightarrow$ Import your GitHub repo.
3. In **Environment Variables**, add:
   - `GROQ_API_KEY`: *(Optional)* Your Groq API key for cloud LLM verification.
   - `GEMINI_API_KEY`: *(Optional)* Your Google Gemini API key.
   - `OPENAI_API_KEY`: *(Optional)* Your OpenAI key.
4. Click **Deploy**. Vercel will build and deploy your site in seconds!
5. Users can now visit your Vercel URL, click **Download Chrome Extension**, and use the built-in **ASTRA-MEET Simulator** or Google Meet.

---

## Local Development & Testing

### 1. Launch Server
```bash
python main.py
```
Open `http://localhost:8000` for the HUD or `http://localhost:8000/simulator` for the meeting simulator.

### 2. Run Test Suite
```bash
python -m pytest tests -v
```
*Result: 107 passed in ~2 minutes (100% pass rate).*


```
ECHOHANDS/
├── CORE/
│   ├── __init__.py
│   ├── sign_knowledge.py       # 35 Alphanumerics + 60+ ISL Words metadata
│   ├── model_arch.py           # ISLNet Residual CNN with 512D neck
│   ├── multi_sign_engine.py    # Skin segmentation, dual-hand merging & reading order
│   ├── sentence_synthesizer.py # Fingerspelling aggregator & ISL SOV smoothing
│   ├── speech_engine.py        # Web Speech API metadata & phonetic generator
│   ├── isl_trainer.py          # Continuous prototype vector memory
│   ├── vision.py               # Dual-Brain Vision Engine & Grad-CAM
│   ├── train.py                # 80/20 Stratified benchmark training pipeline
│   ├── generate_sample_data.py # Sample test generator for letters, words & strips
│   └── app.py                  # FastAPI server & REST API endpoints
├── data/                       # Benchmark sample images (single, words, strips)
├── models/                     # Trained weights, memory file, confusion matrix, ROC
├── static/                     # ASTRA-VISION 5.0 Tactical Dark HUD
│   ├── index.html              # 100% viewport contained HTML5 cockpit
│   ├── styles.css              # Stealth military theme stylesheet
│   └── app.js                  # Audio waveform, canvas HUD & API controller
├── tests/                      # Pytest test suite (50 test cases, 100% pass)
├── main.py                     # Root server launcher
└── README.md                   # Documentation
```

---

## Quick Start

### 1. Launch Web Server
```bash
python main.py
```
Open your browser at `http://localhost:8000`.

### 2. Run Test Suite
```bash
python -m pytest tests -v
```

### 3. Re-run Training Benchmark
```bash
python -m CORE.train --epochs 10 --samples 60
```

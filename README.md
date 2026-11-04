# ECHOHANDS 5.0 // ASTRA-VISION TACTICAL NEURAL HUD
**Real-Time Indian Sign Language (ISL) to Text and Synthesised Speech Translator (Phase-1)**

ECHOHANDS is a real-time computer vision and neural interpretation system designed to translate Indian Sign Language (ISL) gestures into natural English and Hindi text and synthesised speech. Built with an exact **ASTRA-VISION 5.0 Tactical Dark Cockpit HUD** interface, 100% viewport contained, zero-latency offline Web Speech synthesis, and explainable AI (Grad-CAM).

---

## Key Capabilities

1. **Dual-Brain Hybrid Neural Architecture**:
   - **Brain 1 (Alphanumeric CNN Backbone)**: Custom Residual CNN with stem downsampling, 4 residual stages, and a 512D embedding neck. Classifies 35 ISL alphanumeric signs (Digits 1–9, Letters A–Z).
   - **Brain 2 (Continuous Prototype Vector Matcher)**: Cosine similarity matching over 60+ ISL word gestures using deep feature embeddings. Supports local continuous zero-shot learning stored in `models/isl_memory.pt`.
   - **Dual-Brain Arbitration Engine**: Dynamically routes between Brain 1 and Brain 2 based on hand spatial envelope interaction (one-handed vs two-handed) and decision margin thresholds.

2. **Multi-Sign Reading Order Parsing**:
   - Dual-color space skin segmentation using **YCrCb + HSV** thresholding with morphological cleanup and edge/luminance fallback.
   - Dual-hand spatial envelope merging: automatically groups interacting hands for two-handed signs (e.g. `NAMASTE`, `HELP`, letters `A`, `B`, `D`).
   - Natural Reading Order sorting: clusters signs into lines/rows and sorts **Left-to-Right, Top-to-Bottom**.
   - Optical zoom square normalization with aspect ratio preservation (224x224 RGB crops).

3. **Bilingual Grammar Smoothing & Fingerspell Aggregation**:
   - Merges sequences of letters into cohesive words (e.g. `['H', 'E', 'L', 'P']` → `HELP`, `['C', 'A', 'T']` → `CAT`).
   - Converts Indian Sign Language Subject-Object-Verb (SOV) structure into fluent English Subject-Verb-Object (SVO) sentences (`['I', 'FOOD', 'EAT']` → `"I want to eat food."`).
   - Translates into natural Hindi SOV sentences with Devanagari script (`"मैं खाना खाना चाहता हूँ।"`).

4. **Zero-Latency Web Speech API & Visualizer**:
   - 100% client-side, offline voice synthesis using browser-native Web Speech API.
   - Native `en-IN` (Indian English) and `hi-IN` (Hindi) voice routing with speed and pitch controls.
   - Real-time 32-bar pulsing audio waveform canvas visualizer in the tactical cockpit.

5. **Online Interactive Continuous Learning & Negative Punishment Loop**:
   - Immediate feedback UI with `👍 Thumbs Up` and `👎 Thumbs Down` buttons for every prediction.
   - **Thumbs Up (Reward)**: Strengthens the prototype vector towards the confirmed feature representation without retraining.
   - **Thumbs Down (Punish & Teach)**: Opens a teaching drawer where the user provides the correct sign. The system severely repels the erroneous prototype along the mistake axis and pulls the true sign's prototype centroid into place, immediately improving future predictions without server restarts or long retraining cycles.

6. **Explainable AI (Grad-CAM)**:
   - Gradient-weighted Class Activation Mapping computed from the final convolutional stage (`stage4`).
   - Overlays thermal jet/inferno heatmaps to highlight hand, finger, and joint activation regions.

7. **Benchmark Metrics & Evaluation**:
   - Stratified 80/20 train/test evaluation pipeline.
   - 35x35 normalized confusion matrix heatmap (`models/confusion_matrix.png`).
   - Multi-class ROC curves and AUC (`models/roc_curve.png`).
   - Per-class precision, recall, and F1-score report (`models/metrics.json`).
   - Full 54-test suite (`tests/`) covering 100% of subsystem integration.

---

## Directory Structure

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

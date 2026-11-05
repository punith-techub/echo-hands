/**
 * ECHO-HANDS // Realistic Humanoid Indian Sign Language (ISL) Avatar Engine
 * Renders large, high-contrast, fully-articulated human hands with multi-phalanx fingers,
 * paired with real-time authentic ISL hand anatomy vector graphic illustrations.
 */

class ISL3DAvatar {
  constructor(canvasContainer) {
    this.container = canvasContainer;
    this.width = canvasContainer.clientWidth || 320;
    this.height = canvasContainer.clientHeight || 320;
    
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.joints = {};
    this.animationQueue = [];
    this.currentSign = "IDLE";
    this.isPlaying = false;
    this.speedMultiplier = 1.0;
    this.clock = new THREE.Clock();

    // Default neutral ready pose
    this.defaultPose = {
      head: { x: 0, y: 0, z: 0 },
      chest: { x: 0, y: 0, z: 0 },
      leftShoulder: { x: 0.1, y: 0, z: -0.2 },
      leftElbow: { x: 0.3, y: 0, z: 0.4 },
      leftWrist: { x: 0, y: 0, z: 0 },
      rightShoulder: { x: 0.1, y: 0, z: 0.2 },
      rightElbow: { x: 0.3, y: 0, z: -0.4 },
      rightWrist: { x: 0, y: 0, z: 0 },
      leftFingers: [0, 0, 0, 0, 0], // Curl values 0 (open) to 1 (closed)
      rightFingers: [0, 0, 0, 0, 0]
    };

    this.currentPose = JSON.parse(JSON.stringify(this.defaultPose));
    this.targetPose = JSON.parse(JSON.stringify(this.defaultPose));
    this.poseTransitionTime = 0.25;
    this.poseTransitionProgress = 1.0;

    this.initScene();
    this.buildAvatarRig();
    this.initRealHandCard();
    this.startLoop();
  }

  initScene() {
    this.scene = new THREE.Scene();
    // Camera positioned closer to emphasize hands and upper torso
    this.camera = new THREE.PerspectiveCamera(38, this.width / this.height, 0.1, 100);
    this.camera.position.set(0, 0.20, 1.85);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(this.width, this.height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setClearColor(0x060c11, 0.85);
    this.container.appendChild(this.renderer.domElement);

    // Dynamic 4-point tactical lighting for high-definition finger contrast
    const ambientLight = new THREE.AmbientLight(0x506575, 1.4);
    this.scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0x00e6b4, 2.2);
    keyLight.position.set(2, 2.5, 2);
    this.scene.add(keyLight);

    const warmLight = new THREE.DirectionalLight(0xffecd2, 1.8);
    warmLight.position.set(-1.5, 2, 2);
    this.scene.add(warmLight);

    const backLight = new THREE.PointLight(0x00ffcc, 1.6, 6);
    backLight.position.set(0, 0.5, -1);
    this.scene.add(backLight);

    window.addEventListener("resize", () => {
      if (!this.container) return;
      const w = this.container.clientWidth;
      const h = this.container.clientHeight;
      if (w > 0 && h > 0) {
        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(w, h);
      }
    });
  }

  buildAvatarRig() {
    const armorMat = new THREE.MeshStandardMaterial({
      color: 0x142028,
      roughness: 0.35,
      metalness: 0.7
    });

    const glowJointMat = new THREE.MeshStandardMaterial({
      color: 0x00e6b4,
      emissive: 0x008866,
      emissiveIntensity: 0.7,
      roughness: 0.2
    });

    // Realistic high-contrast human skin tone
    const skinMat = new THREE.MeshStandardMaterial({
      color: 0xf5b894, // Warm natural human skin
      roughness: 0.5,
      metalness: 0.1
    });

    const palmHighlightMat = new THREE.MeshStandardMaterial({
      color: 0xfedac3, // Slightly lighter inner palm
      roughness: 0.6
    });

    // Root Group
    const root = new THREE.Group();
    root.position.set(0, -0.65, 0);
    this.scene.add(root);
    this.joints.root = root;

    // Torso / Chest
    const torsoGeo = new THREE.BoxGeometry(0.54, 0.62, 0.28);
    const torso = new THREE.Mesh(torsoGeo, armorMat);
    torso.position.set(0, 0.5, 0);
    root.add(torso);
    this.joints.torso = torso;

    // Glowing core reactor
    const core = new THREE.Mesh(
      new THREE.CylinderGeometry(0.08, 0.08, 0.02, 16),
      glowJointMat
    );
    core.rotation.x = Math.PI / 2;
    core.position.set(0, 0.12, 0.15);
    torso.add(core);

    // Neck
    const neck = new THREE.Group();
    neck.position.set(0, 0.35, 0);
    torso.add(neck);
    this.joints.neck = neck;

    // Head
    const headGeo = new THREE.SphereGeometry(0.18, 24, 24);
    headGeo.scale(1.0, 1.2, 1.05);
    const head = new THREE.Mesh(headGeo, skinMat);
    head.position.set(0, 0.18, 0);
    neck.add(head);
    this.joints.head = head;

    // Visor strip
    const visorGeo = new THREE.BoxGeometry(0.24, 0.04, 0.08);
    const visor = new THREE.Mesh(visorGeo, glowJointMat);
    visor.position.set(0, 0.05, 0.16);
    head.add(visor);
    this.joints.visor = visor;

    // Left Arm Chain
    this.joints.leftShoulder = this.createArmChain(torso, -1, armorMat, glowJointMat, skinMat, palmHighlightMat);
    // Right Arm Chain
    this.joints.rightShoulder = this.createArmChain(torso, 1, armorMat, glowJointMat, skinMat, palmHighlightMat);
  }

  createArmChain(torso, side, armorMat, jointMat, skinMat, palmMat) {
    const isLeft = side < 0;
    const prefix = isLeft ? "left" : "right";

    // Shoulder joint
    const shoulder = new THREE.Group();
    shoulder.position.set(side * 0.34, 0.24, 0);
    torso.add(shoulder);

    const shoulderBall = new THREE.Mesh(new THREE.SphereGeometry(0.085, 16, 16), jointMat);
    shoulder.add(shoulderBall);

    // Upper arm
    const upperArm = new THREE.Group();
    shoulder.add(upperArm);

    const bicep = new THREE.Mesh(new THREE.CylinderGeometry(0.065, 0.055, 0.34, 12), armorMat);
    bicep.position.set(0, -0.17, 0);
    upperArm.add(bicep);

    // Elbow
    const elbow = new THREE.Group();
    elbow.position.set(0, -0.34, 0);
    upperArm.add(elbow);
    this.joints[`${prefix}ElbowGroup`] = elbow;

    const elbowBall = new THREE.Mesh(new THREE.SphereGeometry(0.065, 16, 16), jointMat);
    elbow.add(elbowBall);

    // Forearm
    const forearm = new THREE.Group();
    elbow.add(forearm);

    const forearmMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.05, 0.32, 12), armorMat);
    forearmMesh.position.set(0, -0.16, 0);
    forearm.add(forearmMesh);

    // Wrist
    const wrist = new THREE.Group();
    wrist.position.set(0, -0.32, 0);
    forearm.add(wrist);
    this.joints[`${prefix}WristGroup`] = wrist;

    const wristBall = new THREE.Mesh(new THREE.SphereGeometry(0.05, 12, 12), jointMat);
    wrist.add(wristBall);

    // LARGE, ARTICULATED REALISTIC HUMAN HAND & PALM (2.2x larger for crystal-clear signing)
    const palmGroup = new THREE.Group();
    palmGroup.position.set(0, -0.06, 0);
    wrist.add(palmGroup);

    // Palm base
    const palmGeo = new THREE.BoxGeometry(0.16, 0.18, 0.05);
    const palm = new THREE.Mesh(palmGeo, skinMat);
    palm.position.set(0, -0.08, 0);
    palmGroup.add(palm);

    // Palm inner face highlight
    const palmFace = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.16, 0.01), palmMat);
    palmFace.position.set(0, -0.08, 0.026);
    palmGroup.add(palmFace);

    // 5 HIGH-DEFINITION 2-SEGMENT ARTICULATED FINGERS
    const fingers = [];
    const fingerConfigs = [
      { name: "thumb", x: isLeft ? 0.09 : -0.09, y: -0.04, len1: 0.07, len2: 0.05, r: 0.022, angle: isLeft ? 0.5 : -0.5 },
      { name: "index", x: isLeft ? 0.05 : -0.05, y: -0.17, len1: 0.08, len2: 0.06, r: 0.020, angle: 0 },
      { name: "middle", x: isLeft ? 0.015 : -0.015, y: -0.175, len1: 0.09, len2: 0.065, r: 0.020, angle: 0 },
      { name: "ring", x: isLeft ? -0.02 : 0.02, y: -0.17, len1: 0.08, len2: 0.055, r: 0.019, angle: 0 },
      { name: "pinky", x: isLeft ? -0.055 : 0.055, y: -0.16, len1: 0.065, len2: 0.045, r: 0.017, angle: isLeft ? -0.1 : 0.1 }
    ];

    for (let f = 0; f < 5; f++) {
      const cfg = fingerConfigs[f];

      // Proximal joint (base knuckle)
      const fBase = new THREE.Group();
      fBase.position.set(cfg.x, cfg.y, 0);
      fBase.rotation.z = cfg.angle;
      palmGroup.add(fBase);

      // Knuckle ball
      const knuckle = new THREE.Mesh(new THREE.SphereGeometry(cfg.r * 1.1, 10, 10), skinMat);
      fBase.add(knuckle);

      // Proximal phalanx (segment 1)
      const seg1 = new THREE.Mesh(new THREE.CylinderGeometry(cfg.r, cfg.r * 0.9, cfg.len1, 10), skinMat);
      seg1.position.set(0, -cfg.len1 / 2, 0);
      fBase.add(seg1);

      // Distal joint (segment 2)
      const fDistal = new THREE.Group();
      fDistal.position.set(0, -cfg.len1, 0);
      fBase.add(fDistal);

      const midJoint = new THREE.Mesh(new THREE.SphereGeometry(cfg.r * 0.95, 8, 8), skinMat);
      fDistal.add(midJoint);

      const seg2 = new THREE.Mesh(new THREE.CylinderGeometry(cfg.r * 0.88, cfg.r * 0.75, cfg.len2, 10), skinMat);
      seg2.position.set(0, -cfg.len2 / 2, 0);
      fDistal.add(seg2);

      fBase.distal = fDistal;
      fingers.push(fBase);
    }

    this.joints[`${prefix}Fingers`] = fingers;
    return shoulder;
  }

  initRealHandCard() {
    if (!this.container) return;
    let card = document.getElementById("eh-real-hand-card");
    if (!card) {
      card = document.createElement("div");
      card.id = "eh-real-hand-card";
      card.className = "eh-real-hand-card";
      card.innerHTML = `
        <div class="eh-hand-svg-wrap" id="eh-hand-svg-wrap">
          <svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="38" fill="none" stroke="#00e6b4" stroke-width="6"/><path d="M50 25 L50 55 L70 55" fill="none" stroke="#00e6b4" stroke-width="6" stroke-linecap="round"/></svg>
        </div>
        <div class="eh-hand-info">
          <div class="eh-hand-sign-name" id="eh-hand-sign-name">ISL AVATAR: READY</div>
          <div class="eh-hand-sign-desc" id="eh-hand-sign-desc">Speak or type to generate signs</div>
        </div>
      `;
      this.container.appendChild(card);
    }
  }

  updateRealHandCard(signToken) {
    const nameEl = document.getElementById("eh-hand-sign-name");
    const descEl = document.getElementById("eh-hand-sign-desc");
    const svgWrap = document.getElementById("eh-hand-svg-wrap");

    const info = this.getHandGraphicData(signToken);
    if (nameEl) nameEl.textContent = info.name;
    if (descEl) descEl.textContent = info.desc;
    if (svgWrap) svgWrap.innerHTML = info.svg;
  }

  getHandGraphicData(token) {
    const s = (token || "READY").toUpperCase();

    // 1. Common Words
    if (s === "NAMASTE") {
      return {
        name: "NAMASTE // [TWO-HANDED ISL]",
        desc: "Both open human palms pressed flat together at chest level in prayer",
        svg: `<svg viewBox="0 0 100 100"><path d="M44 85 C44 55 42 35 46 15 C48 10 50 10 50 15 L50 85 Z" fill="#00ffcc"/><path d="M56 85 C56 55 58 35 54 15 C52 10 50 10 50 15 L50 85 Z" fill="#00e6b4"/><circle cx="50" cy="50" r="44" fill="none" stroke="#00ffcc" stroke-width="3" stroke-dasharray="4 4"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED</text></svg>`
      };
    }
    if (s === "HELP") {
      return {
        name: "HELP // [TWO-HANDED ISL]",
        desc: "Flat open left palm supporting right thumbs-up fist lifting together",
        svg: `<svg viewBox="0 0 100 100"><rect x="15" y="75" width="70" height="14" rx="7" fill="#00e6b4"/><rect x="35" y="40" width="30" height="30" rx="8" fill="#00ffcc"/><path d="M50 40 L50 18 Q50 10 58 10 Q65 10 65 20 L65 40 Z" fill="#00ffcc"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED</text></svg>`
      };
    }
    if (s === "STOP") {
      return {
        name: "STOP // [TWO-HANDED ISL]",
        desc: "Right hand chops down vertically onto flat horizontal left palm",
        svg: `<svg viewBox="0 0 100 100"><rect x="15" y="70" width="70" height="14" rx="7" fill="#00e6b4"/><rect x="42" y="15" width="16" height="52" rx="6" fill="#00ffcc"/><path d="M50 68 L50 78" stroke="#041014" stroke-width="4"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED</text></svg>`
      };
    }
    if (s === "WELCOME") {
      return {
        name: "WELCOME // [TWO-HANDED ISL]",
        desc: "Both open palms facing up sweeping inward toward body",
        svg: `<svg viewBox="0 0 100 100"><path d="M15 65 Q35 75 50 60" stroke="#00e6b4" stroke-width="8" fill="none" stroke-linecap="round"/><path d="M85 65 Q65 75 50 60" stroke="#00ffcc" stroke-width="8" fill="none" stroke-linecap="round"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED</text></svg>`
      };
    }
    if (s === "FRIEND") {
      return {
        name: "FRIEND // [TWO-HANDED ISL]",
        desc: "Curved index fingers of both hands hooked into each other",
        svg: `<svg viewBox="0 0 100 100"><circle cx="40" cy="50" r="18" fill="none" stroke="#00e6b4" stroke-width="8"/><circle cx="60" cy="50" r="18" fill="none" stroke="#00ffcc" stroke-width="8"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED</text></svg>`
      };
    }
    if (s === "THANK_YOU" || s === "THANK") {
      return {
        name: "THANK YOU // [CHIN SWEEP]",
        desc: "Fingertips touch chin and open palm sweeps forward towards recipient",
        svg: `<svg viewBox="0 0 100 100"><circle cx="50" cy="22" r="12" fill="#00e6b4"/><path d="M50 34 Q50 65 75 75" stroke="#00ffcc" stroke-width="8" fill="none" stroke-linecap="round"/><polygon points="75,70 85,78 72,82" fill="#00ffcc"/></svg>`
      };
    }
    if (s === "WATER" || s === "DRINK") {
      return {
        name: "WATER // [3-FINGER 'W']",
        desc: "Index, middle, and ring fingers upright (W) tapping chin",
        svg: `<svg viewBox="0 0 100 100"><rect x="30" y="60" width="40" height="30" rx="10" fill="#00e6b4"/><rect x="30" y="20" width="10" height="45" rx="5" fill="#00ffcc"/><rect x="45" y="15" width="10" height="50" rx="5" fill="#00ffcc"/><rect x="60" y="20" width="10" height="45" rx="5" fill="#00ffcc"/></svg>`
      };
    }
    if (s === "FOOD" || s === "EAT") {
      return {
        name: "FOOD // [CLUSTER TO MOUTH]",
        desc: "Fingertips clustered together moving repeatedly to mouth",
        svg: `<svg viewBox="0 0 100 100"><path d="M50 20 C35 35 30 60 35 80 C45 88 55 88 65 80 C70 60 65 35 50 20 Z" fill="#00ffcc"/><circle cx="50" cy="20" r="10" fill="#00e6b4"/></svg>`
      };
    }
    if (s === "YES") {
      return {
        name: "YES // [NODDING FIST]",
        desc: "Closed fist nodding vertically up and down at wrist",
        svg: `<svg viewBox="0 0 100 100"><rect x="30" y="30" width="40" height="40" rx="12" fill="#00ffcc"/><path d="M50 15 L50 25 M42 20 L50 15 L58 20" stroke="#00e6b4" stroke-width="5" fill="none" stroke-linecap="round"/><path d="M50 85 L50 75 M42 80 L50 85 L58 80" stroke="#00e6b4" stroke-width="5" fill="none" stroke-linecap="round"/></svg>`
      };
    }
    if (s === "NO") {
      return {
        name: "NO // [INDEX WAG]",
        desc: "Upright index finger waving left and right firmly",
        svg: `<svg viewBox="0 0 100 100"><rect x="30" y="55" width="40" height="35" rx="8" fill="#00e6b4"/><rect x="45" y="15" width="12" height="48" rx="6" fill="#00ffcc"/><path d="M25 35 L75 35" stroke="#00ffcc" stroke-width="4" stroke-linecap="round" stroke-dasharray="6 4"/></svg>`
      };
    }
    if (s === "DOCTOR") {
      return {
        name: "DOCTOR // [TWO-HANDED ISL]",
        desc: "Right fingertips tap inner pulse point of left wrist twice",
        svg: `<svg viewBox="0 0 100 100"><rect x="15" y="60" width="40" height="20" rx="6" fill="#00e6b4"/><rect x="45" y="25" width="14" height="45" rx="6" fill="#00ffcc"/><circle cx="40" cy="70" r="5" fill="#ff4d4d"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED</text></svg>`
      };
    }

    // 2. ISL Alphabet (A-Z)
    if (s === "A") {
      return {
        name: "A // [TWO-HANDED ISL]",
        desc: "Left hand open palm; Right index touches tip of left thumb",
        svg: `<svg viewBox="0 0 100 100"><rect x="18" y="45" width="35" height="40" rx="8" fill="#00e6b4"/><rect x="12" y="30" width="10" height="25" rx="5" fill="#00e6b4"/><rect x="48" y="20" width="12" height="48" rx="6" fill="#00ffcc"/><circle cx="20" cy="30" r="7" fill="#ffdd55"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }
    if (s === "B") {
      return {
        name: "B // [TWO-HANDED ISL]",
        desc: "Both hands form circles with thumb and index touching (twin B loops)",
        svg: `<svg viewBox="0 0 100 100"><circle cx="34" cy="48" r="18" fill="none" stroke="#00e6b4" stroke-width="8"/><circle cx="66" cy="48" r="18" fill="none" stroke="#00ffcc" stroke-width="8"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }
    if (s === "C") {
      return {
        name: "C // [ONE-HANDED ISL]",
        desc: "Right hand fingers and thumb curved into an open C arc profile",
        svg: `<svg viewBox="0 0 100 100"><path d="M70 25 C35 20 25 45 25 55 C25 65 35 90 70 85 C75 85 75 75 70 75 C45 75 38 60 38 55 C38 50 45 35 70 35 C75 35 75 25 70 25 Z" fill="#00ffcc"/></svg>`
      };
    }
    if (s === "D") {
      return {
        name: "D // [TWO-HANDED ISL]",
        desc: "Left index points vertically UP; Right hand forms loop against it",
        svg: `<svg viewBox="0 0 100 100"><rect x="30" y="15" width="12" height="68" rx="6" fill="#00e6b4"/><path d="M42 25 C65 25 75 40 75 52 C75 64 65 75 42 75 Z" fill="#00ffcc"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }
    if (s === "E") {
      return {
        name: "E // [TWO-HANDED ISL]",
        desc: "Left hand open palm; Right index touches tip of left index finger",
        svg: `<svg viewBox="0 0 100 100"><rect x="22" y="45" width="30" height="40" rx="8" fill="#00e6b4"/><rect x="22" y="20" width="10" height="35" rx="5" fill="#00e6b4"/><rect x="48" y="20" width="12" height="50" rx="6" fill="#00ffcc"/><circle cx="30" cy="20" r="7" fill="#ffdd55"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }
    if (s === "F") {
      return {
        name: "F // [TWO-HANDED ISL]",
        desc: "Left index upright; Right index and middle cross across it horizontally",
        svg: `<svg viewBox="0 0 100 100"><rect x="35" y="15" width="12" height="70" rx="6" fill="#00e6b4"/><rect x="15" y="32" width="65" height="10" rx="5" fill="#00ffcc"/><rect x="15" y="48" width="55" height="10" rx="5" fill="#00ffcc"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }
    if (s === "G") {
      return {
        name: "G // [TWO-HANDED ISL]",
        desc: "Both hands in closed fists stacked vertically (right fist atop left fist)",
        svg: `<svg viewBox="0 0 100 100"><rect x="30" y="15" width="40" height="32" rx="10" fill="#00ffcc"/><rect x="30" y="52" width="40" height="32" rx="10" fill="#00e6b4"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }
    if (s === "H") {
      return {
        name: "H // [TWO-HANDED ISL]",
        desc: "Left hand flat horizontal palm; Right flat palm strokes across it",
        svg: `<svg viewBox="0 0 100 100"><rect x="15" y="50" width="60" height="20" rx="8" fill="#00e6b4"/><rect x="35" y="20" width="22" height="50" rx="8" fill="#00ffcc"/><path d="M25 35 L75 35" stroke="#ffdd55" stroke-width="4" stroke-linecap="round"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }
    if (s === "I") {
      return {
        name: "I // [TWO-HANDED ISL]",
        desc: "Left hand open palm; Right index touches tip of left middle finger",
        svg: `<svg viewBox="0 0 100 100"><rect x="22" y="45" width="30" height="40" rx="8" fill="#00e6b4"/><rect x="32" y="15" width="10" height="40" rx="5" fill="#00e6b4"/><rect x="52" y="15" width="12" height="50" rx="6" fill="#00ffcc"/><circle cx="37" cy="18" r="7" fill="#ffdd55"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }
    if (s === "L") {
      return {
        name: "L // [ONE-HANDED ISL]",
        desc: "Right thumb and index extended at 90-degree right angle forming L",
        svg: `<svg viewBox="0 0 100 100"><rect x="30" y="15" width="14" height="60" rx="7" fill="#00ffcc"/><rect x="30" y="60" width="45" height="14" rx="7" fill="#00ffcc"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">ONE-HANDED</text></svg>`
      };
    }
    if (s === "M") {
      return {
        name: "M // [TWO-HANDED ISL]",
        desc: "Left hand flat palm up; Right hand 3 fingers resting across left palm",
        svg: `<svg viewBox="0 0 100 100"><rect x="15" y="60" width="70" height="18" rx="8" fill="#00e6b4"/><rect x="30" y="25" width="10" height="45" rx="5" fill="#00ffcc"/><rect x="45" y="25" width="10" height="45" rx="5" fill="#00ffcc"/><rect x="60" y="25" width="10" height="45" rx="5" fill="#00ffcc"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }
    if (s === "N") {
      return {
        name: "N // [TWO-HANDED ISL]",
        desc: "Left hand flat palm up; Right hand 2 fingers resting across left palm",
        svg: `<svg viewBox="0 0 100 100"><rect x="15" y="60" width="70" height="18" rx="8" fill="#00e6b4"/><rect x="35" y="25" width="12" height="45" rx="6" fill="#00ffcc"/><rect x="53" y="25" width="12" height="45" rx="6" fill="#00ffcc"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }
    if (s === "P") {
      return {
        name: "P // [TWO-HANDED ISL]",
        desc: "Left index points vertically UP; Right thumb and index loop at top of it",
        svg: `<svg viewBox="0 0 100 100"><rect x="30" y="15" width="12" height="70" rx="6" fill="#00e6b4"/><circle cx="58" cy="32" r="18" fill="none" stroke="#00ffcc" stroke-width="8"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }
    if (s === "S") {
      return {
        name: "S // [TWO-HANDED ISL]",
        desc: "Little fingers (pinkies) of both hands hooked into each other",
        svg: `<svg viewBox="0 0 100 100"><circle cx="40" cy="50" r="14" fill="none" stroke="#00e6b4" stroke-width="8"/><circle cx="60" cy="50" r="14" fill="none" stroke="#00ffcc" stroke-width="8"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }
    if (s === "T") {
      return {
        name: "T // [TWO-HANDED ISL]",
        desc: "Left index upright; Right index touches side horizontally at midpoint",
        svg: `<svg viewBox="0 0 100 100"><rect x="35" y="15" width="12" height="70" rx="6" fill="#00e6b4"/><rect x="47" y="45" width="40" height="12" rx="6" fill="#00ffcc"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }
    if (s === "V") {
      return {
        name: "V // [PEACE V SIGN]",
        desc: "Right index and middle fingers spread in high V",
        svg: `<svg viewBox="0 0 100 100"><rect x="35" y="55" width="34" height="35" rx="10" fill="#00e6b4"/><path d="M42 58 L30 18 Q35 12 42 16 L48 58 Z" fill="#00ffcc"/><path d="M58 58 L70 18 Q65 12 58 16 L52 58 Z" fill="#00ffcc"/></svg>`
      };
    }
    if (s === "W") {
      return {
        name: "W // [3-FINGER TRIDENT]",
        desc: "Right index, middle, and ring spread in high W",
        svg: `<svg viewBox="0 0 100 100"><rect x="30" y="55" width="40" height="35" rx="10" fill="#00e6b4"/><rect x="28" y="18" width="10" height="45" rx="5" fill="#00ffcc"/><rect x="45" y="15" width="10" height="48" rx="5" fill="#00ffcc"/><rect x="62" y="18" width="10" height="45" rx="5" fill="#00ffcc"/></svg>`
      };
    }
    if (s === "X") {
      return {
        name: "X // [TWO-HANDED ISL]",
        desc: "Both index fingers extended and crossed horizontally forming an X",
        svg: `<svg viewBox="0 0 100 100"><line x1="20" y1="25" x2="80" y2="75" stroke="#00e6b4" stroke-width="12" stroke-linecap="round"/><line x1="20" y1="75" x2="80" y2="25" stroke="#00ffcc" stroke-width="12" stroke-linecap="round"/><text x="50" y="96" font-size="8" fill="#00ffcc" text-anchor="middle" font-weight="bold">TWO-HANDED ISL</text></svg>`
      };
    }

    // Generic letter fallback
    return {
      name: `${s} // [ISL FINGERSPELLING]`,
      desc: `Authentic Indian Sign Language letter ${s}`,
      svg: `<svg viewBox="0 0 100 100"><rect x="25" y="30" width="50" height="50" rx="12" fill="#00e6b4"/><circle cx="50" cy="55" r="20" fill="#041014"/><text x="50" y="65" font-size="28" font-weight="bold" fill="#00ffcc" text-anchor="middle">${s}</text></svg>`
    };
  }

  // Set 3D target pose for gesture
  setPose(pose, transitionTime = 0.25) {
    if (this.joints.torso) {
      this.joints.torso.position.z = 0.04;
    }
    if (this.joints.neck) {
      this.joints.neck.rotation.x = 0.12;
    }
    this.targetPose = JSON.parse(JSON.stringify(pose));
    this.poseTransitionTime = Math.max(0.08, transitionTime / this.speedMultiplier);
    this.poseTransitionProgress = 0.0;
  }

  getSignPose(signToken) {
    const s = signToken.toUpperCase();

    // =========================================================================
    // 1. Core Vocabulary Words (Authentic ISL Handedness)
    // =========================================================================
    if (s === "NAMASTE") {
      return {
        head: { x: 0.18, y: 0, z: 0 },
        chest: { x: 0.05, y: 0, z: 0 },
        leftShoulder: { x: -0.85, y: 0.35, z: 0.70 },
        leftElbow: { x: -1.75, y: -0.3, z: 0.2 },
        leftWrist: { x: 0.2, y: 1.1, z: 0 },
        rightShoulder: { x: -0.85, y: -0.35, z: -0.70 },
        rightElbow: { x: -1.75, y: 0.3, z: -0.2 },
        rightWrist: { x: 0.2, y: -1.1, z: 0 },
        leftFingers: [0, 0, 0, 0, 0],
        rightFingers: [0, 0, 0, 0, 0]
      };
    }

    if (s === "HELP") {
      return {
        head: { x: 0.1, y: 0, z: 0 },
        chest: { x: 0.05, y: 0, z: 0 },
        leftShoulder: { x: -0.70, y: 0.20, z: 0.40 },
        leftElbow: { x: -1.40, y: 0, z: 0.20 },
        leftWrist: { x: 0.20, y: 0.30, z: 0 }, // Open flat palm facing up
        rightShoulder: { x: -0.80, y: -0.15, z: -0.30 },
        rightElbow: { x: -1.55, y: 0.10, z: -0.20 },
        rightWrist: { x: 0.15, y: -0.10, z: 0 }, // Thumbs-up fist resting atop left palm
        leftFingers: [0, 0, 0, 0, 0],
        rightFingers: [0, 1, 1, 1, 1] // Thumb upright
      };
    }

    if (s === "STOP") {
      return {
        head: { x: 0.08, y: 0, z: 0 },
        chest: { x: 0.05, y: 0, z: 0 },
        leftShoulder: { x: -0.70, y: 0.20, z: 0.35 },
        leftElbow: { x: -1.35, y: 0, z: 0.15 },
        leftWrist: { x: 0.25, y: 0.20, z: 0 }, // Horizontal base palm
        rightShoulder: { x: -0.85, y: -0.20, z: -0.40 },
        rightElbow: { x: -1.65, y: 0.15, z: -0.15 },
        rightWrist: { x: 0.40, y: -0.50, z: 0 }, // Vertical chopping palm
        leftFingers: [0, 0, 0, 0, 0],
        rightFingers: [0, 0, 0, 0, 0]
      };
    }

    if (s === "WELCOME") {
      return {
        head: { x: 0.10, y: 0, z: 0 },
        chest: { x: 0.05, y: 0, z: 0 },
        leftShoulder: { x: -0.65, y: 0.35, z: 0.50 },
        leftElbow: { x: -1.30, y: -0.20, z: 0.30 },
        leftWrist: { x: 0.20, y: 0.50, z: 0 },
        rightShoulder: { x: -0.65, y: -0.35, z: -0.50 },
        rightElbow: { x: -1.30, y: 0.20, z: -0.30 },
        rightWrist: { x: 0.20, y: -0.50, z: 0 },
        leftFingers: [0, 0, 0, 0, 0],
        rightFingers: [0, 0, 0, 0, 0]
      };
    }

    if (s === "FRIEND") {
      return {
        head: { x: 0.12, y: 0, z: 0 },
        chest: { x: 0.05, y: 0, z: 0 },
        leftShoulder: { x: -0.75, y: 0.25, z: 0.40 },
        leftElbow: { x: -1.50, y: 0, z: 0.20 },
        leftWrist: { x: 0.20, y: 0.40, z: 0 },
        rightShoulder: { x: -0.75, y: -0.25, z: -0.40 },
        rightElbow: { x: -1.50, y: 0, z: -0.20 },
        rightWrist: { x: 0.20, y: -0.40, z: 0 },
        leftFingers: [1, 0.45, 1, 1, 1], // Hooked index
        rightFingers: [1, 0.45, 1, 1, 1]
      };
    }

    if (s === "THANK_YOU" || s === "THANK") {
      return {
        head: { x: 0.10, y: 0, z: 0 },
        chest: { x: 0.05, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -1.05, y: 0.20, z: -0.30 },
        rightElbow: { x: -1.80, y: 0.30, z: 0 },
        rightWrist: { x: 0.40, y: 0.20, z: 0.10 },
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: [0, 0, 0, 0, 0]
      };
    }

    if (s === "FOOD" || s === "EAT") {
      return {
        head: { x: 0.15, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -1.1, y: 0.3, z: -0.2 },
        rightElbow: { x: -2.2, y: 0.1, z: 0 },
        rightWrist: { x: 0.6, y: 0, z: 0.4 }, // Clustered near mouth
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: [0.9, 0.9, 0.9, 0.9, 0.9]
      };
    }

    if (s === "WATER" || s === "DRINK") {
      return {
        head: { x: 0.1, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -1.0, y: 0.2, z: -0.2 },
        rightElbow: { x: -2.1, y: 0.2, z: 0 },
        rightWrist: { x: 0.5, y: 0, z: 0.3 }, // W gesture near chin
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: [1, 0, 0, 0, 1] // 'W' gesture
      };
    }

    if (s === "YES") {
      return {
        head: { x: 0.2, y: 0, z: 0 },
        chest: { x: 0.05, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -0.9, y: 0, z: -0.3 },
        rightElbow: { x: -1.6, y: 0, z: 0 },
        rightWrist: { x: 0.6, y: 0, z: 0 },
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: [1, 1, 1, 1, 1]
      };
    }

    if (s === "NO") {
      return {
        head: { x: 0, y: 0.15, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -0.85, y: 0, z: -0.4 },
        rightElbow: { x: -1.5, y: 0.3, z: 0 },
        rightWrist: { x: 0.2, y: 0.4, z: 0 },
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: [1, 0, 1, 1, 1] // Index upright
      };
    }

    if (s === "DOCTOR") {
      return {
        head: { x: 0.12, y: 0, z: 0 },
        chest: { x: 0.05, y: 0, z: 0 },
        leftShoulder: { x: -0.70, y: 0.25, z: 0.35 },
        leftElbow: { x: -1.40, y: -0.10, z: 0.20 },
        leftWrist: { x: 0.15, y: 0.30, z: 0 },
        rightShoulder: { x: -0.80, y: -0.20, z: -0.35 },
        rightElbow: { x: -1.60, y: 0.10, z: -0.15 },
        rightWrist: { x: 0.30, y: -0.20, z: 0 },
        leftFingers: [0, 0, 0, 0, 0],
        rightFingers: [1, 0, 0, 1, 1] // 2 fingers tapping pulse point
      };
    }

    // =========================================================================
    // 2. ISL Manual Alphabet (A-Z) - TWO-HANDED & ONE-HANDED ACCURACY
    // =========================================================================
    if (s === "A") {
      // TWO-HANDED: Left open palm facing right; Right index touches left thumb tip
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.75, y: 0.30, z: 0.50 },
        leftElbow: { x: -1.50, y: -0.10, z: 0.20 },
        leftWrist: { x: 0.20, y: 0.70, z: 0.0 },
        rightShoulder: { x: -0.80, y: -0.30, z: -0.55 },
        rightElbow: { x: -1.60, y: 0.15, z: -0.15 },
        rightWrist: { x: 0.25, y: -0.75, z: 0.0 },
        leftFingers: [0, 0, 0, 0, 0],      // Left hand open palm
        rightFingers: [1, 0, 1, 1, 1]     // Right index extended to thumb
      };
    }

    if (s === "B") {
      // TWO-HANDED: Both hands form loops touching side-by-side (twin B loops)
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.75, y: 0.25, z: 0.45 },
        leftElbow: { x: -1.50, y: 0, z: 0.15 },
        leftWrist: { x: 0.15, y: 0.50, z: 0.0 },
        rightShoulder: { x: -0.75, y: -0.25, z: -0.45 },
        rightElbow: { x: -1.50, y: 0, z: -0.15 },
        rightWrist: { x: 0.15, y: -0.50, z: 0.0 },
        leftFingers: [0.7, 0.7, 0.1, 0.1, 0.1],
        rightFingers: [0.7, 0.7, 0.1, 0.1, 0.1]
      };
    }

    if (s === "C") {
      // ONE-HANDED: Curved C arc with dominant hand
      return {
        head: { x: 0, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -0.90, y: 0.10, z: -0.30 },
        rightElbow: { x: -1.65, y: 0.15, z: 0 },
        rightWrist: { x: 0.20, y: 0.25, z: 0.15 },
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: [0.45, 0.45, 0.45, 0.45, 0.45]
      };
    }

    if (s === "D") {
      // TWO-HANDED: Left index upright (stem); Right hand curves loop against it
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.75, y: 0.25, z: 0.45 },
        leftElbow: { x: -1.50, y: 0, z: 0.15 },
        leftWrist: { x: 0.20, y: 0.60, z: 0.0 },
        rightShoulder: { x: -0.80, y: -0.25, z: -0.50 },
        rightElbow: { x: -1.55, y: 0.10, z: -0.15 },
        rightWrist: { x: 0.20, y: -0.60, z: 0.0 },
        leftFingers: [1, 0, 1, 1, 1],      // Left index straight up
        rightFingers: [0.55, 0.55, 1, 1, 1] // Right curved D arc
      };
    }

    if (s === "E") {
      // TWO-HANDED: Left open palm; Right index touches tip of left index
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.75, y: 0.25, z: 0.45 },
        leftElbow: { x: -1.50, y: 0, z: 0.15 },
        leftWrist: { x: 0.20, y: 0.65, z: 0.0 },
        rightShoulder: { x: -0.80, y: -0.25, z: -0.50 },
        rightElbow: { x: -1.55, y: 0.10, z: -0.15 },
        rightWrist: { x: 0.20, y: -0.65, z: 0.0 },
        leftFingers: [0, 0, 0, 0, 0],
        rightFingers: [1, 0, 1, 1, 1] // Index touches left index
      };
    }

    if (s === "F") {
      // TWO-HANDED: Left index upright; Right index & middle crossed horizontally
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.75, y: 0.25, z: 0.40 },
        leftElbow: { x: -1.50, y: 0, z: 0.15 },
        leftWrist: { x: 0.20, y: 0.50, z: 0.0 },
        rightShoulder: { x: -0.80, y: -0.25, z: -0.45 },
        rightElbow: { x: -1.55, y: 0.10, z: -0.15 },
        rightWrist: { x: 0.25, y: -0.50, z: 0.0 },
        leftFingers: [1, 0, 1, 1, 1],
        rightFingers: [1, 0, 0, 1, 1] // Crossed 2 fingers
      };
    }

    if (s === "G") {
      // TWO-HANDED: Two closed fists stacked vertically
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.65, y: 0.20, z: 0.35 },
        leftElbow: { x: -1.35, y: 0, z: 0.15 },
        leftWrist: { x: 0.20, y: 0.20, z: 0 },  // Lower fist
        rightShoulder: { x: -0.85, y: -0.20, z: -0.35 },
        rightElbow: { x: -1.65, y: 0, z: -0.15 },
        rightWrist: { x: 0.20, y: -0.20, z: 0 }, // Upper fist stacked atop
        leftFingers: [1, 1, 1, 1, 1],
        rightFingers: [1, 1, 1, 1, 1]
      };
    }

    if (s === "H") {
      // TWO-HANDED: Left horizontal flat palm; Right flat palm strokes across it
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.70, y: 0.20, z: 0.40 },
        leftElbow: { x: -1.40, y: 0, z: 0.15 },
        leftWrist: { x: 0.20, y: 0.30, z: 0 },
        rightShoulder: { x: -0.80, y: -0.20, z: -0.45 },
        rightElbow: { x: -1.55, y: 0.10, z: -0.15 },
        rightWrist: { x: 0.25, y: -0.30, z: 0 },
        leftFingers: [0, 0, 0, 0, 0],
        rightFingers: [0, 0, 0, 0, 0]
      };
    }

    if (s === "I") {
      // TWO-HANDED: Left open palm; Right index touches tip of left middle finger
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.75, y: 0.25, z: 0.45 },
        leftElbow: { x: -1.50, y: 0, z: 0.15 },
        leftWrist: { x: 0.20, y: 0.60, z: 0.0 },
        rightShoulder: { x: -0.80, y: -0.25, z: -0.50 },
        rightElbow: { x: -1.55, y: 0.10, z: -0.15 },
        rightWrist: { x: 0.20, y: -0.60, z: 0.0 },
        leftFingers: [0, 0, 0, 0, 0],
        rightFingers: [1, 0, 1, 1, 1]
      };
    }

    if (s === "L") {
      // ONE-HANDED: Thumb & index extended at 90-degree right angle
      return {
        head: { x: 0, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -0.95, y: 0.1, z: -0.35 },
        rightElbow: { x: -1.7, y: 0.1, z: 0 },
        rightWrist: { x: 0.25, y: 0.1, z: 0.2 },
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: [0, 0, 1, 1, 1] // Thumb + index L
      };
    }

    if (s === "M") {
      // TWO-HANDED: Left flat palm up; Right hand 3 fingers resting across it
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.70, y: 0.20, z: 0.40 },
        leftElbow: { x: -1.40, y: 0, z: 0.15 },
        leftWrist: { x: 0.20, y: 0.30, z: 0 },
        rightShoulder: { x: -0.80, y: -0.20, z: -0.45 },
        rightElbow: { x: -1.55, y: 0.10, z: -0.15 },
        rightWrist: { x: 0.25, y: -0.30, z: 0 },
        leftFingers: [0, 0, 0, 0, 0],
        rightFingers: [1, 0, 0, 0, 1] // 3 fingers resting across
      };
    }

    if (s === "N") {
      // TWO-HANDED: Left flat palm up; Right hand 2 fingers resting across it
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.70, y: 0.20, z: 0.40 },
        leftElbow: { x: -1.40, y: 0, z: 0.15 },
        leftWrist: { x: 0.20, y: 0.30, z: 0 },
        rightShoulder: { x: -0.80, y: -0.20, z: -0.45 },
        rightElbow: { x: -1.55, y: 0.10, z: -0.15 },
        rightWrist: { x: 0.25, y: -0.30, z: 0 },
        leftFingers: [0, 0, 0, 0, 0],
        rightFingers: [1, 0, 0, 1, 1] // 2 fingers resting across
      };
    }

    if (s === "P") {
      // TWO-HANDED: Left index upright (stem); Right loop at top of it
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.75, y: 0.25, z: 0.45 },
        leftElbow: { x: -1.50, y: 0, z: 0.15 },
        leftWrist: { x: 0.20, y: 0.60, z: 0.0 },
        rightShoulder: { x: -0.85, y: -0.25, z: -0.50 },
        rightElbow: { x: -1.65, y: 0.10, z: -0.15 },
        rightWrist: { x: 0.20, y: -0.60, z: 0.0 },
        leftFingers: [1, 0, 1, 1, 1],      // Upright stem
        rightFingers: [0.6, 0.6, 1, 1, 1] // Loop at top
      };
    }

    if (s === "S") {
      // TWO-HANDED: Both little fingers (pinkies) hooked together
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.75, y: 0.25, z: 0.40 },
        leftElbow: { x: -1.50, y: 0, z: 0.15 },
        leftWrist: { x: 0.20, y: 0.45, z: 0 },
        rightShoulder: { x: -0.75, y: -0.25, z: -0.40 },
        rightElbow: { x: -1.50, y: 0, z: -0.15 },
        rightWrist: { x: 0.20, y: -0.45, z: 0 },
        leftFingers: [1, 1, 1, 1, 0],
        rightFingers: [1, 1, 1, 1, 0]
      };
    }

    if (s === "T") {
      // TWO-HANDED: Left index upright; Right index touches side horizontally at midpoint
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.75, y: 0.25, z: 0.45 },
        leftElbow: { x: -1.50, y: 0, z: 0.15 },
        leftWrist: { x: 0.20, y: 0.50, z: 0.0 },
        rightShoulder: { x: -0.80, y: -0.25, z: -0.45 },
        rightElbow: { x: -1.55, y: 0.10, z: -0.15 },
        rightWrist: { x: 0.20, y: -0.50, z: 0.0 },
        leftFingers: [1, 0, 1, 1, 1],
        rightFingers: [1, 0, 1, 1, 1]
      };
    }

    if (s === "V") {
      // ONE-HANDED: Peace V sign spread
      return {
        head: { x: 0, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -0.95, y: 0.1, z: -0.35 },
        rightElbow: { x: -1.7, y: 0.1, z: 0 },
        rightWrist: { x: 0.25, y: 0.1, z: 0.2 },
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: [1, 0, 0, 1, 1] // Index + middle spread
      };
    }

    if (s === "W") {
      // ONE-HANDED: Trident W sign
      return {
        head: { x: 0, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -0.95, y: 0.1, z: -0.35 },
        rightElbow: { x: -1.7, y: 0.1, z: 0 },
        rightWrist: { x: 0.25, y: 0.1, z: 0.2 },
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: [1, 0, 0, 0, 1] // Index + middle + ring spread
      };
    }

    if (s === "X") {
      // TWO-HANDED: Both index fingers crossed horizontally like an X
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.75, y: 0.25, z: 0.40 },
        leftElbow: { x: -1.50, y: 0, z: 0.15 },
        leftWrist: { x: 0.20, y: 0.45, z: 0 },
        rightShoulder: { x: -0.75, y: -0.25, z: -0.40 },
        rightElbow: { x: -1.50, y: 0, z: -0.15 },
        rightWrist: { x: 0.20, y: -0.45, z: 0 },
        leftFingers: [1, 0, 1, 1, 1],
        rightFingers: [1, 0, 1, 1, 1]
      };
    }

    // Default letter fallback (Two-handed ISL interactive posture)
    return {
      head: { x: 0, y: 0, z: 0 },
      chest: { x: 0, y: 0, z: 0 },
      leftShoulder: { x: -0.65, y: 0.20, z: 0.35 },
      leftElbow: { x: -1.35, y: 0, z: 0.15 },
      leftWrist: { x: 0.15, y: 0.30, z: 0 },
      rightShoulder: { x: -0.90, y: -0.10, z: -0.30 },
      rightElbow: { x: -1.65, y: 0.10, z: -0.10 },
      rightWrist: { x: 0.25, y: -0.20, z: 0 },
      leftFingers: [0, 0, 0, 0, 0],
      rightFingers: [1, 0, 1, 1, 1]
    };
  }

  playSequence(tokens, onTokenChange = null, onComplete = null) {
    if (!tokens || tokens.length === 0) return;
    if (this.activeTimer) {
      clearTimeout(this.activeTimer);
      this.activeTimer = null;
    }
    this.animationQueue = [...tokens];
    this.onTokenChange = onTokenChange;
    this.onComplete = onComplete;
    this.isPlaying = true;
    this.playNextSign();
  }

  playNextSign() {
    if (this.animationQueue.length === 0) {
      this.isPlaying = false;
      this.currentSign = "IDLE";
      this.setPose(this.defaultPose, 0.35);
      this.updateRealHandCard("READY");
      if (this.onComplete) this.onComplete();
      return;
    }

    const token = this.animationQueue.shift();
    this.currentSign = token;
    if (this.onTokenChange) this.onTokenChange(token);

    // Update real human hand graphic card alongside 3D avatar
    this.updateRealHandCard(token);

    const isAlpha = token.length === 1 && token.match(/[A-Z0-9]/i);
    const holdDuration = isAlpha ? 750 : 1300;
    const pose = this.getSignPose(token);

    this.setPose(pose, 0.22);

    this.activeTimer = setTimeout(() => {
      this.activeTimer = null;
      this.playNextSign();
    }, holdDuration / this.speedMultiplier);
  }

  update(delta) {
    if (this.poseTransitionProgress < 1.0) {
      this.poseTransitionProgress += delta / this.poseTransitionTime;
      if (this.poseTransitionProgress > 1.0) this.poseTransitionProgress = 1.0;

      const t = this.easeOutCubic(this.poseTransitionProgress);

      const lerpGroup = (group, cur, tgt) => {
        if (!group) return;
        group.rotation.x = THREE.MathUtils.lerp(cur.x, tgt.x, t);
        group.rotation.y = THREE.MathUtils.lerp(cur.y, tgt.y, t);
        group.rotation.z = THREE.MathUtils.lerp(cur.z, tgt.z, t);
      };

      lerpGroup(this.joints.neck, this.currentPose.head, this.targetPose.head);
      lerpGroup(this.joints.torso, this.currentPose.chest, this.targetPose.chest);

      lerpGroup(this.joints.leftShoulder, this.currentPose.leftShoulder, this.targetPose.leftShoulder);
      lerpGroup(this.joints.leftElbowGroup, this.currentPose.leftElbow, this.targetPose.leftElbow);
      lerpGroup(this.joints.leftWristGroup, this.currentPose.leftWrist, this.targetPose.leftWrist);

      lerpGroup(this.joints.rightShoulder, this.currentPose.rightShoulder, this.targetPose.rightShoulder);
      lerpGroup(this.joints.rightElbowGroup, this.currentPose.rightElbow, this.targetPose.rightElbow);
      lerpGroup(this.joints.rightWristGroup, this.currentPose.rightWrist, this.targetPose.rightWrist);

      // Realistic 2-segment finger curls
      for (let f = 0; f < 5; f++) {
        const lCurl = THREE.MathUtils.lerp(this.currentPose.leftFingers[f], this.targetPose.leftFingers[f], t);
        const rCurl = THREE.MathUtils.lerp(this.currentPose.rightFingers[f], this.targetPose.rightFingers[f], t);

        if (this.joints.leftFingers && this.joints.leftFingers[f]) {
          this.joints.leftFingers[f].rotation.x = lCurl * 1.5;
          if (this.joints.leftFingers[f].distal) {
            this.joints.leftFingers[f].distal.rotation.x = lCurl * 1.4;
          }
        }
        if (this.joints.rightFingers && this.joints.rightFingers[f]) {
          this.joints.rightFingers[f].rotation.x = rCurl * 1.5;
          if (this.joints.rightFingers[f].distal) {
            this.joints.rightFingers[f].distal.rotation.x = rCurl * 1.4;
          }
        }
      }

      if (this.poseTransitionProgress >= 1.0) {
        this.currentPose = JSON.parse(JSON.stringify(this.targetPose));
      }
    }

    // Subtle natural breathing dynamic
    const time = this.clock.getElapsedTime();
    if (!this.isPlaying) {
      this.joints.torso.position.y = 0.5 + Math.sin(time * 2.0) * 0.008;
      this.joints.neck.rotation.x = Math.sin(time * 1.2) * 0.02;
    }
  }

  easeOutCubic(x) {
    return 1 - Math.pow(1 - x, 3);
  }

  startLoop() {
    const animate = () => {
      requestAnimationFrame(animate);
      const delta = this.clock.getDelta();
      this.update(delta);
      if (this.renderer && this.scene && this.camera) {
        this.renderer.render(this.scene, this.camera);
      }
    };
    animate();
  }
}

window.ISL3DAvatar = ISL3DAvatar;

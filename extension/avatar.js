/**
 * ECHOHANDS 5.0 // ASTRA-VISION 3D Rigged WebGL ISL Avatar Engine
 * Renders an interactive 3D humanoid avatar with articulated joint kinematics,
 * finger articulation, and smooth co-articulation animation blending for ISL signs.
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

    // Default neutral pose definition
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
    this.poseTransitionTime = 0.3; // Seconds to blend
    this.poseTransitionProgress = 1.0;

    this.initScene();
    this.buildAvatarRig();
    this.startLoop();
  }

  initScene() {
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(40, this.width / this.height, 0.1, 100);
    this.camera.position.set(0, 0.4, 2.4);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(this.width, this.height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setClearColor(0x060c11, 0.85); // Tactical cockpit dark glass
    this.container.appendChild(this.renderer.domElement);

    // Tactical lighting
    const ambientLight = new THREE.AmbientLight(0x406070, 1.2);
    this.scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0x00e6b4, 2.0); // Teal rim
    keyLight.position.set(2, 3, 2);
    this.scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x00a8ff, 1.2); // Cyan fill
    fillLight.position.set(-2, 1, 1);
    this.scene.add(fillLight);

    const backLight = new THREE.PointLight(0x00ffcc, 1.5, 5);
    backLight.position.set(0, 0.5, -1);
    this.scene.add(backLight);

    // Responsive resize
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
    // Tactical materials
    const armorMat = new THREE.MeshStandardMaterial({
      color: 0x142028,
      roughness: 0.4,
      metalness: 0.7
    });

    const glowJointMat = new THREE.MeshStandardMaterial({
      color: 0x00e6b4,
      emissive: 0x008866,
      emissiveIntensity: 0.6,
      roughness: 0.2
    });

    const skinMat = new THREE.MeshStandardMaterial({
      color: 0xd9a888, // Natural warm tone with tactical finish
      roughness: 0.6
    });

    // Root Group
    const root = new THREE.Group();
    root.position.set(0, -0.6, 0);
    this.scene.add(root);
    this.joints.root = root;

    // Torso / Chest
    const torsoGeo = new THREE.BoxGeometry(0.5, 0.6, 0.26);
    const torso = new THREE.Mesh(torsoGeo, armorMat);
    torso.position.set(0, 0.5, 0);
    root.add(torso);
    this.joints.torso = torso;

    // Tactical chest emblem
    const chestPlate = new THREE.Mesh(
      new THREE.CylinderGeometry(0.08, 0.08, 0.02, 16),
      glowJointMat
    );
    chestPlate.rotation.x = Math.PI / 2;
    chestPlate.position.set(0, 0.12, 0.14);
    torso.add(chestPlate);

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

    // Visor / HUD Eyes (tactical glowing strip)
    const visorGeo = new THREE.BoxGeometry(0.24, 0.04, 0.08);
    const visor = new THREE.Mesh(visorGeo, glowJointMat);
    visor.position.set(0, 0.05, 0.16);
    head.add(visor);
    this.joints.visor = visor;

    // Left Arm Chain
    this.joints.leftShoulder = this.createArmChain(torso, -1, armorMat, glowJointMat, skinMat);
    // Right Arm Chain
    this.joints.rightShoulder = this.createArmChain(torso, 1, armorMat, glowJointMat, skinMat);
  }

  createArmChain(torso, side, armorMat, jointMat, skinMat) {
    const isLeft = side < 0;
    const prefix = isLeft ? "left" : "right";

    // Shoulder joint
    const shoulder = new THREE.Group();
    shoulder.position.set(side * 0.32, 0.22, 0);
    torso.add(shoulder);

    const shoulderBall = new THREE.Mesh(new THREE.SphereGeometry(0.08, 16, 16), jointMat);
    shoulder.add(shoulderBall);

    // Upper arm
    const upperArm = new THREE.Group();
    upperArm.position.set(0, 0, 0);
    shoulder.add(upperArm);

    const bicep = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.05, 0.32, 12), armorMat);
    bicep.position.set(0, -0.16, 0);
    upperArm.add(bicep);

    // Elbow
    const elbow = new THREE.Group();
    elbow.position.set(0, -0.32, 0);
    upperArm.add(elbow);
    this.joints[`${prefix}ElbowGroup`] = elbow;

    const elbowBall = new THREE.Mesh(new THREE.SphereGeometry(0.06, 16, 16), jointMat);
    elbow.add(elbowBall);

    // Forearm
    const forearm = new THREE.Group();
    elbow.add(forearm);

    const forearmMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.045, 0.3, 12), armorMat);
    forearmMesh.position.set(0, -0.15, 0);
    forearm.add(forearmMesh);

    // Wrist
    const wrist = new THREE.Group();
    wrist.position.set(0, -0.3, 0);
    forearm.add(wrist);
    this.joints[`${prefix}WristGroup`] = wrist;

    const wristBall = new THREE.Mesh(new THREE.SphereGeometry(0.045, 12, 12), jointMat);
    wrist.add(wristBall);

    // Palm / Hand
    const palmGeo = new THREE.BoxGeometry(0.09, 0.12, 0.03);
    const palm = new THREE.Mesh(palmGeo, skinMat);
    palm.position.set(0, -0.06, 0);
    wrist.add(palm);

    // 5 Articulated Fingers
    const fingers = [];
    const fingerNames = ["thumb", "index", "middle", "ring", "pinky"];
    const xOffsets = side < 0
      ? [0.05, 0.03, 0.01, -0.01, -0.03]
      : [-0.05, -0.03, -0.01, 0.01, 0.03];

    for (let f = 0; f < 5; f++) {
      const fGroup = new THREE.Group();
      fGroup.position.set(xOffsets[f], -0.06, 0);
      palm.add(fGroup);

      const fLen = f === 0 ? 0.05 : 0.06;
      const fGeo = new THREE.CylinderGeometry(0.012, 0.01, fLen, 8);
      const fMesh = new THREE.Mesh(fGeo, skinMat);
      fMesh.position.set(0, -fLen / 2, 0);
      fGroup.add(fMesh);

      fingers.push(fGroup);
    }

    this.joints[`${prefix}Fingers`] = fingers;
    return shoulder;
  }

  // Set 3D target pose for gesture
  setPose(pose, transitionTime = 0.25) {
    this.targetPose = JSON.parse(JSON.stringify(pose));
    this.poseTransitionTime = Math.max(0.08, transitionTime / this.speedMultiplier);
    this.poseTransitionProgress = 0.0;
  }

  // Dictionary of ISL Sign Kinematic Presets
  getSignPose(signToken) {
    const s = signToken.toUpperCase();

    // 1. Common Words
    if (s === "NAMASTE") {
      return {
        head: { x: 0.15, y: 0, z: 0 },
        chest: { x: 0.05, y: 0, z: 0 },
        leftShoulder: { x: -0.4, y: 0.2, z: 0.7 },
        leftElbow: { x: -1.6, y: -0.5, z: 0.2 },
        leftWrist: { x: 0.1, y: 0.9, z: 0 },
        rightShoulder: { x: -0.4, y: -0.2, z: -0.7 },
        rightElbow: { x: -1.6, y: 0.5, z: -0.2 },
        rightWrist: { x: 0.1, y: -0.9, z: 0 },
        leftFingers: [0, 0, 0, 0, 0],
        rightFingers: [0, 0, 0, 0, 0]
      };
    }

    if (s === "HELLO") {
      return {
        head: { x: -0.05, y: 0.1, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -1.2, y: 0.4, z: -0.6 },
        rightElbow: { x: -1.4, y: 0.8, z: 0.3 },
        rightWrist: { x: 0, y: 0.5, z: 0.4 },
        leftFingers: [0.3, 0.3, 0.3, 0.3, 0.3],
        rightFingers: [0, 0, 0, 0, 0]
      };
    }

    if (s === "THANK_YOU" || s === "THANK") {
      return {
        head: { x: 0.1, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -0.8, y: 0.2, z: -0.3 },
        rightElbow: { x: -1.8, y: 0.2, z: 0 },
        rightWrist: { x: 0.4, y: 0, z: 0.2 },
        leftFingers: [0.3, 0.3, 0.3, 0.3, 0.3],
        rightFingers: [0, 0, 0, 0, 0]
      };
    }

    if (s === "HELP") {
      return {
        head: { x: 0, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.5, y: 0.2, z: 0.4 },
        leftElbow: { x: -1.2, y: 0, z: 0.4 },
        leftWrist: { x: 0.2, y: 0, z: 0 }, // Flat palm up
        rightShoulder: { x: -0.6, y: -0.1, z: -0.3 },
        rightElbow: { x: -1.3, y: 0.2, z: -0.3 },
        rightWrist: { x: 0.1, y: 0, z: 0 }, // Fist resting on palm
        leftFingers: [0, 0, 0, 0, 0],
        rightFingers: [0, 1, 1, 1, 1] // Thumb up
      };
    }

    if (s === "FOOD" || s === "EAT") {
      return {
        head: { x: 0.1, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -0.8, y: 0.3, z: -0.2 },
        rightElbow: { x: -2.1, y: 0.1, z: 0 },
        rightWrist: { x: 0.5, y: 0, z: 0.3 }, // Near mouth
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: [0.8, 0.8, 0.8, 0.8, 0.8] // Clustered to mouth
      };
    }

    if (s === "WATER" || s === "DRINK") {
      return {
        head: { x: 0.05, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -0.7, y: 0.2, z: -0.2 },
        rightElbow: { x: -2.0, y: 0.2, z: 0 },
        rightWrist: { x: 0.4, y: 0, z: 0.2 },
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: [0.9, 0, 0, 0, 0.9] // 'W' shape
      };
    }

    if (s === "DOCTOR") {
      return {
        head: { x: 0.1, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: -0.5, y: 0.3, z: 0.3 },
        leftElbow: { x: -1.2, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0.5, z: 0 },
        rightShoulder: { x: -0.5, y: -0.2, z: -0.2 },
        rightElbow: { x: -1.3, y: 0.4, z: -0.2 },
        rightWrist: { x: 0.2, y: 0, z: 0 },
        leftFingers: [0, 0, 0, 0, 0],
        rightFingers: [1, 0, 0, 1, 1] // Pulse check with index+middle
      };
    }

    if (s === "YES") {
      return {
        head: { x: 0.15, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -0.6, y: 0, z: -0.3 },
        rightElbow: { x: -1.4, y: 0, z: 0 },
        rightWrist: { x: 0.5, y: 0, z: 0 },
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: [1, 1, 1, 1, 1] // Fist nodding
      };
    }

    if (s === "NO") {
      return {
        head: { x: 0, y: 0.1, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -0.6, y: 0, z: -0.4 },
        rightElbow: { x: -1.3, y: 0.3, z: 0 },
        rightWrist: { x: 0.1, y: 0.3, z: 0 },
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: [0.8, 0.8, 0.8, 0, 0] // Snap close
      };
    }

    // 2. Letters & Fingerspelling (A-Z)
    if (s.length === 1 && s >= "A" && s <= "Z") {
      const code = s.charCodeAt(0) - 65;
      const fingerPatterns = [
        [0, 1, 1, 1, 1], // A
        [1, 0, 0, 0, 0], // B
        [0.4, 0.4, 0.4, 0.4, 0.4], // C
        [1, 0, 1, 1, 1], // D
        [1, 0.9, 0.9, 0.9, 0.9], // E
        [0.8, 0.8, 0, 0, 0], // F
        [0, 0, 1, 1, 1], // G
        [0, 0, 0, 1, 1], // H
        [1, 1, 1, 1, 0], // I
        [1, 1, 1, 1, 0], // J
        [0, 0, 0, 1, 1], // K
        [0, 0, 1, 1, 1], // L
        [0.9, 0.9, 0.9, 1, 1], // M
        [0.9, 0.9, 1, 1, 1], // N
        [0.5, 0.5, 0.5, 0.5, 0.5], // O
        [0, 0, 0.7, 1, 1], // P
        [0, 0, 1, 1, 1], // Q
        [1, 0, 0, 1, 1], // R
        [1, 1, 1, 1, 1], // S
        [0.5, 1, 1, 1, 1], // T
        [1, 0, 0, 1, 1], // U
        [1, 0, 0, 1, 1], // V
        [1, 0, 0, 0, 1], // W
        [1, 0.5, 1, 1, 1], // X
        [0, 1, 1, 1, 0], // Y
        [1, 0, 1, 1, 1]  // Z
      ];
      const rFing = fingerPatterns[code] || [0, 0, 0, 0, 0];

      return {
        head: { x: 0, y: 0, z: 0 },
        chest: { x: 0, y: 0, z: 0 },
        leftShoulder: { x: 0.1, y: 0, z: -0.2 },
        leftElbow: { x: 0.3, y: 0, z: 0.4 },
        leftWrist: { x: 0, y: 0, z: 0 },
        rightShoulder: { x: -0.7, y: 0, z: -0.3 },
        rightElbow: { x: -1.3, y: 0, z: 0 },
        rightWrist: { x: 0.1, y: 0, z: 0.2 },
        leftFingers: [0.5, 0.5, 0.5, 0.5, 0.5],
        rightFingers: rFing
      };
    }

    // Default neutral ready pose
    return JSON.parse(JSON.stringify(this.defaultPose));
  }

  // Play a sequence of signs with co-articulation
  playSequence(tokens, onTokenChange = null, onComplete = null) {
    if (!tokens || tokens.length === 0) return;
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
      this.setPose(this.defaultPose, 0.4);
      if (this.onComplete) this.onComplete();
      return;
    }

    const token = this.animationQueue.shift();
    this.currentSign = token;
    if (this.onTokenChange) this.onTokenChange(token);

    const isAlpha = token.length === 1 && token.match(/[A-Z0-9]/i);
    const holdDuration = isAlpha ? 650 : 1200; // ms per sign
    const pose = this.getSignPose(token);

    this.setPose(pose, 0.25);

    setTimeout(() => {
      this.playNextSign();
    }, holdDuration / this.speedMultiplier);
  }

  // Loop update
  update(delta) {
    // 1. Smoothly interpolate joints toward target pose (co-articulation)
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

      // Finger curls
      for (let f = 0; f < 5; f++) {
        const lCurl = THREE.MathUtils.lerp(this.currentPose.leftFingers[f], this.targetPose.leftFingers[f], t);
        const rCurl = THREE.MathUtils.lerp(this.currentPose.rightFingers[f], this.targetPose.rightFingers[f], t);

        if (this.joints.leftFingers && this.joints.leftFingers[f]) {
          this.joints.leftFingers[f].rotation.x = lCurl * 1.4;
        }
        if (this.joints.rightFingers && this.joints.rightFingers[f]) {
          this.joints.rightFingers[f].rotation.x = rCurl * 1.4;
        }
      }

      if (this.poseTransitionProgress >= 1.0) {
        this.currentPose = JSON.parse(JSON.stringify(this.targetPose));
      }
    }

    // 2. Subtle organic breathing / idle dynamics
    const time = this.clock.getElapsedTime();
    if (!this.isPlaying) {
      this.joints.torso.position.y = 0.5 + Math.sin(time * 2.0) * 0.01;
      this.joints.neck.rotation.x = Math.sin(time * 1.2) * 0.03;
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

// Attach to window for extension scripts
window.ISL3DAvatar = ISL3DAvatar;

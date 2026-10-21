import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { CompanionExpressionState, CursorGazeCoordinates } from '../types';

interface Sloth3DCanvasProps {
  state: CompanionExpressionState;
  cursorGaze?: CursorGazeCoordinates | null;
  gazeEnabled?: boolean;
  onFallback?: () => void;
}

export const Sloth3DCanvas: React.FC<Sloth3DCanvasProps> = ({
  state,
  cursorGaze,
  gazeEnabled = true,
  onFallback,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [webGlAvailable, setWebGlAvailable] = useState<boolean>(true);

  // References to animated 3D parts
  const animRefs = useRef<{
    headGroup?: THREE.Group;
    eyesGroup?: THREE.Group;
    leftEye?: THREE.Mesh;
    rightEye?: THREE.Mesh;
    leftPupil?: THREE.Mesh;
    rightPupil?: THREE.Mesh;
    leftUpperLid?: THREE.Mesh;
    rightUpperLid?: THREE.Mesh;
    leftLowerLid?: THREE.Mesh;
    rightLowerLid?: THREE.Mesh;
    jaw?: THREE.Group;
    mouthOpenMesh?: THREE.Mesh;
    bodyGroup?: THREE.Group;
    leftArm?: THREE.Group;
    rightArm?: THREE.Group;
    tie?: THREE.Mesh;
    sparkles?: THREE.Points;
  }>({});

  // Animation state tracking
  const stateRef = useRef({
    currentState: state,
    targetGaze: { x: 0, y: 0 },
    currentGaze: { x: 0, y: 0 },
    blinkProgress: 0,
    blinkTarget: 0,
    nextBlinkTime: 2.0,
    mouthOpen: 0,
    targetMouthOpen: 0,
    typingSpeed: 0,
    time: 0,
  });

  // Keep stateRef in sync with props
  useEffect(() => {
    stateRef.current.currentState = state;
    // Set target mouth openness based on state
    if (state === 'success') {
      stateRef.current.targetMouthOpen = 1.0; // Iconic massive Flash laugh
    } else if (state === 'listening') {
      stateRef.current.targetMouthOpen = 0.25;
    } else if (state === 'thinking') {
      stateRef.current.targetMouthOpen = 0.1;
    } else if (state === 'stopped') {
      stateRef.current.targetMouthOpen = 0.35;
    } else {
      stateRef.current.targetMouthOpen = 0.0;
    }
  }, [state]);

  // Update target cursor gaze
  useEffect(() => {
    if (gazeEnabled && cursorGaze && state !== 'disconnected') {
      // Map normalized 0..1 to -1..1 gaze direction
      stateRef.current.targetGaze = {
        x: (cursorGaze.x - 0.5) * 1.8,
        y: -(cursorGaze.y - 0.5) * 1.4, // Inverted Y for 3D world space
      };
    } else {
      // Look forward towards camera
      stateRef.current.targetGaze = { x: 0, y: 0 };
    }
  }, [cursorGaze, gazeEnabled, state]);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // Check WebGL availability
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (!gl) {
      console.warn('WebGL not supported on this device. Switching to 2D SVG companion.');
      setWebGlAvailable(false);
      if (onFallback) onFallback();
      return;
    }

    // 1. Scene, Camera, Renderer
    const width = container.clientWidth || 320;
    const height = container.clientHeight || 320;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    camera.position.set(0, 0.3, 3.6);
    camera.lookAt(0, 0.1, 0);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        powerPreference: 'high-performance',
        precision: 'mediump',
      });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      container.appendChild(renderer.domElement);
    } catch (err) {
      console.warn('WebGL context creation failed, falling back to 2D:', err);
      setWebGlAvailable(false);
      if (onFallback) onFallback();
      return;
    }


    // 2. Lighting - Warm Disney Zootopia DMV Lighting
    const ambientLight = new THREE.AmbientLight(0xfef3c7, 1.4);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xfff7ed, 1.8);
    keyLight.position.set(2.5, 3.5, 3.0);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0xa7f3d0, 0.8);
    fillLight.position.set(-3.0, 1.5, 2.0);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0xfbbf24, 1.2);
    rimLight.position.set(0, 3.0, -3.0);
    scene.add(rimLight);

    // 3. Materials
    const slothFurDark = new THREE.MeshStandardMaterial({
      color: 0x451a03, // Dark chocolate eye patch
      roughness: 0.9,
      metalness: 0.05,
    });
    const slothFurBase = new THREE.MeshStandardMaterial({
      color: 0x92613d, // Warm caramel sloth fur
      roughness: 0.85,
      metalness: 0.05,
    });
    const slothFurLight = new THREE.MeshStandardMaterial({
      color: 0xd6c2a4, // Cream face & muzzle
      roughness: 0.9,
      metalness: 0.0,
    });
    const noseMat = new THREE.MeshStandardMaterial({
      color: 0x1f1917, // Dark leathery nose
      roughness: 0.5,
      metalness: 0.15,
    });
    const eyeWhiteMat = new THREE.MeshStandardMaterial({
      color: 0xfafafa,
      roughness: 0.1,
      metalness: 0.0,
    });
    const pupilMat = new THREE.MeshStandardMaterial({
      color: 0x090604, // Deep dark brown/black
      roughness: 0.1,
    });
    const irisMat = new THREE.MeshStandardMaterial({
      color: 0xb45309, // Warm hazel amber
      roughness: 0.2,
    });
    const dmvShirtMat = new THREE.MeshStandardMaterial({
      color: 0x658d68, // Zootopia DMV Sage Green polo
      roughness: 0.8,
    });
    const tieMat = new THREE.MeshStandardMaterial({
      color: 0xdd5e28, // Orange with navy stripes
      roughness: 0.6,
    });
    const tieClipMat = new THREE.MeshStandardMaterial({
      color: 0xfacc15, // Gold tie clip
      roughness: 0.3,
      metalness: 0.8,
    });
    const clawMat = new THREE.MeshStandardMaterial({
      color: 0xede4d3, // Pale sloth claws
      roughness: 0.4,
    });
    const deskMat = new THREE.MeshStandardMaterial({
      color: 0xb46b38, // Warm wooden DMV counter
      roughness: 0.6,
    });
    const mugMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      roughness: 0.3,
    });

    // 4. Build Procedural Flash Character
    const characterRoot = new THREE.Group();
    scene.add(characterRoot);

    // --- DMV Counter Desk ---
    const deskGeo = new THREE.BoxGeometry(4.0, 0.6, 1.4);
    const desk = new THREE.Mesh(deskGeo, deskMat);
    desk.position.set(0, -0.9, 0.4);
    desk.receiveShadow = true;
    characterRoot.add(desk);

    // Counter Coffee Mug ("You want it when?")
    const mugGroup = new THREE.Group();
    mugGroup.position.set(0.9, -0.5, 0.5);
    const mugGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.24, 16);
    const mug = new THREE.Mesh(mugGeo, mugMat);
    mugGroup.add(mug);
    characterRoot.add(mugGroup);

    // --- Body / Torso ---
    const bodyGroup = new THREE.Group();
    bodyGroup.position.set(0, -0.4, -0.2);
    characterRoot.add(bodyGroup);
    animRefs.current.bodyGroup = bodyGroup;

    // Torso (Green DMV Polo Shirt)
    const torsoGeo = new THREE.CapsuleGeometry(0.55, 0.7, 16, 20);
    const torso = new THREE.Mesh(torsoGeo, dmvShirtMat);
    torso.rotation.x = 0.18;
    torso.castShadow = true;
    bodyGroup.add(torso);

    // Collar
    const collarGeo = new THREE.TorusGeometry(0.35, 0.08, 12, 24);
    const collar = new THREE.Mesh(collarGeo, dmvShirtMat);
    collar.position.set(0, 0.38, 0.16);
    collar.rotation.x = Math.PI / 2.4;
    bodyGroup.add(collar);

    // Tie (Orange and Navy Striped DMV Tie)
    const tieGroup = new THREE.Group();
    tieGroup.position.set(0, 0.24, 0.28);
    const tieGeo = new THREE.BoxGeometry(0.14, 0.6, 0.03);
    const tie = new THREE.Mesh(tieGeo, tieMat);
    tieGroup.add(tie);

    // Gold tie clip
    const clipGeo = new THREE.BoxGeometry(0.16, 0.03, 0.04);
    const clip = new THREE.Mesh(clipGeo, tieClipMat);
    clip.position.set(0, 0.05, 0.015);
    tieGroup.add(clip);

    bodyGroup.add(tieGroup);
    animRefs.current.tie = tie;

    // Sloth Arms & Claws on Counter
    const leftArm = new THREE.Group();
    leftArm.position.set(-0.55, 0.1, 0.1);
    const armGeo = new THREE.CapsuleGeometry(0.15, 0.6, 12, 16);
    const armMeshL = new THREE.Mesh(armGeo, dmvShirtMat);
    armMeshL.rotation.z = 0.55;
    armMeshL.rotation.x = -0.55;
    leftArm.add(armMeshL);

    // 3 Curved Sloth Claws (Left)
    for (let c = -1; c <= 1; c++) {
      const clawGeo = new THREE.ConeGeometry(0.025, 0.18, 8);
      const claw = new THREE.Mesh(clawGeo, clawMat);
      claw.position.set(-0.35 + c * 0.06, -0.42, 0.45);
      claw.rotation.x = Math.PI / 2 + 0.3;
      leftArm.add(claw);
    }
    bodyGroup.add(leftArm);
    animRefs.current.leftArm = leftArm;

    const rightArm = new THREE.Group();
    rightArm.position.set(0.55, 0.1, 0.1);
    const armMeshR = new THREE.Mesh(armGeo, dmvShirtMat);
    armMeshR.rotation.z = -0.55;
    armMeshR.rotation.x = -0.55;
    rightArm.add(armMeshR);

    // 3 Curved Sloth Claws (Right)
    for (let c = -1; c <= 1; c++) {
      const clawGeo = new THREE.ConeGeometry(0.025, 0.18, 8);
      const claw = new THREE.Mesh(clawGeo, clawMat);
      claw.position.set(0.35 + c * 0.06, -0.42, 0.45);
      claw.rotation.x = Math.PI / 2 + 0.3;
      rightArm.add(claw);
    }
    bodyGroup.add(rightArm);
    animRefs.current.rightArm = rightArm;

    // --- Head Group ---
    const headGroup = new THREE.Group();
    headGroup.position.set(0, 0.38, 0.15);
    characterRoot.add(headGroup);
    animRefs.current.headGroup = headGroup;

    // Head Base (Fur Dome)
    const headGeo = new THREE.SphereGeometry(0.58, 24, 20);
    headGeo.scale(1.0, 1.05, 0.95);
    const headMesh = new THREE.Mesh(headGeo, slothFurBase);
    headMesh.castShadow = true;
    headGroup.add(headMesh);

    // Parted Sloth Hair tuft on top
    const hairGeo = new THREE.ConeGeometry(0.25, 0.3, 8);
    const hair = new THREE.Mesh(hairGeo, slothFurLight);
    hair.position.set(0, 0.65, -0.05);
    hair.rotation.x = -0.3;
    headGroup.add(hair);

    // Cream Face / Muzzle Disc
    const faceMaskGeo = new THREE.SphereGeometry(0.46, 20, 16);
    faceMaskGeo.scale(1.0, 0.95, 0.5);
    const faceMask = new THREE.Mesh(faceMaskGeo, slothFurLight);
    faceMask.position.set(0, -0.05, 0.32);
    headGroup.add(faceMask);

    // Eye Patches (Dark Fur around eyes)
    const patchGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.04, 16);
    patchGeo.rotateX(Math.PI / 2);
    const patchL = new THREE.Mesh(patchGeo, slothFurDark);
    patchL.position.set(-0.25, 0.08, 0.48);
    patchL.rotation.z = 0.25;
    headGroup.add(patchL);

    const patchR = new THREE.Mesh(patchGeo, slothFurDark);
    patchR.position.set(0.25, 0.08, 0.48);
    patchR.rotation.z = -0.25;
    headGroup.add(patchR);

    // Eyes Group
    const eyesGroup = new THREE.Group();
    eyesGroup.position.set(0, 0.08, 0.46);
    headGroup.add(eyesGroup);
    animRefs.current.eyesGroup = eyesGroup;

    // Left & Right Eyeballs
    const eyeGeo = new THREE.SphereGeometry(0.13, 20, 16);

    const eyeL = new THREE.Mesh(eyeGeo, eyeWhiteMat);
    eyeL.position.set(-0.25, 0, 0);
    eyesGroup.add(eyeL);
    animRefs.current.leftEye = eyeL;

    const eyeR = new THREE.Mesh(eyeGeo, eyeWhiteMat);
    eyeR.position.set(0.25, 0, 0);
    eyesGroup.add(eyeR);
    animRefs.current.rightEye = eyeR;

    // Iris & Pupil (Left)
    const irisGeo = new THREE.CylinderGeometry(0.065, 0.065, 0.02, 16);
    irisGeo.rotateX(Math.PI / 2);
    const irisL = new THREE.Mesh(irisGeo, irisMat);
    irisL.position.set(0, 0, 0.12);
    eyeL.add(irisL);

    const pupilGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.022, 16);
    pupilGeo.rotateX(Math.PI / 2);
    const pupilL = new THREE.Mesh(pupilGeo, pupilMat);
    pupilL.position.set(0, 0, 0.125);
    eyeL.add(pupilL);
    animRefs.current.leftPupil = pupilL;

    // Specular eye catchlight
    const sparkleGeo = new THREE.SphereGeometry(0.018, 8, 8);
    const sparkleL = new THREE.Mesh(sparkleGeo, new THREE.MeshBasicMaterial({ color: 0xffffff }));
    sparkleL.position.set(0.02, 0.025, 0.13);
    eyeL.add(sparkleL);

    // Iris & Pupil (Right)
    const irisR = new THREE.Mesh(irisGeo, irisMat);
    irisR.position.set(0, 0, 0.12);
    eyeR.add(irisR);

    const pupilR = new THREE.Mesh(pupilGeo, pupilMat);
    pupilR.position.set(0, 0, 0.125);
    eyeR.add(pupilR);
    animRefs.current.rightPupil = pupilR;

    const sparkleR = new THREE.Mesh(sparkleGeo, new THREE.MeshBasicMaterial({ color: 0xffffff }));
    sparkleR.position.set(0.02, 0.025, 0.13);
    eyeR.add(sparkleR);

    // Eyelids (for sloth slow blinks & heavy sleepy eyelids)
    const lidGeo = new THREE.CylinderGeometry(0.14, 0.14, 0.08, 16, 1, false, 0, Math.PI);
    lidGeo.rotateX(Math.PI / 2);

    const upperLidL = new THREE.Mesh(lidGeo, slothFurDark);
    upperLidL.position.set(-0.25, 0.04, 0.05);
    eyesGroup.add(upperLidL);
    animRefs.current.leftUpperLid = upperLidL;

    const upperLidR = new THREE.Mesh(lidGeo, slothFurDark);
    upperLidR.position.set(0.25, 0.04, 0.05);
    eyesGroup.add(upperLidR);
    animRefs.current.rightUpperLid = upperLidR;

    // Leathery Snout & Nose
    const snoutGeo = new THREE.CapsuleGeometry(0.14, 0.18, 12, 16);
    snoutGeo.scale(1.3, 0.9, 1.1);
    const snout = new THREE.Mesh(snoutGeo, noseMat);
    snout.position.set(0, -0.06, 0.52);
    snout.rotation.x = -0.15;
    headGroup.add(snout);

    // Nostrils
    const nostrilGeo = new THREE.SphereGeometry(0.025, 8, 8);
    const nostrilMat = new THREE.MeshBasicMaterial({ color: 0x000000 });
    const nostrilL = new THREE.Mesh(nostrilGeo, nostrilMat);
    nostrilL.position.set(-0.06, -0.08, 0.62);
    headGroup.add(nostrilL);

    const nostrilR = new THREE.Mesh(nostrilGeo, nostrilMat);
    nostrilR.position.set(0.06, -0.08, 0.62);
    headGroup.add(nostrilR);

    // Jaw / Mouth (Opens up wide for Flash's huge slow laugh!)
    const jawGroup = new THREE.Group();
    jawGroup.position.set(0, -0.22, 0.38);
    headGroup.add(jawGroup);
    animRefs.current.jaw = jawGroup;

    // Mouth interior (Dark pink)
    const mouthInteriorGeo = new THREE.BoxGeometry(0.26, 0.18, 0.15);
    const mouthInteriorMat = new THREE.MeshStandardMaterial({ color: 0x881337, roughness: 0.7 });
    const mouthInterior = new THREE.Mesh(mouthInteriorGeo, mouthInteriorMat);
    mouthInterior.position.set(0, 0, 0.02);
    jawGroup.add(mouthInterior);
    animRefs.current.mouthOpenMesh = mouthInterior;

    // Tongue
    const tongueGeo = new THREE.SphereGeometry(0.09, 12, 8);
    tongueGeo.scale(1.2, 0.5, 1.0);
    const tongue = new THREE.Mesh(tongueGeo, new THREE.MeshStandardMaterial({ color: 0xf43f5e }));
    tongue.position.set(0, -0.04, 0.06);
    jawGroup.add(tongue);

    // Golden Celebration Sparkle Particles (for Happy/Success)
    const sparkleCount = 24;
    const sparklePositions = new Float32Array(sparkleCount * 3);
    for (let i = 0; i < sparkleCount; i++) {
      sparklePositions[i * 3] = (Math.random() - 0.5) * 1.6;
      sparklePositions[i * 3 + 1] = Math.random() * 1.5 + 0.2;
      sparklePositions[i * 3 + 2] = (Math.random() - 0.5) * 1.0 + 0.5;
    }
    const sparklePartGeo = new THREE.BufferGeometry();
    sparklePartGeo.setAttribute('position', new THREE.BufferAttribute(sparklePositions, 3));
    const sparklePartMat = new THREE.PointsMaterial({
      color: 0xfde047,
      size: 0.08,
      transparent: true,
      opacity: 0.0,
    });
    const sparkles = new THREE.Points(sparklePartGeo, sparklePartMat);
    scene.add(sparkles);
    animRefs.current.sparkles = sparkles;

    // 5. Main Animation Loop
    let animId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);

      const delta = clock.getDelta();
      stateRef.current.time += delta;
      const t = stateRef.current.time;
      const curState = stateRef.current.currentState;

      // Smooth gaze tracking towards target (snappy, low lag)
      stateRef.current.currentGaze.x = THREE.MathUtils.lerp(
        stateRef.current.currentGaze.x,
        stateRef.current.targetGaze.x,
        delta * 14.0
      );
      stateRef.current.currentGaze.y = THREE.MathUtils.lerp(
        stateRef.current.currentGaze.y,
        stateRef.current.targetGaze.y,
        delta * 14.0
      );

      // --- Sloth Blinking Logic (Deliberate & Slow) ---
      if (t > stateRef.current.nextBlinkTime && curState !== 'disconnected') {
        stateRef.current.blinkTarget = 1.0;
        if (stateRef.current.blinkProgress > 0.85) {
          stateRef.current.blinkTarget = 0.0;
          // Schedule next blink in 3.5 - 7 seconds
          stateRef.current.nextBlinkTime = t + 3.5 + Math.random() * 3.5;
        }
      }
      stateRef.current.blinkProgress = THREE.MathUtils.lerp(
        stateRef.current.blinkProgress,
        stateRef.current.blinkTarget,
        delta * 12.0
      );

      // --- Head & Body Animation by State ---
      const head = animRefs.current.headGroup;
      const body = animRefs.current.bodyGroup;
      const leftArm = animRefs.current.leftArm;
      const rightArm = animRefs.current.rightArm;
      const jaw = animRefs.current.jaw;
      const leftUpperLid = animRefs.current.leftUpperLid;
      const rightUpperLid = animRefs.current.rightUpperLid;
      const leftEye = animRefs.current.leftEye;
      const rightEye = animRefs.current.rightEye;
      const sparkles = animRefs.current.sparkles;

      // Breathing oscillation
      const breathe = Math.sin(t * 1.5) * 0.015;
      if (body) {
        body.position.y = -0.4 + breathe;
      }

      if (head) {
        // Base gaze rotation (responsive tracking)
        const gazeYaw = stateRef.current.currentGaze.x * 0.65;
        const gazePitch = stateRef.current.currentGaze.y * 0.45;

        if (curState === 'idle') {
          head.rotation.y = THREE.MathUtils.lerp(head.rotation.y, gazeYaw + Math.sin(t * 0.8) * 0.04, delta * 8.0);
          head.rotation.x = THREE.MathUtils.lerp(head.rotation.x, gazePitch + breathe, delta * 8.0);
          head.rotation.z = THREE.MathUtils.lerp(head.rotation.z, 0, delta * 6.0);
        } else if (curState === 'listening') {
          // Attentive curious head tilt
          head.rotation.y = THREE.MathUtils.lerp(head.rotation.y, gazeYaw * 0.7, delta * 8.0);
          head.rotation.x = THREE.MathUtils.lerp(head.rotation.x, -0.08, delta * 8.0);
          head.rotation.z = THREE.MathUtils.lerp(head.rotation.z, 0.12, delta * 8.0);
        } else if (curState === 'thinking') {
          // Pondering upward gaze
          head.rotation.y = THREE.MathUtils.lerp(head.rotation.y, Math.sin(t * 1.2) * 0.1, delta * 2.5);
          head.rotation.x = THREE.MathUtils.lerp(head.rotation.x, 0.18, delta * 2.5);
          head.rotation.z = THREE.MathUtils.lerp(head.rotation.z, -0.08, delta * 2.5);
        } else if (curState === 'executing') {
          // Focused on desk / working
          head.rotation.y = THREE.MathUtils.lerp(head.rotation.y, gazeYaw * 0.5, delta * 8.0);
          head.rotation.x = THREE.MathUtils.lerp(head.rotation.x, -0.12 + Math.sin(t * 4.0) * 0.02, delta * 8.0);
        } else if (curState === 'success') {
          // Ecstatic head bob and tilt back
          head.rotation.x = THREE.MathUtils.lerp(head.rotation.x, 0.12 + Math.sin(t * 3.0) * 0.03, delta * 3.0);
          head.rotation.y = THREE.MathUtils.lerp(head.rotation.y, Math.sin(t * 2.0) * 0.08, delta * 3.0);
        } else if (curState === 'stopped') {
          // Frozen still
          head.rotation.x = THREE.MathUtils.lerp(head.rotation.x, -0.05, delta * 8.0);
        } else if (curState === 'disconnected') {
          // Sleepy nap slumped head
          head.rotation.x = THREE.MathUtils.lerp(head.rotation.x, -0.28, delta * 2.0);
          head.rotation.z = THREE.MathUtils.lerp(head.rotation.z, 0.15, delta * 2.0);
        }
      }

      // --- Eye Gaze & Eyelids (Bold, responsive range) ---
      if (leftEye && rightEye) {
        const eyeYaw = stateRef.current.currentGaze.x * 0.85;
        const eyePitch = stateRef.current.currentGaze.y * 0.65;
        leftEye.rotation.y = eyeYaw;
        leftEye.rotation.x = eyePitch;
        rightEye.rotation.y = eyeYaw;
        rightEye.rotation.x = eyePitch;
      }

      // Eyelid position (sleepy / blink)
      let lidOpenOffset = 0.04;
      if (curState === 'disconnected') {
        lidOpenOffset = -0.06; // Fully closed in sleep
      } else if (curState === 'listening') {
        lidOpenOffset = 0.09; // Wide alert eyes
      } else if (curState === 'success') {
        lidOpenOffset = 0.01; // Happy squint
      } else {
        // Normal sleepy sloth idle with blinking
        lidOpenOffset = 0.04 - stateRef.current.blinkProgress * 0.1;
      }

      if (leftUpperLid && rightUpperLid) {
        leftUpperLid.position.y = THREE.MathUtils.lerp(leftUpperLid.position.y, lidOpenOffset, delta * 15.0);
        rightUpperLid.position.y = THREE.MathUtils.lerp(rightUpperLid.position.y, lidOpenOffset, delta * 15.0);
      }

      // --- Mouth & Slow Flash Laugh Animation ---
      stateRef.current.mouthOpen = THREE.MathUtils.lerp(
        stateRef.current.mouthOpen,
        stateRef.current.targetMouthOpen,
        delta * 2.2 // Intentionally slow spread like the Zootopia scene!
      );

      if (jaw) {
        jaw.position.y = -0.22 - stateRef.current.mouthOpen * 0.12;
        jaw.scale.y = 1.0 + stateRef.current.mouthOpen * 0.8;
      }

      // --- Arms Typing Motion when Executing ---
      if (leftArm && rightArm) {
        if (curState === 'executing') {
          leftArm.rotation.x = -0.55 + Math.sin(t * 6.0) * 0.08;
          rightArm.rotation.x = -0.55 + Math.cos(t * 6.0) * 0.08;
        } else {
          leftArm.rotation.x = THREE.MathUtils.lerp(leftArm.rotation.x, -0.55, delta * 3.0);
          rightArm.rotation.x = THREE.MathUtils.lerp(rightArm.rotation.x, -0.55, delta * 3.0);
        }
      }

      // --- Sparkle Particles on Success ---
      if (sparkles) {
        const targetOpacity = curState === 'success' ? 0.9 : 0.0;
        (sparkles.material as THREE.PointsMaterial).opacity = THREE.MathUtils.lerp(
          (sparkles.material as THREE.PointsMaterial).opacity,
          targetOpacity,
          delta * 4.0
        );
        if (curState === 'success') {
          sparkles.rotation.y += delta * 0.6;
        }
      }

      renderer.render(scene, camera);
    };

    animId = requestAnimationFrame(animate);

    // Responsive Resize Handler
    const handleResize = () => {
      if (!container) return;
      const newW = container.clientWidth;
      const newH = container.clientHeight;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    };
    window.addEventListener('resize', handleResize);

    // Cleanup on unmount
    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      if (container && renderer.domElement) {
        try {
          container.removeChild(renderer.domElement);
        } catch {}
      }
      renderer.dispose();
    };
  }, [onFallback]);

  if (!webGlAvailable) {
    return null;
  }

  return (
    <div
      ref={mountRef}
      className={`sloth-3d-canvas state-${state}`}
      style={{
        width: '100%',
        height: '240px',
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      role="img"
      aria-label={`3D Flash Sloth Companion: ${state}`}
    />
  );
};

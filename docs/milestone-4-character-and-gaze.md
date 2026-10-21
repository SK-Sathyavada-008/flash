# Milestone 4: Flash 3D Sloth Companion & Cursor Gaze Synchronization

This document covers the implementation, visual direction, animation system, cursor gaze synchronization protocol, WebGL fallback behavior, and GLB replacement guide for **Milestone 4**.

---

## 1. Visual Direction & Disney's Zootopia DMV Theme

Flash's design directly reflects the iconic DMV (Department of Mammal Vehicles) scene from Disney's *Zootopia*:

- **Character Anatomy & Materials**:
  - **Head & Fur**: Soft warm caramel/taupe procedural fur dome with distinctive silvery-beige parted tuft on top.
  - **Eye Patches**: Dark chocolate eye-mask patches extending laterally from the bridge of the snout.
  - **Eyes & Eyelids**: Expressive warm amber irises, deep pupils, white sclera, specular catchlights, and articulated eyelids that capture Flash's characteristic sleepy heavy-lidded gaze.
  - **Snout**: Dark leathery textured snout with nostrils.
  - **Articulated Jaw**: Opens slowly into Flash's legendary, ultra-wide open-mouth beaming laugh upon task success!
  - **Attire**: Zootopia DMV sage green short-sleeved polo shirt, diagonal striped orange-and-navy necktie, and gold tie clip.
  - **Arms & Counter**: Long pale 3-claw paws resting on a warm wooden DMV service counter with a ceramic mug.
- **Zootopia DMV Palette & UI**:
  - Terracotta and warm wood counter tones (`#b46b38`, `#78350f`).
  - DMV uniform sage green (`#658d68`).
  - Navy and orange tie accents (`#1f2a44`, `#dd5e28`) with gold embellishments (`#facc15`).
  - Playful DMV badge and sloth speed quotes (*"Flash Flash Hundred Yard Dash... You want it when?"*).

---

## 2. Animation System & Task State Mapping

The 3D procedural character in [`Sloth3DCanvas.tsx`](file:///c:/Keerthu/flash/flash/companion/src/components/Sloth3DCanvas.tsx) is driven by real agent events and task execution states:

| State | Character Behavior & Animation | Visual Indicators |
|---|---|---|
| **`idle`** | Gentle breathing (chest and shoulders oscillate at 1.5 rad/s), subtle head sway, occasional slow sloth blinks every 3.5–7 seconds. Eyes smoothly track the Windows mouse cursor. | Golden amber glow aura, *"Flash is ready"*. |
| **`listening`** | Attentive curious head tilt, alert wide eyes (eyelids lift up), subtle lean forward. | Emerald green glow, live speech waveform and transcript. |
| **`thinking`** | Contemplative head cock, eyes roll upward and drift as if pondering a memory from 5 minutes ago, brow furrows slightly. | Amber glow aura, floating thought bubble 💭. |
| **`executing`** | Focused downward gaze toward desk, paws tap rhythmically on the counter (simulating typing on keyboard), head bobs gently. | Electric blue glow, live multi-step task progress list. |
| **`success`** | **The Iconic Flash Smile**: Jaw and mouth slowly spread wide open into a huge joyous laugh over 2.5 seconds, eyes squint happily with celebratory gold sparkle particles! | Bright green glow, celebratory eye sparkles, *"Done!"*. |
| **`failure`** | Sleepy head droop, eyelids half-close apologetically, slow confused head shake. | Coral red glow, error details with retry option. |
| **`stopped`** | Sudden comical rigid freeze, halted instantly by the emergency stop circuit. | Crimson red glow, *"Emergency Stopped"*, Resume button. |
| **`disconnected`** | Sleepy nap state: head slumped forward onto desk, eyelids completely closed in a peaceful slumber with snooze zZz particles. | Desaturated badge, *"Offline / Disconnected"*. |

---

## 3. Desktop Cursor Gaze Synchronization

### Protocol & Normalization
The Windows desktop agent captures the physical mouse position without capturing or transmitting screenshots:
1. **Coordinate Normalization**:
   - `x_norm = max(0.0, min(1.0, mouse_x / screen_width))`
   - `y_norm = max(0.0, min(1.0, mouse_y / screen_height))`
2. **Throttling & Delta Filter**:
   - Samples at 20 Hz (every 50 ms).
   - Only emits an update if $\Delta \ge 0.004$ (0.4% screen travel) to eliminate network jitter and save battery on the phone.
3. **Payload**:
   ```json
   {
     "type": "cursor_gaze",
     "x": 0.4521,
     "y": 0.3814,
     "timestamp": 1792484000.123
   }
   ```
4. **Phone Smoothing (Lerp)**:
   - On the Redmi Android companion, target gaze is mapped to 3D yaw/pitch:
     $$\text{targetGazeX} = (x - 0.5) \times 1.8$$
     $$\text{targetGazeY} = -(y - 0.5) \times 1.4$$
   - Eyeballs and head interpolate using Three.js `MathUtils.lerp(current, target, delta * 3.5)` for smooth, natural sloth motion.
5. **Gaze Toggle Setting**:
   - In Settings (gear icon), users can toggle **"Sync Eyes to Laptop Mouse"** on or off. Toggling off sends `{"type": "set_gaze_enabled", "enabled": false}` to the laptop, pausing tracking and reducing Wi-Fi traffic.

---

## 4. WebGL Fallback & Performance Guardrails

- **Zero GPU Lockup / Low Battery Drain**:
  - The procedural sloth is modeled using optimized low-poly primitives (16–24 segments per part), avoiding complex mesh skinning calculations that drain mobile batteries.
  - Configured with `precision: "mediump"`, `powerPreference: "high-performance"`, and device pixel ratio clamped to `Math.min(window.devicePixelRatio, 2)`.
- **Automatic WebGL Fallback**:
  - If WebGL hardware acceleration is missing or context creation fails, [`Sloth3DCanvas`](file:///c:/Keerthu/flash/flash/companion/src/components/Sloth3DCanvas.tsx) safely catches the error and instantly switches to the 2D vector SVG sloth companion (which also wears the Zootopia DMV green collar and striped tie).
- **Manual 3D / 2D Toggle**:
  - A small floating pill (`3D Sloth` / `2D Mode`) lets users manually toggle between 3D and 2D mode at any time.

---

## 5. Replacing the Procedural Character with a Rigged GLB Model

When a custom rigged 3D sloth model in `.glb` format is ready:
1. Place the `.glb` file in `flash/companion/public/models/flash_sloth.glb`.
2. In `flash/companion/src/components/Sloth3DCanvas.tsx`, replace the primitive assembly with Three.js `GLTFLoader`:
   ```typescript
   import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

   const loader = new GLTFLoader();
   loader.load('/models/flash_sloth.glb', (gltf) => {
     const model = gltf.scene;
     scene.add(model);
     
     // Find bone / morph target references:
     const mixer = new THREE.AnimationMixer(model);
     // Map clip actions: idle, listening, thinking, smile, typing
   });
   ```
3. Bone targets for `head_bone`, `eye_left_bone`, `eye_right_bone`, and morph targets for `mouth_smile` and `eyelids_blink` can simply receive the existing `currentGaze` and `mouthOpen` lerp values calculated in `animate()`.

---

## 6. Automated Verification

- **Backend Tests (62/62 Passed)**:
  - `tests/test_cursor_tracker.py` verifies coordinate normalization, boundary clamping, client registration, and WebSocket toggle commands.
  - All existing action, auth, orchestrator, and security tests continue to pass with 100% green status.
- **Frontend Tests (9/9 Passed)**:
  - `companion.test.tsx` verifies 3D/2D mode switching, WebGL fallback handling, state rendering, and gaze toggle in Settings.
- **Production PWA Build**:
  - Bundled cleanly with Three.js via `npm run build`.

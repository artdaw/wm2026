# Penalty Game Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "⚽ Spiel" third tab with a 3D penalty shootout game (best of 5, slingshot aim) built on Three.js loaded from CDN.

**Architecture:** Two files change — `index.html` gets the tab button, game-view div, overlay HTML, CSS, and two `<script>` tags. `game.js` is a self-contained module: pure physics functions at the top (Node-testable), followed by a Three.js IIFE that only runs in the browser. The render loop starts/stops via a MutationObserver watching the game-view's `active` class.

**Tech Stack:** Three.js r134 (CDN global), vanilla JS, no build step.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `index.html` | Modify | Tab button, game-view div, overlay HTML, CSS, script tags |
| `game.js` | Create | Pure physics functions + Three.js scene + game loop |
| `scripts/test_game_physics.js` | Create | Node.js unit tests for pure physics functions |

---

## Task 1: Wire up the tab in index.html

**Files:**
- Modify: `index.html:27` (view-tabs — add tab button)
- Modify: `index.html:14–93` (style block — add game CSS)
- Modify: `index.html:128–130` (after schedule-view — add game-view)
- Modify: `index.html:435` (before `</body>` — add script tags)

- [ ] **Step 1: Add CSS for game view and overlays**

In `index.html`, inside the `<style>` block, add before the closing `</style>`:

```css
  #game-view{position:relative;overflow:hidden}
  #game-canvas{width:100%;height:100%;display:block;touch-action:none}
  #game-ui{position:absolute;inset:0;pointer-events:none;display:flex;flex-direction:column;align-items:center}
  #game-score{margin-top:10px;background:rgba(15,17,21,.75);border:1px solid var(--line);border-radius:999px;padding:6px 16px;font-size:13px;font-weight:700;color:var(--accent)}
  #game-instruction{margin-top:8px;font-size:12px;color:var(--muted)}
  #game-result{position:absolute;top:42%;left:50%;transform:translate(-50%,-50%);font-size:36px;font-weight:900;text-shadow:0 2px 16px rgba(0,0,0,.9);pointer-events:none}
  #game-over{position:absolute;inset:0;background:rgba(15,17,21,.85);display:none;flex-direction:column;align-items:center;justify-content:center;gap:18px;pointer-events:all}
  #game-over-text{font-size:22px;font-weight:800;color:var(--txt);text-align:center;padding:0 20px}
  #game-replay{padding:13px 32px;border-radius:8px;border:0;background:var(--accent);color:#17110a;font-size:15px;font-weight:800;cursor:pointer}
```

- [ ] **Step 2: Add the "Spiel" tab button**

In `index.html`, find:
```html
        <button class="view-tab" type="button" data-view="schedule">Spielplan</button>
```
Change it to:
```html
        <button class="view-tab" type="button" data-view="schedule">Spielplan</button>
        <button class="view-tab" type="button" data-view="game">⚽ Spiel</button>
```

- [ ] **Step 3: Add the game-view div**

In `index.html`, find:
```html
</div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
```
Change it to:
```html
</div>
  <div class="view" id="game-view">
    <canvas id="game-canvas"></canvas>
    <div id="game-ui">
      <div id="game-score">0 : 0 &middot; Elfmeter 1/5</div>
      <div id="game-instruction">Zieh den Ball und lass los!</div>
      <div id="game-result" style="display:none"></div>
      <div id="game-over" style="display:none">
        <p id="game-over-text"></p>
        <button id="game-replay">Nochmal spielen</button>
      </div>
    </div>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
```

- [ ] **Step 4: Add CDN + game script tags**

In `index.html`, find the closing `</body>` tag and add before it:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r134/three.min.js"></script>
<script src="game.js"></script>
```

- [ ] **Step 5: Create stub game.js to confirm wiring**

Create `/Users/gleb/Developer/wm2026/game.js`:
```javascript
// Stub — replaced in Task 3
console.log('game.js loaded');
```

- [ ] **Step 6: Open browser and verify**

Open `index.html` in a browser (or run `open index.html`). Confirm:
- Three tabs appear: Karte · Spielplan · ⚽ Spiel
- Clicking "⚽ Spiel" shows a black/empty view (canvas not yet initialised — correct)
- Browser console shows `game.js loaded`
- Other two tabs still work normally

- [ ] **Step 7: Commit**

```bash
git add index.html game.js
git commit -m "feat: add Spiel tab scaffold with game-view and overlays"
```

---

## Task 2: Pure physics functions + tests (TDD)

**Files:**
- Create: `scripts/test_game_physics.js`
- Modify: `game.js` (replace stub with physics functions)

- [ ] **Step 1: Create the test file**

Create `/Users/gleb/Developer/wm2026/scripts/test_game_physics.js`:

```javascript
const {
  computeLaunchVelocity, computeTrajectory,
  isGoal, isSaved, stepPhysics,
} = require('../game.js');
const assert = require('assert');
let passed = 0, failed = 0;

function test(name, fn) {
  try { fn(); console.log(`  ✓ ${name}`); passed++; }
  catch (e) { console.error(`  ✗ ${name}: ${e.message}`); failed++; }
}

console.log('\ncomputeLaunchVelocity');
test('drag gives negative vz (toward goal)', () => {
  const v = computeLaunchVelocity(60, -80, 120, 18);
  assert(v.z < 0, `vz should be negative, got ${v.z}`);
});
test('left drag gives positive vx (ball goes right)', () => {
  const v = computeLaunchVelocity(60, 0, 120, 18);
  assert(v.x > 0, `vx should be positive, got ${v.x}`);
});
test('downward drag gives positive vy', () => {
  const v = computeLaunchVelocity(0, -80, 120, 18);
  assert(v.y > 0, `vy should be positive, got ${v.y}`);
});
test('zero drag still gives minimum upward velocity', () => {
  const v = computeLaunchVelocity(0, 0, 120, 18);
  assert(v.y >= 3.0, `vy should be >= 3, got ${v.y}`);
});
test('vz magnitude does not exceed maxSpeed', () => {
  const v = computeLaunchVelocity(120, -120, 120, 18);
  assert(Math.abs(v.z) <= 18 + 0.01, `|vz| must not exceed 18, got ${v.z}`);
});

console.log('\ncomputeTrajectory');
test('returns array of [x,y,z] triples', () => {
  const v = computeLaunchVelocity(0, -80, 120, 18);
  const pts = computeTrajectory({ x: 0, y: 0.11, z: 11 }, v, 30, 0.06);
  assert(pts.length > 0, 'need at least one point');
  assert(Array.isArray(pts[0]) && pts[0].length === 3, 'each element must be [x,y,z]');
});
test('y never drops below ball radius', () => {
  const v = { x: 0, y: 4, z: -15 };
  const pts = computeTrajectory({ x: 0, y: 0.11, z: 11 }, v, 50, 0.06);
  pts.forEach(([, y], i) => assert(y >= 0.11 - 0.001, `pt ${i} y=${y} below radius`));
});
test('stops before or at goal line', () => {
  const v = { x: 0, y: 8, z: -20 };
  const pts = computeTrajectory({ x: 0, y: 0.11, z: 11 }, v, 60, 0.06);
  pts.forEach(([, , z]) => assert(z >= -0.05, `z=${z} overshot goal`));
});

console.log('\nisGoal');
test('centre of goal is a goal', () => assert(isGoal(0, 1.2)));
test('outside left post is not a goal', () => assert(!isGoal(-4.0, 1.2)));
test('outside right post is not a goal', () => assert(!isGoal(4.0, 1.2)));
test('above crossbar is not a goal', () => assert(!isGoal(0, 2.5)));
test('at ground level is not a goal', () => assert(!isGoal(0, 0.05)));
test('top corner is a goal', () => assert(isGoal(3.0, 2.2)));

console.log('\nisSaved');
test('ball at keeper position is saved', () => assert(isSaved(1.5, 0.9, 1.5)));
test('ball 3m from keeper is not saved', () => assert(!isSaved(3.0, 0.9, 0)));
test('ball high above keeper is not saved', () => assert(!isSaved(0, 2.0, 0)));

console.log('\nstepPhysics');
test('gravity decreases vy each step', () => {
  const { vel } = stepPhysics({ x: 0, y: 5, z: 11 }, { x: 0, y: 10, z: -15 }, 0.1);
  const expected = 10 + (-9.8) * 0.1;
  assert(Math.abs(vel.y - expected) < 0.001, `vy should be ~${expected.toFixed(2)}, got ${vel.y}`);
});
test('ball moves toward goal', () => {
  const { pos } = stepPhysics({ x: 0, y: 2, z: 11 }, { x: 0, y: 5, z: -15 }, 0.1);
  assert(pos.z < 11, `z should decrease, got ${pos.z}`);
});
test('vx is unchanged (no air resistance)', () => {
  const { vel } = stepPhysics({ x: 0, y: 0, z: 0 }, { x: 3, y: 0, z: 0 }, 0.1);
  assert(Math.abs(vel.x - 3) < 0.001, `vx should stay 3, got ${vel.x}`);
});

console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
```

- [ ] **Step 2: Run tests — expect failure**

```bash
~/.nvm/versions/node/v22.0.0/bin/node scripts/test_game_physics.js 2>&1 | head -5
```

Expected: `TypeError: computeLaunchVelocity is not a function` (game.js is still the stub)

- [ ] **Step 3: Replace game.js with physics functions**

Replace the entire content of `/Users/gleb/Developer/wm2026/game.js`:

```javascript
// ─── Constants ────────────────────────────────────────────────────────────────
const GRAVITY    = -9.8;
const PENALTY_Z  = 11;   // ball start z (penalty spot 11m from goal)
const GOAL_Z     = 0;    // goal line
const BALL_R     = 0.11; // ball radius in metres
const GOAL_HALF  = 3.66; // half goal width (7.32m total)
const GOAL_H     = 2.44; // crossbar height

// ─── Pure physics (no THREE dependency) ──────────────────────────────────────

function computeLaunchVelocity(dragX, dragY, maxDrag, maxSpeed) {
  // dragX = startX - curX: positive → dragged left → ball goes right
  // dragY = startY - curY: negative → dragged down → ball goes up
  const power = Math.min(Math.hypot(dragX, dragY) / maxDrag, 1.0);
  return {
    x:  (dragX / maxDrag) * maxSpeed * 0.7,
    y:  Math.max(-dragY / maxDrag, 0) * maxSpeed * 0.8 + 3.0, // min 3 m/s upward
    z:  -(power * maxSpeed),                                    // toward goal (-z)
  };
}

function computeTrajectory(startPos, vel, steps, dt) {
  const pts = [];
  let p = { x: startPos.x, y: startPos.y, z: startPos.z };
  let v = { x: vel.x, y: vel.y, z: vel.z };
  for (let i = 0; i < steps; i++) {
    pts.push([p.x, Math.max(p.y, BALL_R), p.z]);
    v = { x: v.x, y: v.y + GRAVITY * dt, z: v.z };
    p = { x: p.x + v.x * dt, y: p.y + v.y * dt, z: p.z + v.z * dt };
    if (p.z <= GOAL_Z || p.y < 0) break;
  }
  return pts;
}

function isGoal(x, y) {
  return Math.abs(x) < GOAL_HALF && y > BALL_R && y < GOAL_H;
}

function isSaved(ballX, ballY, keeperX) {
  return Math.abs(ballX - keeperX) < 0.55 && ballY > 0.1 && ballY < 1.6;
}

function stepPhysics(pos, vel, dt) {
  return {
    pos: { x: pos.x + vel.x * dt, y: pos.y + vel.y * dt, z: pos.z + vel.z * dt },
    vel: { x: vel.x, y: vel.y + GRAVITY * dt, z: vel.z },
  };
}

// Node.js export for tests
if (typeof module !== 'undefined') {
  module.exports = { computeLaunchVelocity, computeTrajectory, isGoal, isSaved, stepPhysics };
}

// ─── Three.js game (browser only) ────────────────────────────────────────────
(function initGame() {
  if (typeof THREE === 'undefined') return;
  // Scene code added in Task 3
})();
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
~/.nvm/versions/node/v22.0.0/bin/node scripts/test_game_physics.js
```

Expected output (all lines start with `✓`):
```
computeLaunchVelocity
  ✓ drag gives negative vz (toward goal)
  ✓ left drag gives positive vx (ball goes right)
  ✓ downward drag gives positive vy
  ✓ zero drag still gives minimum upward velocity
  ✓ vz magnitude does not exceed maxSpeed

computeTrajectory
  ✓ returns array of [x,y,z] triples
  ✓ y never drops below ball radius
  ✓ stops before or at goal line

isGoal
  ✓ centre of goal is a goal
  ✓ outside left post is not a goal
  ✓ outside right post is not a goal
  ✓ above crossbar is not a goal
  ✓ at ground level is not a goal
  ✓ top corner is a goal

isSaved
  ✓ ball at keeper position is saved
  ✓ ball 3m from keeper is not saved
  ✓ ball high above keeper is not saved

stepPhysics
  ✓ gravity decreases vy each step
  ✓ ball moves toward goal
  ✓ vx is unchanged (no air resistance)

20 passed, 0 failed
```

- [ ] **Step 5: Commit**

```bash
git add game.js scripts/test_game_physics.js
git commit -m "feat: add physics functions with tests"
```

---

## Task 3: Complete Three.js game

**Files:**
- Modify: `game.js` — replace the empty `initGame` IIFE with the full scene + game loop

- [ ] **Step 1: Replace the `initGame` IIFE with the full game**

In `game.js`, replace:
```javascript
// ─── Three.js game (browser only) ────────────────────────────────────────────
(function initGame() {
  if (typeof THREE === 'undefined') return;
  // Scene code added in Task 3
})();
```

With:
```javascript
// ─── Three.js game (browser only) ────────────────────────────────────────────
(function initGame() {
  if (typeof THREE === 'undefined') return;

  const canvas  = document.getElementById('game-canvas');
  const gameView = document.getElementById('game-view');

  // ── Renderer ──────────────────────────────────────────────────────────────
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setClearColor(0x0f1115);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  // ── Scene & Camera ────────────────────────────────────────────────────────
  const scene  = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
  camera.position.set(0, 1.5, 14);
  camera.lookAt(0, 1.2, 0);

  // ── Lighting ──────────────────────────────────────────────────────────────
  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const sun = new THREE.DirectionalLight(0xffffff, 0.8);
  sun.position.set(-5, 10, 10);
  scene.add(sun);

  // ── Pitch ─────────────────────────────────────────────────────────────────
  const pitchMesh = new THREE.Mesh(
    new THREE.PlaneGeometry(20, 30),
    new THREE.MeshLambertMaterial({ color: 0x1a3a1a })
  );
  pitchMesh.rotation.x = -Math.PI / 2;
  scene.add(pitchMesh);

  // ── Goal ──────────────────────────────────────────────────────────────────
  const postMat = new THREE.MeshLambertMaterial({ color: 0xffffff });
  function box(w, h, d, x, y, z) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), postMat);
    m.position.set(x, y, z);
    return m;
  }
  scene.add(
    box(0.12, 2.44, 0.12, -3.66, 1.22, 0),  // left post
    box(0.12, 2.44, 0.12,  3.66, 1.22, 0),  // right post
    box(7.44, 0.12, 0.12,  0,    2.44, 0)   // crossbar
  );
  const net = new THREE.Mesh(
    new THREE.PlaneGeometry(7.32, 2.44, 18, 8),
    new THREE.MeshBasicMaterial({ color: 0xcccccc, transparent: true, opacity: 0.18, wireframe: true })
  );
  net.position.set(0, 1.22, -0.8);
  scene.add(net);

  // ── Ball ──────────────────────────────────────────────────────────────────
  const ball = new THREE.Mesh(
    new THREE.SphereGeometry(BALL_R, 16, 16),
    new THREE.MeshLambertMaterial({ color: 0xe8eaed })
  );
  scene.add(ball);

  // ── Goalkeeper ────────────────────────────────────────────────────────────
  const keeper = new THREE.Group();
  const torso  = new THREE.Mesh(new THREE.BoxGeometry(0.7, 1.0, 0.3), new THREE.MeshLambertMaterial({ color: 0xe8462a }));
  torso.position.y = 0.5;
  const head   = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.35, 0.35), new THREE.MeshLambertMaterial({ color: 0xf5c5a0 }));
  head.position.y = 1.18;
  keeper.add(torso, head);
  keeper.position.set(0, 0, 0.3);
  scene.add(keeper);

  // ── Trajectory preview ────────────────────────────────────────────────────
  const trajGeo  = new THREE.BufferGeometry();
  const trajLine = new THREE.Line(
    trajGeo,
    new THREE.LineDashedMaterial({ color: 0xffcf33, dashSize: 0.25, gapSize: 0.12 })
  );
  trajLine.visible = false;
  scene.add(trajLine);

  // ── UI refs ───────────────────────────────────────────────────────────────
  const uiScore       = document.getElementById('game-score');
  const uiInstruction = document.getElementById('game-instruction');
  const uiResult      = document.getElementById('game-result');
  const uiOver        = document.getElementById('game-over');
  const uiOverText    = document.getElementById('game-over-text');
  document.getElementById('game-replay').addEventListener('click', resetGame);

  // ── Game state ────────────────────────────────────────────────────────────
  const MAX_DRAG  = 120; // px
  const MAX_SPEED = 18;  // m/s
  const KICKS_MAX = 5;
  const BALL_START = { x: 0, y: BALL_R, z: PENALTY_Z };

  let state       = 'idle'; // idle | aiming | flying | result | gameover
  let goals       = 0, saved = 0, kicks = 0;
  let dragStart   = null, dragCur = null;
  let ballVel     = null;
  let keeperTgt   = null;
  let resultTimer = 0;
  let rafId       = null, lastTime = null;

  function resetBall() {
    ball.position.set(BALL_START.x, BALL_START.y, BALL_START.z);
    ball.rotation.set(0, 0, 0);
    keeper.position.x = 0;
    trajLine.visible = false;
  }

  function resetGame() {
    goals = 0; saved = 0; kicks = 0;
    resetBall();
    setState('idle');
  }

  function setState(s) {
    state = s;
    uiInstruction.style.display = s === 'idle'     ? 'block' : 'none';
    uiResult.style.display      = s === 'result'   ? 'block' : 'none';
    uiOver.style.display        = s === 'gameover' ? 'flex'  : 'none';
    updateScore();
  }

  function updateScore() {
    const kick = Math.min(kicks + 1, KICKS_MAX);
    uiScore.textContent = `${goals} : ${saved} · Elfmeter ${kick}/${KICKS_MAX}`;
  }

  function handleResult(outcome) {
    if (outcome === 'goal') goals++; else saved++;
    kicks++;
    const labels = { goal: 'TOR! ⚽', saved: 'Gehalten! 🧤', miss: 'Vergeben! 😬' };
    uiResult.textContent = labels[outcome] || 'Vergeben!';
    resultTimer = 0;
    setState('result');
  }

  function updateTrajectory() {
    if (!dragStart || !dragCur) return;
    const dx = dragStart.x - dragCur.x;
    const dy = dragStart.y - dragCur.y;
    if (Math.hypot(dx, dy) < 5) { trajLine.visible = false; return; }
    const vel = computeLaunchVelocity(dx, dy, MAX_DRAG, MAX_SPEED);
    const pts = computeTrajectory(BALL_START, vel, 30, 0.06);
    if (!pts.length) return;
    const flat = new Float32Array(pts.length * 3);
    pts.forEach(([x, y, z], i) => { flat[i * 3] = x; flat[i * 3 + 1] = y; flat[i * 3 + 2] = z; });
    trajGeo.setAttribute('position', new THREE.BufferAttribute(flat, 3));
    trajGeo.setDrawRange(0, pts.length);
    trajGeo.attributes.position.needsUpdate = true;
    trajLine.computeLineDistances();
    trajLine.visible = true;
  }

  // ── Game tick ─────────────────────────────────────────────────────────────
  function tick(ts) {
    rafId = requestAnimationFrame(tick);
    const dt = lastTime ? Math.min((ts - lastTime) / 1000, 0.05) : 0.016;
    lastTime = ts;

    if (state === 'flying') {
      const { pos, vel } = stepPhysics(
        { x: ball.position.x, y: ball.position.y, z: ball.position.z },
        ballVel, dt
      );
      ball.position.set(pos.x, Math.max(pos.y, BALL_R), pos.z);
      ballVel = vel;
      // Spin proportional to velocity
      ball.rotation.x -= vel.z * dt * 2;
      ball.rotation.z += vel.x * dt * 2;
      // Keeper dives at fixed speed
      const kdx   = keeperTgt.x - keeper.position.x;
      const kstep = keeperTgt.speed * dt;
      keeper.position.x += Math.sign(kdx) * Math.min(Math.abs(kdx), kstep);

      // Check goal-line crossing
      if (pos.z <= GOAL_Z + 0.05) {
        let outcome;
        if (!isGoal(pos.x, pos.y))             outcome = 'miss';
        else if (isSaved(pos.x, pos.y, keeper.position.x)) outcome = 'saved';
        else                                    outcome = 'goal';
        handleResult(outcome);
      }
      // Hit ground before reaching goal
      if (pos.y <= BALL_R && pos.z > GOAL_Z + 0.5) {
        handleResult('miss');
      }
    }

    if (state === 'result') {
      resultTimer += dt;
      if (resultTimer > 1.3) {
        if (kicks >= KICKS_MAX) {
          uiOverText.textContent = `${goals} von ${KICKS_MAX} Elfmeter verwandelt!`;
          setState('gameover');
        } else {
          resetBall();
          setState('idle');
        }
      }
    }

    // Resize canvas to match CSS size
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (canvas.width !== w || canvas.height !== h) {
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }

    renderer.render(scene, camera);
  }

  // ── Input ─────────────────────────────────────────────────────────────────
  function getXY(e) {
    const rect = canvas.getBoundingClientRect();
    const src  = e.touches ? e.touches[0] : e;
    return { x: src.clientX - rect.left, y: src.clientY - rect.top };
  }

  function onDown(e) {
    if (state !== 'idle') return;
    e.preventDefault();
    dragStart = getXY(e);
    dragCur   = { ...dragStart };
    state     = 'aiming';
    uiInstruction.style.display = 'none';
  }

  function onMove(e) {
    if (state !== 'aiming') return;
    e.preventDefault();
    dragCur = getXY(e);
    updateTrajectory();
  }

  function onUp(e) {
    if (state !== 'aiming') return;
    e.preventDefault();
    const dx = dragStart.x - dragCur.x;
    const dy = dragStart.y - dragCur.y;
    dragStart = null; dragCur = null;
    if (Math.hypot(dx, dy) < 10) { setState('idle'); return; } // too small — cancel
    ballVel  = computeLaunchVelocity(dx, dy, MAX_DRAG, MAX_SPEED);
    keeperTgt = { x: (Math.random() < 0.5 ? -1 : 1) * (0.9 + Math.random() * 1.6), speed: 4 + Math.random() * 3 };
    trajLine.visible = false;
    state = 'flying';
  }

  canvas.addEventListener('mousedown',  onDown);
  canvas.addEventListener('mousemove',  onMove);
  canvas.addEventListener('mouseup',    onUp);
  canvas.addEventListener('touchstart', onDown, { passive: false });
  canvas.addEventListener('touchmove',  onMove, { passive: false });
  canvas.addEventListener('touchend',   onUp,   { passive: false });

  // ── Lifecycle: start/stop render loop with tab visibility ─────────────────
  new MutationObserver(() => {
    const active = gameView.classList.contains('active');
    if (active && !rafId) {
      lastTime = null;
      resetGame();
      rafId = requestAnimationFrame(tick);
    } else if (!active && rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }).observe(gameView, { attributes: true, attributeFilter: ['class'] });
})();
```

- [ ] **Step 2: Run tests to confirm physics still pass**

```bash
~/.nvm/versions/node/v22.0.0/bin/node scripts/test_game_physics.js
```

Expected: `20 passed, 0 failed`

- [ ] **Step 3: Open browser and do a full play-through**

```bash
open /Users/gleb/Developer/wm2026/index.html
```

Check each of these:
- Click "⚽ Spiel" tab → 3D scene appears (green pitch, white goal, ball on spot, red keeper)
- Drag anywhere on canvas → dashed yellow arc preview appears
- Release → ball flies toward goal; keeper dives
- "TOR! ⚽" / "Gehalten! 🧤" / "Vergeben! 😬" flashes briefly
- After 5 kicks → game-over overlay with score + "Nochmal spielen"
- Click "Nochmal spielen" → resets and plays again
- Switch to Karte tab and back → scene resets and works again
- Mobile-style: on-screen drag works (test via DevTools device mode)

- [ ] **Step 4: Commit**

```bash
git add game.js
git commit -m "feat: add Three.js penalty shootout game"
```

- [ ] **Step 5: Push**

```bash
git push
```

Pages will rebuild automatically via the existing deploy workflow.

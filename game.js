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
    p = { x: p.x + v.x * dt, y: p.y + v.y * dt, z: p.z + v.z * dt };  // position first
    v = { x: v.x, y: v.y + GRAVITY * dt, z: v.z };  // then gravity
    if (p.z <= GOAL_Z || p.y < 0) break;
  }
  return pts;
}

function isGoal(x, y) {
  return Math.abs(x) < GOAL_HALF && y > BALL_R && y < GOAL_H;
}

function isSaved(ballX, ballY, keeperX) {
  return Math.abs(ballX - keeperX) < 0.55 && ballY > 0.1 && ballY < 1.9;
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
  const TRAJ_STEPS = 30;
  const trajPts  = new Float32Array(TRAJ_STEPS * 3);
  const trajAttr = new THREE.BufferAttribute(trajPts, 3).setUsage(THREE.DynamicDrawUsage);
  trajGeo.setAttribute('position', trajAttr);
  trajGeo.setDrawRange(0, 0);

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
    pts.forEach(([x, y, z], i) => { trajPts[i * 3] = x; trajPts[i * 3 + 1] = y; trajPts[i * 3 + 2] = z; });
    trajGeo.setDrawRange(0, pts.length);
    trajAttr.needsUpdate = true;
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
      else if (pos.y <= BALL_R && pos.z > GOAL_Z + 0.5) {
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

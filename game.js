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
  // Scene code added in Task 3
})();

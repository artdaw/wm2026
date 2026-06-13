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

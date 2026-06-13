# Penalty Shootout Mini-Game Design

**Date:** 2026-06-14  
**Status:** Approved

## Goal

Add a browser-based penalty shootout game as a third tab on the WM 2026 Berlin site. Players drag back the ball (slingshot) and release to shoot — best of 5. Built with Three.js (CDN) for a 3D behind-the-ball perspective. No build toolchain needed.

## Files

| File | Action | Responsibility |
|---|---|---|
| `index.html` | Modify | Add tab button, game-view div, Two script tags |
| `game.js` | Create | Self-contained Three.js game — scene, physics, input, state |

No other files change.

## index.html Changes

1. Add third tab button inside `.view-tabs`:
   ```html
   <button class="view-tab" type="button" data-view="game">⚽ Spiel</button>
   ```

2. Add game view div after `#schedule-view`:
   ```html
   <div class="view" id="game-view">
     <canvas id="game-canvas"></canvas>
   </div>
   ```

3. Add at bottom of `<body>`, before closing tag:
   ```html
   <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r167/three.min.js"></script>
   <script src="game.js"></script>
   ```

The existing tab-switching JS (`data-view` / `.view.active`) already handles showing/hiding the new view without changes.

## 3D Scene

**Camera:** Positioned 3m behind and 1m above the ball, angled at the goal. Classic broadcast penalty-kick POV.

**Objects:**
- **Pitch**: `PlaneGeometry`, rotated flat, dark green `#1a3a1a`
- **Goal posts & crossbar**: white `BoxGeometry` pieces assembled into a goal shape
- **Net**: semi-transparent `MeshBasicMaterial` plane behind the goal line
- **Ball**: `SphereGeometry`, dark leather colour `#2a1f0e`, rests at penalty spot
- **Goalkeeper**: two `BoxGeometry` meshes (torso + head), coloured `--accent2` red `#e8462a`. No rigging — translates only.

**Lighting:** Ambient (`#ffffff`, intensity 0.6) + directional from above-left (`#ffffff`, intensity 0.8). Night-match feel.

**Renderer:** `THREE.WebGLRenderer` on `#game-canvas`. Clear colour `#0f1115` (matches `--bg`). Resizes with window. Render loop runs only when game-view tab is active (paused otherwise).

## Slingshot Mechanic

**Input:** Mouse (`mousedown / mousemove / mouseup`) and touch (`touchstart / touchmove / touchend`) anywhere on the canvas. Drag vector = `startPoint - currentPoint` (inverted so dragging left sends ball right).

**Power & direction:** Drag vector magnitude → launch speed (clamped to `maxDrag = 120px` → `maxSpeed = 18 m/s`). Drag vector angle → horizontal + vertical launch angle.

**Trajectory preview:** While dragging, a `THREE.Line` of 20 computed points shows the parabolic arc in world space. Updates every frame during aiming. Hidden on release.

**Flight physics (per frame):**
```
velocity.y -= 9.8 * deltaTime
position += velocity * deltaTime
```
Flight duration ~0.8s to reach goal line (12m away).

**Goal detection:** When ball z-position crosses goal line (z = 0): check if ball x is within post width (±3.66m) and ball y is below crossbar (≤2.44m). If yes: GOAL. Otherwise: MISS.

## Goalkeeper AI

- On ball release: picks random target x in range `[-2.8, 2.8]` and random dive speed `[4, 7] m/s`.
- Translates toward target over ~0.4s.
- **Save detection:** If goalkeeper bounding box (`±0.6m x, ±0.9m y`) intersects ball position at goal-line crossing: SAVED.

## State Machine

```
idle → aiming → flying → result → idle   (repeats 5 times)
                                     ↓ after 5 kicks
                                  game-over
```

| State | Duration | Description |
|---|---|---|
| `idle` | until drag | Ball at spot, instruction shown |
| `aiming` | until release | Drag active, arc preview shown |
| `flying` | ~0.8s | Ball in motion, keeper diving |
| `result` | 1.2s | Overlay shows TOR / Gehalten / Vergeben |
| `game-over` | until replay | Final score overlay + Nochmal button |

## HTML Overlays (not Three.js)

Absolutely-positioned `<div>` elements over the canvas. Toggled with `display` based on state.

| Element | Text | Visible in state |
|---|---|---|
| `#game-instruction` | "Zieh den Ball und lass los!" | `idle` |
| `#game-result` | "TOR! ⚽" / "Gehalten! 🧤" / "Vergeben! 😬" | `result` |
| `#game-score` | "2 : 1 (Kick 3/5)" | always during play |
| `#game-over` | "3 von 5 Elfmeter verwandelt! [Nochmal]" | `game-over` |

## Lifecycle

`game.js` exports nothing. On load it attaches a `MutationObserver` (or listens to the existing tab-click events) to detect when `#game-view` gains/loses the `active` class:
- **Gained active**: initialise scene if first visit, start `requestAnimationFrame` loop
- **Lost active**: cancel animation frame, pause renderer

This ensures zero GPU cost when the user is on Karte or Spielplan.

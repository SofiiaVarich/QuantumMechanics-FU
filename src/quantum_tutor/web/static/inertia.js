'use strict';
// Radians/second; exact exponential integration makes travel independent of FPS.
window.AtlasInertia = {
  step(velocity, dt) {
    const friction = 1.15, threshold = .004;
    if (Math.abs(velocity) <= threshold || dt <= 0) return {velocity: dt <= 0 ? velocity : 0, delta: 0};
    const duration = Math.min(dt, Math.log(Math.abs(velocity) / threshold) / friction);
    const next = velocity * Math.exp(-friction * duration);
    return {velocity: duration < dt ? 0 : next, delta: (velocity - next) / friction};
  },
  release(samples, now, reduced = false) {
    if (reduced || samples.length < 2 || now - samples.at(-1).t > 90) return {x: 0, y: 0};
    const recent = samples.filter(s => now - s.t <= 120);
    if (recent.length < 2) return {x: 0, y: 0};
    const first = recent[0], last = recent.at(-1), dt = (last.t - first.t) / 1000;
    if (dt < .008) return {x: 0, y: 0};
    const clamp = v => Math.max(-6, Math.min(6, v));
    return {x: clamp((last.x-first.x)*.01/dt), y: clamp((last.y-first.y)*.01/dt)};
  }
};

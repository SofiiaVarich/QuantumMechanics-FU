/** Quantum Tutor — polyphonic metallic-ball sound engine (no dependencies). */
'use strict';
window.MetalBallAudio = class MetalBallAudio {
  constructor({ maxVoices = 32, volume = 0.32 } = {}) {
    this.ctx = null;
    this.master = null;
    this.maxVoices = Math.floor(this._clamp(maxVoices, 1, 32));
    this.disposed = false;
    this.timers = new Set();
    this.volume = this._clamp(volume);
    this.muted = false;
    this.voices = new Set();
    this.rolling = new Map();
    this.lastImpact = new Map();
    this.noiseBuffer = null;
  }

  _clamp(value, low = 0, high = 1) { return Math.max(low, Math.min(high, Number.isFinite(value) ? value : low)); }

  async unlock(event) {
    if (this.disposed || event?.isTrusted !== true || !['pointerdown', 'click'].includes(event.type)) return false;
    try {
    if (!this.ctx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return false;
      this.ctx = new AudioContext();
      this.master = this.ctx.createGain();
      this.master.gain.value = this.muted ? 0 : this.volume;
      this.master.connect(this.ctx.destination);
      const buffer = this.ctx.createBuffer(1, this.ctx.sampleRate * 2, this.ctx.sampleRate);
      const samples = buffer.getChannelData(0);
      for (let i = 0; i < samples.length; i++) samples[i] = Math.random() * 2 - 1;
      this.noiseBuffer = buffer;
    }
    // Safari can report "interrupted" after an audio-route change.
    if (this.ctx.state === 'suspended' || this.ctx.state === 'interrupted') await this.ctx.resume();
    return !this.disposed && this.ctx?.state === 'running';
    } catch (_) { return false; }
  }

  setMuted(value) {
    this.muted = Boolean(value);
    if (this.muted) this.stopAll();
    if (this.master) this.master.gain.setTargetAtTime(this.muted ? 0 : this.volume, this.ctx.currentTime, 0.02);
  }

  setVolume(value) {
    this.volume = this._clamp(value);
    if (this.master) this.master.gain.setTargetAtTime(this.muted ? 0 : this.volume, this.ctx.currentTime, 0.02);
  }

  _pan(x = 0.5) {
    const pan = this.ctx.createStereoPanner ? this.ctx.createStereoPanner() : this.ctx.createGain();
    if (pan.pan) pan.pan.value = this._clamp(x) * 2 - 1;
    pan.connect(this.master);
    return pan;
  }

  _voice(duration, x) {
    if (!this.ctx || this.muted || this.voices.size >= this.maxVoices) return null;
    const output = this._pan(x);
    const voice = { output, nodes: [], stop: () => {} };
    this.voices.add(voice);
    let timeout;
    voice.stop = () => {
      clearTimeout(timeout);
      this.timers.delete(timeout);
      voice.nodes.forEach(node => { try { node.stop(); } catch (_) {} try { node.disconnect(); } catch (_) {} });
      output.disconnect();
      this.voices.delete(voice);
    };
    timeout = setTimeout(voice.stop, Math.ceil((duration + 0.15) * 1000));
    this.timers.add(timeout);
    return voice;
  }

  /** Small metallic bowling-ball tap. intensity is normalized to 0..1. */
  impact(ballId, { intensity = 0.5, x = 0.5, type = 'metal' } = {}) {
    if (!this.ctx || this.ctx.state !== 'running' || this.muted) return;
    const now = this.ctx.currentTime;
    const key = String(ballId);
    if (now - (this.lastImpact.get(key) ?? -10) < 0.055) return;
    if (this.lastImpact.size >= 128) this.lastImpact.clear();
    this.lastImpact.set(key, now);
    const force = this._clamp(intensity, 0.05, 1);
    const duration = 0.22 + force * 0.35;
    const voice = this._voice(duration, x);
    if (!voice) return;
    const base = (type === 'experiment' ? 260 : 190) * (0.94 + Math.random() * 0.12);
    const modes = [1, 1.52, 2.17, 3.08];
    const nowTime = now + 0.002;
    modes.forEach((ratio, index) => {
      const osc = this.ctx.createOscillator();
      osc.type = index === 0 ? 'sine' : 'triangle';
      osc.frequency.setValueAtTime(base * ratio * (1 + force * 0.06), nowTime);
      osc.frequency.exponentialRampToValueAtTime(base * ratio * 0.94, nowTime + duration);
      const gain = this.ctx.createGain();
      const level = (0.20 * force) / (index + 1.4);
      gain.gain.setValueAtTime(0.0001, nowTime);
      gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, level), nowTime + 0.006);
      gain.gain.exponentialRampToValueAtTime(0.0001, nowTime + duration * (1 - index * 0.13));
      osc.connect(gain).connect(voice.output);
      osc.start(nowTime);
      osc.stop(nowTime + duration + 0.01);
      voice.nodes.push(osc, gain);
    });
    // Brief, filtered impact noise provides the physical 'clonk'.
    const noise = this.ctx.createBufferSource();
    noise.buffer = this.noiseBuffer;
    const filter = this.ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = 700 + force * 1300;
    filter.Q.value = 0.7;
    const noiseGain = this.ctx.createGain();
    noiseGain.gain.setValueAtTime(0.10 * force, nowTime);
    noiseGain.gain.exponentialRampToValueAtTime(0.0001, nowTime + 0.045);
    noise.connect(filter).connect(noiseGain).connect(voice.output);
    noise.start(nowTime);
    noise.stop(nowTime + 0.055);
    voice.nodes.push(noise, filter, noiseGain);
  }

  /** A single collision produces one impact; use the midpoint for stereo position. */
  collision(ballA, ballB, { relativeSpeed = 0.5, x = 0.5 } = {}) {
    this.impact(`${ballA}:${ballB}`, { intensity: relativeSpeed, x });
  }

  /** Continuous rolling sound per ball. velocity normalized 0..1. */
  setRolling(ballId, { velocity = 0, x = 0.5 } = {}) {
    if (this.disposed || this.muted || !this.ctx || this.ctx.state !== 'running') return;
    const id = String(ballId);
    const speed = this._clamp(velocity);
    let roll = this.rolling.get(id);
    if (speed < 0.015) {
      if (roll) this.stopRolling(id);
      return;
    }
    if (!roll) {
      if (this.rolling.size >= this.maxVoices) return;
      const source = this.ctx.createBufferSource();
      source.buffer = this.noiseBuffer;
      source.loop = true;
      const filter = this.ctx.createBiquadFilter();
      filter.type = 'lowpass';
      const gain = this.ctx.createGain();
      gain.gain.value = 0;
      const panner = this._pan(x);
      source.connect(filter).connect(gain).connect(panner);
      source.start();
      roll = { source, filter, gain, panner };
      this.rolling.set(id, roll);
    }
    const t = this.ctx.currentTime;
    roll.filter.frequency.setTargetAtTime(120 + speed * 1350, t, 0.04);
    roll.gain.gain.setTargetAtTime(this.muted ? 0 : 0.045 * speed, t, 0.04);
    if (roll.panner.pan) roll.panner.pan.setTargetAtTime(this._clamp(x) * 2 - 1, t, 0.04);
  }

  stopRolling(ballId) {
    const id = String(ballId);
    const roll = this.rolling.get(id);
    if (!roll) return;
    this.rolling.delete(id);
    try { roll.source.stop(); } catch (_) {}
    for (const node of [roll.source, roll.filter, roll.gain, roll.panner]) node.disconnect();
  }

  stopAll() {
    for (const id of this.rolling.keys()) this.stopRolling(id);
    for (const voice of [...this.voices]) voice.stop();
  }

  async dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.stopAll();
    for (const timer of this.timers) clearTimeout(timer);
    this.timers.clear();
    this.lastImpact.clear();
    const context = this.ctx;
    this.ctx = null;
    this.master?.disconnect();
    this.master = this.noiseBuffer = null;
    try { if (context) await context.close(); } catch (_) {}
  }
};

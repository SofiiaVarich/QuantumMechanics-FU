'use strict';
(() => {
  const asset = new URL('crystal-crumple.mp3', document.currentScript?.src || new URL('crystal-audio.js', window.location.href)).href;
  let bufferPromise = null;
  function bufferFor(context) {
    if (!bufferPromise) {
      bufferPromise = fetch(asset).then(response => {
        if (!response.ok) throw new Error('Crystal audio unavailable');
        return response.arrayBuffer();
      }).then(bytes => context.decodeAudioData(bytes)).catch(error => {
        bufferPromise = null;
        throw error;
      });
    }
    return bufferPromise;
  }
  window.createCrystalAudio = function () {
    let context, source, gain, filter, timer;
    let active = false, disposed = false, generation = 0, muted = false;
    let speed = 0, pressure = .5;
    try { muted = localStorage.getItem('crystal-muted') === 'true'; } catch (_) {}
    const clamp = (value, low, high) => Math.max(low, Math.min(high, Number.isFinite(value) ? value : low));
    function silence(immediate = false) {
      if (!source) return;
      const old = source;
      source = null;
      const oldGain = gain, oldFilter = filter;
      oldGain.gain.cancelScheduledValues(context.currentTime);
      oldGain.gain.setTargetAtTime(0, context.currentTime, immediate ? .001 : .025);
      old.stop(context.currentTime + (immediate ? 0 : .15));
      old.onended = () => { old.disconnect(); oldGain.disconnect(); oldFilter.disconnect(); };
    }
    function update(motion = {}) {
      speed = clamp(motion.speed, 0, 2000);
      pressure = clamp(motion.pressure ?? .5, 0, 1);
      if (!active || !source || muted) return;
      const intensity = speed / 2000;
      const now = context.currentTime;
      gain.gain.setTargetAtTime(.012 + .16 * intensity * (.3 + .7 * pressure), now, .025);
      source.playbackRate.setTargetAtTime(.65 + 1.05 * intensity + .15 * pressure, now, .04);
      filter.frequency.setTargetAtTime(650 + 6350 * intensity + 1000 * pressure, now, .04);
      clearTimeout(timer);
      // A stationary held pointer returns to a quiet texture, even without pointermove.
      if (speed) timer = setTimeout(() => update({ speed: 0, pressure }), 100);
    }
    function end(immediate = false) {
      active = false; generation++; clearTimeout(timer); silence(immediate);
    }
    function unlock(event) {
      if (disposed || event?.isTrusted !== true || !['pointerdown', 'click'].includes(event.type) || document.hidden) return Promise.resolve(false);
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return Promise.resolve(false);
      try {
        if (!context) context = new AudioContext();
        return Promise.resolve(context.resume()).then(() => !disposed);
      } catch (_) { return Promise.resolve(false); }
    }
    function begin(event) {
      if (!event || event.isTrusted === false || disposed || muted || document.hidden) return;
      end(true);
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      const token = ++generation;
      active = true;
      speed = 0; pressure = clamp(event.pressure || .5, 0, 1);
      try {
        if (!context) context = new AudioContext();
        // resume is invoked synchronously inside the pointer gesture, not after fetch.
        Promise.all([context.resume(), bufferFor(context)]).then(([, buffer]) => {
          if (disposed || muted || !active || token !== generation || document.hidden) return;
          source = context.createBufferSource(); gain = context.createGain(); filter = context.createBiquadFilter();
          source.buffer = buffer; source.loop = true; filter.type = 'lowpass';
          gain.gain.value = 0;
          source.connect(filter); filter.connect(gain); gain.connect(context.destination);
          source.start(); update({ speed, pressure });
        }).catch(() => { if (token === generation) end(true); });
      } catch (_) { end(true); }
    }
    function setMuted(value) {
      muted = !!value;
      try { localStorage.setItem('crystal-muted', String(muted)); } catch (_) {}
      if (muted) end(true);
    }
    const hidden = () => { if (document.hidden) end(true); };
    const pagehide = () => end(true);
    document.addEventListener('visibilitychange', hidden);
    window.addEventListener('pagehide', pagehide);
    return { begin, unlock, update, end, setMuted, get muted() { return muted; }, dispose() {
      if (disposed) return;
      disposed = true; end(true);
      document.removeEventListener('visibilitychange', hidden);
      window.removeEventListener('pagehide', pagehide);
      if (context) { try { Promise.resolve(context.close()).catch(() => {}); } catch (_) {} }
    } };
  };
})();

'use strict';

(() => {
  const app = document.getElementById('app');
  const status = document.getElementById('status');
  const tg = window.Telegram && window.Telegram.WebApp;
  const modes = { learn: ['Learn', 'Understand the essentials', '01'], formula: ['Formulas', 'Practice the mathematics', '02'], law: ['Laws', 'Connect principles and ideas', '03'] };
  let mode = 'learn';
  let session = null;
  let busy = false;
  let screenVersion = 0;
  let screen = 'home';
  let disposeAtlas = () => {}; 

  function node(tag, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined && text !== null) el.textContent = String(text);
    if (className) el.className = className;
    return el;
  }
  function announce(text) { status.textContent = text; }
  function button(text, action, className = 'button') {
    const el = node('button', text, className);
    el.type = 'button';
    el.addEventListener('click', action);
    return el;
  }
  function renderScreen(name) {
    disposeAtlas();
    disposeAtlas = () => {};
    screen = name;
    screenVersion += 1;
    app.replaceChildren();
    if (tg && tg.BackButton) {
      if (name === 'home' || name === 'error') tg.BackButton.hide();
      else tg.BackButton.show();
    }
    app.focus({ preventScroll: true });
    return screenVersion;
  }
  function heading(eyebrow, title, description) {
    const section = node('section', null, 'intro');
    section.append(node('p', eyebrow, 'eyebrow'), node('h1', title));
    if (description) section.append(node('p', description, 'muted'));
    app.append(section);
  }
  function loading() { app.append(node('p', 'Loading…', 'loading')); }
  function errorMessage(error) {
    if (error.status === 401 || error.status === 403) return 'Your Telegram authorization could not be verified. Close this Mini App and reopen it from the bot.';
    if (error.status === 409) return 'This question has changed or was already answered. Reload the current session before continuing.';
    return error.message || 'Something went wrong. Please try again.';
  }
  function showError(error, retry) {
    announce(errorMessage(error));
    const box = node('section', null, 'notice error');
    box.setAttribute('role', 'alert');
    box.append(node('p', errorMessage(error)));
    if (retry && error.status !== 401 && error.status !== 403) box.append(button('Try again', retry, 'button secondary'));
    app.append(box);
  }
  async function api(path, body) {
    if (!tg || !tg.initData) throw new Error('Open Quantum Tutor inside Telegram using the bot’s Mini App button. Telegram authorization is required; browser previews and demo accounts are not supported.');
    let response;
    try {
      response = await fetch(`/api${path}`, {
        method: body === undefined ? 'GET' : 'POST',
        headers: { Authorization: 'tma ' + tg.initData, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        cache: 'no-store'
      });
    } catch (_) { throw new Error('Unable to connect. Check your connection and try again.'); }
    if (!response.ok) {
      const error = new Error(response.status >= 500 ? 'The study service is temporarily unavailable. Please try again.' : 'The request could not be completed. Please try again.');
      error.status = response.status;
      throw error;
    }
    return response.json();
  }
  function percent(value) { return Math.max(0, Math.min(100, Number(value) || 0)); }
  function meter(value, label) {
    const el = node('progress');
    el.max = 100;
    el.value = percent(value);
    el.setAttribute('aria-label', label);
    return el;
  }
  function math(container, latex, fallback) {
    if (latex && window.katex) {
      try { window.katex.render(latex, container, { trust: false, throwOnError: true, strict: 'ignore', displayMode: false }); return; } catch (_) { /* Keep formulas readable when rendering is unavailable. */ }
    }
    container.textContent = fallback || latex || '';
  }
  function navigation() { app.append(button('← Main menu', () => { if (!busy) home(); }, 'text-button')); }

  async function home() {
    if (busy) return;
    const version = renderScreen('home');
    heading('A LITTLE PRACTICE, EVERY DAY', 'Make quantum mechanics click.', 'Explore your course, recall what matters, and see your understanding grow.');
    const grid = node('div', null, 'mode-grid');
    Object.entries(modes).forEach(([key, [title, description, index]]) => {
      const item = button('', () => topics(key), 'mode-card');
      item.append(node('span', index, 'mode-index'), node('h2', title), node('p', description), node('span', 'Explore →', 'mode-link'));
      grid.append(item);
    });
    app.append(grid);
    const dashboard = node('section', null, 'panel');
    dashboard.append(node('p', 'YOUR LEARNING', 'eyebrow'), node('h2', 'A clearer picture, with every answer.'));
    app.append(dashboard);
    try {
      const [progress, existing] = await Promise.all([api('/progress'), api('/session').catch(error => { if (error.status === 404) return null; throw error; })]);
      if (version !== screenVersion) return;
      const stats = node('div', null, 'stats');
      [['Answered', progress.answered], ['Correct', progress.correct], ['Accuracy', `${percent(progress.accuracy)}%`], ['Known cards', `${progress.known} / ${progress.total}`]].forEach(([label, value]) => {
        const stat = node('div'); stat.append(node('strong', value), node('span', label)); stats.append(stat);
      });
      dashboard.append(stats, meter(progress.total ? progress.known / progress.total * 100 : 0, 'Known cards'));
      const review = button('', () => reviewSelection(), 'review-card');
      review.append(node('span', '↻', 'review-icon'), node('span', `Review · ${progress.review_count} to revisit`), node('span', '→'));
      app.append(review);
      if (existing && !existing.complete) app.append(button('Continue your session →', () => { session = existing; showSession(); }, 'button primary wide'));
    } catch (error) { if (version === screenVersion) showError(error, home); }
  }

  function reviewSelection() {
    renderScreen('review'); navigation();
    heading('SPACED PRACTICE', 'A second look. A stronger memory.', 'Choose a mode, then review a topic or all topics. Missed questions return to the queue.');
    Object.entries(modes).forEach(([key, [title]]) => app.append(button(`Review ${title.toLowerCase()} →`, () => topics(key, true), 'button secondary wide')));
  }

  async function topics(selectedMode, review = false) {
    if (busy) return;
    mode = selectedMode;
    const version = renderScreen('topics'); navigation();
    heading(review ? 'REVIEW' : 'YOUR COURSE', modes[mode][0], review ? 'Revisit questions that need more practice.' : 'Choose a topic, or practice the whole course.');
    loading();
    try {
      const data = await api(`/topics?mode=${encodeURIComponent(mode)}`);
      if (version !== screenVersion) return;
      app.querySelector('.loading').remove();
      renderAtlas(data.topics, review);
      app.append(button(review ? `Review all topics · ${data.review_count} due` : 'Practice all topics →', () => start(null, review), 'button primary wide'));
      app.append(node('h2', 'Topic list · dates, cards & progress', 'atlas-list-heading'));
      if (!review) app.append(button(`Review this mode · ${data.review_count} due`, () => topics(selectedMode, true), 'text-button'));
      for (const [title, min, max] of [['Chapters', 1, 10], ['Experiments', 11, 20]]) {
        const group = node('section', null, 'topic-group');
        group.append(node('h2', title));
        const list = node('div', null, 'topic-list');
        data.topics.filter(topic => topic.number >= min && topic.number <= max).forEach(topic => {
          const item = button('', () => start(topic.number, review), 'topic-card');
          const content = node('div', null, 'topic-content');
          content.append(node('h3', topic.title_de || topic.title || '')); 
          const metadata = [topic.professor, topic.date, `${review ? topic.review_count : topic.card_count} cards`].filter(value => value !== null && value !== undefined && value !== '');
          content.append(node('p', metadata.join(' · '), 'topic-meta'), meter(topic.percent, `${topic.title || topic.title_de}: ${percent(topic.percent)}%`));
          item.append(node('span', String(topic.number).padStart(2, '0'), 'topic-number'), content, node('span', `${percent(topic.percent)}%`, 'topic-percent'));
          list.append(item);
        });
        if (!list.childElementCount) list.append(node('p', 'No topics available in this group.', 'muted'));
        group.append(list); app.append(group);
      }
    } catch (error) { if (version === screenVersion) { app.querySelector('.loading')?.remove(); showError(error, () => topics(selectedMode, review)); } }
  }

  function renderAtlas(topics, review) {
    const scene = node('section', null, 'atlas-scene');
    scene.setAttribute('aria-label', 'Crystal Atlas: chapters 01–10 and experiments E1–E10');
    const hint = node('p', 'CHOOSE YOUR ORBIT · ' + modes[mode][0].toUpperCase(), 'atlas-caption');
    const core = button('', () => start(null, review), 'atlas-core');
    core.setAttribute('aria-label', review ? 'Review all topics' : 'Practice all topics');
    core.append(node('span', 'Q', 'atlas-crystal'), node('span', review ? 'REVIEW ALL TOPICS' : 'ALL TOPICS', 'atlas-core-label'));
    scene.append(hint, core);
    const spheres = [];
    topics.filter(topic => topic.number >= 1 && topic.number <= 20)
      .slice().sort((a, b) => a.number - b.number).forEach(topic => {
        // Capture the API ID, never an animation index or mutable loop counter.
        const topicId = topic.number;
        const experiment = topicId > 10;
        const label = experiment ? `E${topicId - 10}` : String(topicId).padStart(2, '0');
        const sphere = button(label, () => start(topicId, review), `atlas-sphere ${experiment ? 'experiment' : 'theory'}`);
        sphere.setAttribute('aria-label', `${experiment ? 'Experiment' : 'Chapter'} ${label}: ${topic.title_de || topic.title}`);
        sphere.title = `${topic.title_de || topic.title} · ${review ? topic.review_count : topic.card_count} cards · ${percent(topic.percent)}%`;
        sphere.dataset.topicId = String(topicId);
        scene.append(sphere);
        spheres.push(sphere);
      });
    app.append(scene, node('p', 'Select a sphere or use the topic list below. Motion pauses while the atlas has keyboard focus.', 'atlas-help'));

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    let frameId = null;
    let phase = 0;
    let previous = null;
    let focused = false;
    let disposed = false;
    function place() {
      // Equal spacing on a perimeter keeps all twenty targets separate, even on mobile.
      // The compact crystal stays inside the perimeter and cannot cover a sphere.
      const width = Math.max(1, scene.clientWidth - 48);
      const height = scene.clientHeight - 96;
      const perimeter = 2 * (width + height);
      spheres.forEach((sphere, index) => {
        let distance = ((index / spheres.length + phase) % 1) * perimeter;
        let x, y;
        if (distance < width) { x = distance; y = 0; }
        else if ((distance -= width) < height) { x = width; y = distance; }
        else if ((distance -= height) < width) { x = width - distance; y = height; }
        else { distance -= width; x = 0; y = height - distance; }
        sphere.style.left = `${x + 24}px`;
        sphere.style.top = `${y + 60}px`;
      });
    }
    function stop() {
      if (frameId !== null) cancelAnimationFrame(frameId);
      frameId = null;
      previous = null;
    }
    function frame(time) {
      frameId = null;
      if (disposed || document.hidden || reduced.matches || focused) return;
      if (previous !== null) phase = (phase + Math.min(time - previous, 50) / 180000) % 1;
      previous = time;
      place();
      frameId = requestAnimationFrame(frame);
    }
    function sync() {
      stop();
      place();
      if (!disposed && !document.hidden && !reduced.matches && !focused) frameId = requestAnimationFrame(frame);
    }
    function focusIn() { focused = true; stop(); }
    function focusOut(event) { focused = scene.contains(event.relatedTarget); sync(); }
    scene.addEventListener('focusin', focusIn);
    scene.addEventListener('focusout', focusOut);
    document.addEventListener('visibilitychange', sync);
    window.addEventListener('resize', sync);
    reduced.addEventListener('change', sync);
    disposeAtlas = () => {
      disposed = true;
      stop();
      document.removeEventListener('visibilitychange', sync);
      window.removeEventListener('resize', sync);
      reduced.removeEventListener('change', sync);
      scene.removeEventListener('focusin', focusIn);
      scene.removeEventListener('focusout', focusOut);
    };
    sync();
  }

  async function start(topicId, review) {
    if (busy) return;
    busy = true;
    app.querySelectorAll('button').forEach(el => { el.disabled = true; });
    try { session = await api('/session', { mode, topic_id: topicId, review }); showSession(); }
    catch (error) { showError(error); }
    finally { busy = false; app.querySelectorAll('button').forEach(el => { el.disabled = false; }); }
  }
  async function reloadSession() {
    if (busy) return;
    busy = true;
    try { session = await api('/session'); showSession(); }
    catch (error) { if (error.status === 404) { busy = false; home(); } else showError(error); }
    finally { busy = false; }
  }
  async function endSession() {
    if (busy) return;
    busy = true;
    try { await api('/session/end', {}); session = null; busy = false; home(); }
    catch (error) { showError(error, endSession); }
    finally { busy = false; }
  }
  function showSession() {
    renderScreen('session');
    if (session.complete) { completion(); return; }
    app.append(button('← End session', endSession, 'text-button'));
    heading('ACTIVE RECALL', session.title, 'Choose an answer. Take your time.');
    const progress = node('div', null, 'session-progress');
    progress.append(node('span', `${session.completed} / ${session.total} completed`), node('span', `${percent(session.percent)}%`), meter(session.percent, 'Session progress'));
    app.append(progress);
    const question = session.question;
    if (!question) { showError(new Error('No question is available. Reload your session.'), reloadSession); return; }
    const card = node('section', null, 'question-panel');
    card.append(node('p', `QUESTION ${session.position}`, 'eyebrow'), node('h2', question.prompt, 'question-prompt'));
    const choices = node('div', null, 'choices');
    question.choices.forEach((choice, index) => {
      const answer = button('', () => submit(question.id, index, choices), 'choice');
      const content = node('span', null, 'choice-content');
      if (choice.latex) { const formula = node('span', null, 'math'); math(formula, choice.latex, choice.text); content.append(formula); }
      else if (choice.text) content.append(node('span', choice.text));
      answer.append(node('span', String.fromCharCode(65 + index), 'choice-letter'), content);
      choices.append(answer);
    });
    choices.append(button('I don’t know — practice again', () => submit(question.id, null, choices), 'button secondary unknown'));
    card.append(choices); app.append(card);
  }
  async function submit(questionId, choiceIndex, choices) {
    if (busy || !session || session.question?.id !== questionId) return;
    busy = true;
    choices.querySelectorAll('button').forEach(el => { el.disabled = true; });
    app.querySelectorAll('.text-button').forEach(el => { el.disabled = true; });
    try {
      const result = await api('/answer', { question_id: questionId, choice_index: choiceIndex });
      session = result.state;
      const feedback = result.feedback;
      const box = node('section', null, `feedback ${feedback.correct ? 'correct' : 'incorrect'}`);
      box.tabIndex = -1;
      box.append(node('h2', feedback.correct ? 'Correct. Nicely done.' : choiceIndex === null ? 'Let’s learn this one.' : 'Not quite — you’ll see this again.'));
      box.append(node('p', feedback.answer));
      if (feedback.latex) { const formula = node('div', null, 'math feedback-math'); math(formula, feedback.latex, feedback.answer); box.append(formula); }
      if (feedback.source_note) box.append(node('p', feedback.source_note, 'source-note'));
      if (!feedback.correct) box.append(node('p', 'Added back to your practice queue.', 'retry-note'));
      box.append(button(session.complete ? 'See completion →' : 'Next question →', showSession, 'button primary wide'));
      app.append(box);
      announce(feedback.correct ? 'Correct answer.' : 'Answer revealed. This question will return for practice.');
      box.focus({ preventScroll: true });
      box.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'nearest' });
    } catch (error) {
      showError(error, reloadSession);
      // An uncertain response may already have been accepted. Never resubmit a stale token.
      announce('Unable to confirm your answer. Reload the session to continue safely.');
    } finally {
      busy = false;
      app.querySelectorAll('.text-button').forEach(el => { el.disabled = false; });
    }
  }
  function completion() {
    heading('SESSION COMPLETE', 'A little more understood.', session.title);
    const panel = node('section', null, 'completion panel');
    panel.append(node('div', '✓', 'completion-icon'), node('h2', 'Practice complete'), node('p', `${session.completed} / ${session.total} completed · ${percent(session.percent)}%`, 'muted'), button('Main menu', endSession, 'button primary wide'));
    app.append(panel);
    announce('Session complete.');
  }
  function applyTheme() {
    document.documentElement.dataset.theme = tg?.colorScheme === 'dark' ? 'dark' : 'light';
    const themeColor = tg?.themeParams?.bg_color;
    if (themeColor && /^#[0-9a-f]{6}$/i.test(themeColor)) document.documentElement.style.setProperty('--telegram-bg', themeColor);
  }
  document.getElementById('brand').addEventListener('click', event => { event.preventDefault(); if (!busy && screen !== 'error') home(); });
  if (!tg?.initData) {
    renderScreen('error');
    heading('TELEGRAM MINI APP', 'Your study space lives in Telegram.', 'Open Quantum Tutor from the bot’s Mini App button to securely load your course and progress.');
    showError(new Error('Telegram authorization is missing. Close this page and launch the Mini App inside Telegram.'));
    return;
  }
  applyTheme();
  tg.ready();
  tg.expand();
  tg.onEvent('themeChanged', applyTheme);
  tg.BackButton?.onClick(() => { if (!busy) { if (screen === 'session') endSession(); else home(); } });
  home();
})();

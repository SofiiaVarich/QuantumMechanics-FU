'use strict';

(() => {
  const app = document.getElementById('app');
  const status = document.getElementById('status');
  const tg = window.Telegram && window.Telegram.WebApp;
  const modes = { learn: ['Learn', 'Understand the essentials', '01'], formula: ['Formulas', 'Practice the mathematics', '02'], law: ['Laws', 'Connect principles and ideas', '03'] };
  let mode = 'learn';
  let session = null;
  let busy = false;
  let uncertainAnswer = null;
  const REQUEST_TIMEOUT_MS = 15000;

  function lockControls() {
    busy = true;
    app.setAttribute('aria-busy', 'true');
    const controls = Array.from(app.querySelectorAll('button'), el => [el, el.disabled]);
    controls.forEach(([el]) => { el.disabled = true; });
    return () => {
      busy = false;
      app.setAttribute('aria-busy', 'false');
      controls.forEach(([el, disabled]) => { el.disabled = disabled; });
      if (uncertainAnswer) app.querySelectorAll('.choices button').forEach(el => { el.disabled = true; });
    };
  }
  let screenVersion = 0;
  let screen = 'home';
  let disposeExercise = () => {};
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
    disposeExercise();
    disposeExercise = () => {};
    document.body.classList.toggle('exercise-session', name === 'session');
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
    if (error.status === 403) return 'This is a private learning app. Your Telegram account is not on the access list. Contact the bot owner; reopening the app will not grant access.';
    if (error.code === 'auth_missing') return 'Telegram sign-in data is missing. Open Quantum Tutor from the bot’s Mini App button; browser previews are not supported.';
    if (error.code === 'auth_expired') return 'Your Telegram sign-in has expired. Close this Mini App completely and reopen it from the bot to start a fresh session.';
    if (error.status === 401) return 'Telegram sign-in data is invalid. Close this Mini App and reopen it from the bot. If it still fails, contact the bot owner.';
    if (error.status === 409) return 'This question has changed or was already answered. Reload the current session before continuing.';
    return error.message || 'Something went wrong. Please try again.';
  }
  function showError(error, retry, retryLabel = 'Try again') {
    announce(errorMessage(error));
    const box = node('section', null, 'notice error');
    box.setAttribute('role', 'alert');
    box.append(node('p', errorMessage(error)));
    if (retry && error.status !== 401 && error.status !== 403) box.append(button(retryLabel, retry, 'button secondary'));
    app.append(box);
  }
  async function api(path, body) {
    if (!tg || !tg.initData) {
      const error = new Error('Telegram sign-in data is missing.');
      error.status = 401;
      error.code = 'auth_missing';
      throw error;
    }
    const controller = new AbortController();
    let timer;
    const timeout = new Promise((_, reject) => {
      timer = setTimeout(() => {
        reject(new Error('The request timed out. Check your connection, then retry or resume your session.'));
        controller.abort();
      }, REQUEST_TIMEOUT_MS);
    });
    try {
      return await Promise.race([timeout, (async () => {
      const response = await fetch(`/api${path}`, {
        method: body === undefined ? 'GET' : 'POST',
        headers: { Authorization: 'tma ' + tg.initData, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        cache: 'no-store',
        signal: controller.signal
      });
    if (!response.ok) {
      const error = new Error(response.status >= 500 ? 'The study service is temporarily unavailable. Please try again.' : 'The request could not be completed. Please try again.');
      error.status = response.status;
      if (response.status === 401 || response.status === 403) {
        try {
          const payload = await response.json();
          if (typeof payload?.code === 'string') error.code = payload.code;
        } catch (_) { /* Keep status-based guidance for non-JSON error responses. */ }
      }
      throw error;
    }
    return await response.json();
      })()]);
    } catch (error) {
      if (error.status || controller.signal.aborted) throw error;
      throw new Error('Unable to connect or read the response. Check your connection, then retry or resume your session.');
    } finally { clearTimeout(timer); }
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
  function navigation() { app.append(button('← Atlas', () => { if (!busy) home(); }, 'text-button')); }

  function home() { return topics(mode); }

  async function dashboardScreen() {
    if (busy) return;
    const version = renderScreen('progress');
    navigation();
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
      review.append(node('span', '↻', 'review-icon'), node('span', `Review · ${progress.review_count}`), node('span', '→'));
      app.append(review);
      if (existing && !existing.complete) app.append(button('Resume', () => { session = existing; showSession(); }, 'button primary wide'));
    } catch (error) { if (version === screenVersion) showError(error, () => dashboardScreen()); }
  }

  function reviewSelection() {
    renderScreen('review'); navigation();
    heading('SPACED PRACTICE', 'A second look. A stronger memory.', 'Choose a mode, then review a topic or all topics. Missed questions return to the queue.');
    Object.entries(modes).forEach(([key, [title]]) => app.append(button(title, () => topics(key, true), 'button secondary wide')));
  }

  async function topics(selectedMode, review = false) {
    if (busy) return;
    mode = selectedMode;
    const version = renderScreen(review ? 'review' : 'home');
    if (review) navigation();
    heading('STUDY THE INVISIBLE / 2026', 'TOUCH\nQUANTUM', 'Twenty worlds of physics. Turn the crystal, drag the spheres, and choose a chapter or experiment.');
    loading();
    try {
      const data = await api(`/topics?mode=${encodeURIComponent(mode)}`);
      if (version !== screenVersion) return;
      app.querySelector('.loading').remove();
      renderAtlas(data.topics, review);
      const controls = node('nav', null, 'atlas-modes');
      controls.setAttribute('aria-label', 'Study mode');
      Object.entries(modes).forEach(([key, [title]]) => {
        const control = button(title, () => topics(key, review), 'button secondary');
        control.setAttribute('aria-pressed', String(key === mode));
        controls.append(control);
      });
      controls.append(button('Progress', dashboardScreen, 'text-button'));
      app.append(controls);
      app.append(node('h2', 'Topic list · dates, cards & progress', 'atlas-list-heading'));
      if (!review) app.append(button(`Review · ${data.review_count}`, () => topics(selectedMode, true), 'text-button'));
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
    const core = button('', () => {}, 'atlas-core');
    core.setAttribute('aria-label', 'Interactive crystal: press to deform, drag to turn');
    const canvas = node('canvas');
    core.append(node('span', 'Q', 'atlas-crystal'), canvas);
    const cta = node('div', null, 'atlas-cta');
    cta.append(node('span', 'TOUCH & PRESS THE CRYSTAL'), button(review ? 'REVIEW ALL' : 'STUDY ALL', () => start(null, review), 'atlas-start'));
    scene.append(hint, core, cta);
    scene.dataset.filter = 'all';
    const filters = node('div', null, 'atlas-filters');
    filters.setAttribute('role', 'group');
    filters.setAttribute('aria-label', 'Filter atlas topics');
    const spheres = [];
    const filterButtons = [];
    for (const [value, label] of [['all', 'ALL 20'], ['theory', '01—10 THEORY'], ['experiment', 'E1—E10 LAB']]) {
      const control = button(label, () => {
        scene.dataset.filter = value;
        filterButtons.forEach(item => item.setAttribute('aria-pressed', String(item === control)));
        spheres.forEach(sphere => { sphere.hidden = value !== 'all' && sphere.dataset.category !== value; });
      }, 'button secondary');
      control.setAttribute('aria-pressed', String(value === 'all'));
      filterButtons.push(control);
      filters.append(control);
    }
    topics.filter(topic => topic.number >= 1 && topic.number <= 20)
      .slice().sort((a, b) => a.number - b.number).forEach(topic => {
        // Capture the API ID, never an animation index or mutable loop counter.
        const topicId = topic.number;
        const experiment = topicId > 10;
        const label = experiment ? `E${topicId - 10}` : String(topicId).padStart(2, '0');
        let moved = false;
        const sphere = button(label, () => { if (!moved) start(topicId, review); }, `atlas-sphere ${experiment ? 'experiment' : 'theory'}`);
        const mini = node('canvas'); mini.width = mini.height = 92;
        sphere.textContent = '';
        sphere.append(mini, node('span', label, 'atlas-chip'));
        sphere.setAttribute('aria-label', `${experiment ? 'Experiment' : 'Chapter'} ${label}: ${topic.title_de || topic.title}`);
        sphere.title = `${topic.title_de || topic.title} · ${review ? topic.review_count : topic.card_count} cards · ${percent(topic.percent)}%`;
        sphere.dataset.topicId = String(topicId);
        sphere.dataset.category = experiment ? 'experiment' : 'theory';
        scene.append(sphere);
        spheres.push(sphere);
        let origin = null;
        sphere.addEventListener('pointerdown', event => { moved = false; origin = [event.clientX, event.clientY]; sphere.setPointerCapture(event.pointerId); });
        sphere.addEventListener('pointermove', event => {
          if (!origin) return;
          const dx = event.clientX - origin[0], dy = event.clientY - origin[1];
          if (Math.hypot(dx, dy) > 5) moved = true;
          sphere.style.translate = `${dx}px ${dy}px`;
        });
        sphere.addEventListener('pointerup', () => { origin = null; });
        sphere.addEventListener('pointercancel', () => { origin = null; moved = true; });
        sphere.addEventListener('keydown', () => { moved = false; });
      });
    const foot = node('div', null, 'atlas-foot');
        for (const [title, detail] of [['CHOOSE YOUR ORBIT', 'Tap a sphere to open its exercises.'], ['DRAG / TAP', 'Interactive study map']]) {
          const column = node('span');
          column.append(node('b', title), node('br'), node('span', detail));
          foot.append(column);
        }
        app.append(scene, filters, foot, node('p', 'Select a sphere or use the topic list below. Motion pauses while the atlas has keyboard focus.', 'sr-only'));
        for (let k = 0; k < 14; k++) {
          const dust = node('i', null, 'atlas-dust');
          dust.setAttribute('aria-hidden', 'true');
          const size = 2 + (k * 7 % 5);
          dust.style.cssText = `width:${size}px;height:${size}px;left:${(k * 37 + 11) % 100}%;top:${5 + (k * 23 % 90)}%;animation-delay:-${k % 9}s;opacity:${.4 + (k % 5) * .1}`;
          scene.append(dust);
        }

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    const crystal = window.createAtlasCrystal?.(core, canvas, reduced, () => scene.dataset.filter);
    const minis = window.createAtlasMiniCrystals?.(spheres);
    let frameId = null;
    let phase = 0;
    let previous = null;
    let focused = false;
    let disposed = false;
    function place() {
      const width = scene.clientWidth, height = scene.clientHeight;
      spheres.forEach(sphere => {
        const id = Number(sphere.dataset.topicId), experiment = id > 10;
        const angle = ((id - 1) % 10) * Math.PI / 5 + (experiment ? .4 : 0) + phase * Math.PI * 2 * (experiment ? -1 : 1);
        const x = width * (experiment ? .44 : .32) * Math.cos(angle);
        const y = height * (experiment ? .36 : .22) * Math.sin(angle);
        const tilt = experiment ? -.55 : .57;
        sphere.style.left = `${width / 2 + x * Math.cos(tilt) - y * Math.sin(tilt)}px`;
        sphere.style.top = `${height / 2 + x * Math.sin(tilt) + y * Math.cos(tilt)}px`;
        sphere.style.zIndex = Math.sin(angle) > 0 ? 6 : 2;
                sphere.style.scale = String(.85 + .15 * (1 + Math.sin(angle)) / 2);
      });
    }

    function stop() {
      if (frameId !== null) cancelAnimationFrame(frameId);
      frameId = null;
      previous = null;
      crystal?.stop();
    }
    function frame(time) {
      frameId = null;
      if (disposed || document.hidden || reduced.matches || focused) return;
      if (previous !== null) phase = (phase + Math.min(time - previous, 50) / 180000) % 1;
      previous = time;
      place();
      crystal?.draw();
      minis?.draw(time);
      frameId = requestAnimationFrame(frame);
    }
    function sync() {
      stop();
      place();
      if (!document.hidden) { crystal?.draw(); minis?.draw(reduced.matches ? 0 : performance.now()); }
      if (!disposed && !document.hidden && !reduced.matches && !focused) frameId = requestAnimationFrame(frame);
    }
    function focusIn(event) { focused = !event?.target?.matches || event.target.matches(':focus-visible'); if (focused) stop(); }
    function focusOut(event) { focused = scene.contains(event.relatedTarget); sync(); }
    scene.addEventListener('focusin', focusIn);
    scene.addEventListener('focusout', focusOut);
    document.addEventListener('visibilitychange', sync);
    window.addEventListener('resize', sync);
    reduced.addEventListener('change', sync);
    disposeAtlas = () => {
      disposed = true;
      stop();
      crystal?.dispose();
      minis?.dispose();
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
    const version = screenVersion;
    const unlock = lockControls();
    const atlas = app.querySelector('.atlas-scene');
    app.setAttribute('aria-busy', 'true');
    atlas?.setAttribute('aria-busy', 'true');
    app.querySelectorAll('button').forEach(el => { el.disabled = true; });
    try {
      const state = await api('/session', { mode, topic_id: topicId, review });
      if (version !== screenVersion) return;
      session = state; uncertainAnswer = null; showSession();
    }
    catch (error) { if (version === screenVersion) showError(error, reloadSession, 'Resume session'); }
    finally {
      atlas?.setAttribute('aria-busy', 'false');
      unlock();
    }
  }
  async function reloadSession() {
    if (busy) return;
    const version = screenVersion;
    const unlock = lockControls();
    try {
      const state = await api('/session');
      if (version !== screenVersion) return;
      session = state; uncertainAnswer = null; showSession();
    }
    catch (error) {
      if (version !== screenVersion) return;
      if (error.status === 404) { session = null; uncertainAnswer = null; busy = false; home(); }
      else showError(error, reloadSession, 'Resume session');
    }
    finally { unlock(); }
  }
  async function endSession() {
    if (busy) return;
    const version = screenVersion;
    const unlock = lockControls();
    try {
      await api('/session/end', {});
      if (version !== screenVersion) return;
      session = null; uncertainAnswer = null; busy = false; home();
    }
    catch (error) { if (version === screenVersion) showError(error, reloadSession, 'Resume session'); }
    finally { unlock(); }
  }
  function showSession() {
    renderScreen('session');
    if (session.complete) { completion(); return; }
    const toolbar = node('div', null, 'exercise-toolbar');
    toolbar.append(button('End session', endSession, 'text-button'));
    const title = button(session.title, () => {
      const dialog = document.getElementById('session-title-dialog');
      dialog.querySelector('h2').textContent = session.title;
      dialog.showModal();
    }, 'session-title');
    title.setAttribute('aria-label', `Full session title: ${session.title}`);
    title.setAttribute('aria-haspopup', 'dialog');
    toolbar.append(title); app.append(toolbar);
    const progress = node('div', null, 'session-progress');
    progress.append(node('span', `${session.completed} / ${session.total} completed`), node('span', `${percent(session.percent)}%`), meter(session.percent, 'Session progress'));
    app.append(progress);
    const question = session.question;
    if (!question) { showError(new Error('No question is available. Reload your session.'), reloadSession); return; }
    const card = node('section', null, 'question-panel');
    const prompt = node('div', null, 'exercise-question');
    prompt.id = 'exercise-question';
    prompt.append(node('p', `QUESTION ${session.position}`, 'eyebrow'), node('h2', question.prompt, 'question-prompt'));
    prompt.tabIndex = 0;
    prompt.setAttribute('aria-label', 'Question, scroll for full content');
    card.append(prompt);
    const choices = node('div', null, 'choices');
    question.choices.forEach((choice, index) => {
      const answer = button('', () => submit(question.id, index, choices), 'choice');
      answer.setAttribute('aria-label', `${String.fromCharCode(65 + index)}: ${choice.text}`);
      answer.addEventListener('keydown', event => {
        const formula = answer.querySelector('.math');
        if (formula && formula.scrollWidth > formula.clientWidth && ['ArrowLeft', 'ArrowRight'].includes(event.key)) {
          event.preventDefault();
          formula.scrollLeft += event.key === 'ArrowRight' ? 80 : -80;
        }
      });
      const content = node('span', null, 'choice-content');
      if (choice.latex) { const formula = node('span', null, 'math'); math(formula, choice.latex, choice.text); content.append(formula); }
      else if (choice.text) content.append(node('span', choice.text));
      answer.append(node('span', String.fromCharCode(65 + index), 'choice-letter'), content);
      choices.append(answer);
    });
    choices.append(button('Don’t know', () => submit(question.id, null, choices), 'button secondary unknown'));
    if (uncertainAnswer) {
      choices.querySelectorAll('button').forEach(el => { el.disabled = true; });
      showError(new Error('Your previous answer is unconfirmed. Resume the session before answering again.'), reloadSession, 'Resume session');
    }
    choices.id = 'exercise-answers';
    const switcher = node('div', null, 'exercise-switcher');
    switcher.hidden = true;
    const explanation = node('p', 'Full content cannot fit together at a readable size. Switch views; scroll within each view or formula to read everything.', 'focus-explanation');
    let view = 'question';
    const select = next => { view = next; applyView(); };
    const questionView = button('Question', () => select('question'), 'button secondary');
    const answerView = button('Answers', () => select('answers'), 'button secondary');
    questionView.setAttribute('aria-controls', prompt.id);
    answerView.setAttribute('aria-controls', choices.id);
    switcher.append(explanation, questionView, answerView);
    card.append(switcher, choices); app.append(card);
    function applyView() {
      const focused = card.dataset.layout === 'focus';
      prompt.hidden = focused && view !== 'question';
      choices.hidden = focused && view !== 'answers';
      questionView.setAttribute('aria-pressed', String(view === 'question'));
      answerView.setAttribute('aria-pressed', String(view === 'answers'));
    }
    let frame = 0;
    let disposed = false;
    function measure() {
      frame = 0;
      if (disposed || app.querySelector('.feedback')) return;
      // Measure intrinsic content, not the constrained/hidden fallback views.
      card.dataset.layout = 'measure';
      prompt.hidden = false; choices.hidden = false; switcher.hidden = true;
      const available = card.clientHeight - 20;
      const needed = prompt.scrollHeight + choices.scrollHeight + 8;
      const focused = needed > available;
      card.dataset.layout = focused ? 'focus' : 'together';
      switcher.hidden = !focused;
      applyView();
    }
    const schedule = () => { if (!disposed && !frame) frame = requestAnimationFrame(measure); };
    const observer = new ResizeObserver(schedule);
    observer.observe(app);
    observer.observe(prompt);
    observer.observe(choices);
    window.addEventListener('resize', schedule);
    window.visualViewport?.addEventListener('resize', schedule);
    tg?.onEvent?.('viewportChanged', schedule);
    tg?.onEvent?.('safeAreaChanged', schedule);
    tg?.onEvent?.('contentSafeAreaChanged', schedule);
    document.fonts?.addEventListener('loadingdone', schedule);
    document.fonts?.ready.then(schedule);
    schedule(); // KaTeX rendering above is synchronous; font metrics may settle later.
    disposeExercise = () => {
      disposed = true; cancelAnimationFrame(frame); observer.disconnect();
      window.removeEventListener('resize', schedule);
      window.visualViewport?.removeEventListener('resize', schedule);
      tg?.offEvent?.('viewportChanged', schedule);
      tg?.offEvent?.('safeAreaChanged', schedule);
      tg?.offEvent?.('contentSafeAreaChanged', schedule);
      document.fonts?.removeEventListener('loadingdone', schedule);
    };
  }
  async function submit(questionId, choiceIndex, choices) {
    if (busy || uncertainAnswer || !session || session.question?.id !== questionId) return;
    const version = screenVersion;
    const unlock = lockControls();
    uncertainAnswer = questionId;
    try {
      const result = await api('/answer', { question_id: questionId, choice_index: choiceIndex });
      if (version !== screenVersion) return;
      uncertainAnswer = null;
      session = result.state;
      const feedback = result.feedback;
      const box = node('section', null, `feedback ${feedback.correct ? 'correct' : 'incorrect'}`);
      box.tabIndex = -1;
      box.append(node('h2', feedback.correct ? 'Correct. Nicely done.' : choiceIndex === null ? 'Let’s learn this one.' : 'Not quite — you’ll see this again.'));
      box.append(node('p', feedback.answer));
      if (feedback.latex) { const formula = node('div', null, 'math feedback-math'); math(formula, feedback.latex, feedback.answer); box.append(formula); }
      if (feedback.source_note) box.append(node('p', feedback.source_note, 'source-note'));
      if (!feedback.correct) box.append(node('p', 'Added back to your practice queue.', 'retry-note'));
      box.append(button(session.complete ? 'Finish' : 'Next', showSession, 'button primary wide'));
      disposeExercise();
      disposeExercise = () => {};
      app.querySelector('.question-panel')?.remove();
      const next = box.lastElementChild;
      const detail = node('div', null, 'feedback-detail');
      detail.tabIndex = 0;
      detail.setAttribute('aria-label', 'Answer explanation, scroll for full content');
      while (box.firstChild && box.firstChild !== next) detail.append(box.firstChild);
      box.prepend(detail);
      app.append(box);
      announce(feedback.correct ? 'Correct answer.' : 'Answer revealed. This question will return for practice.');
      box.focus({ preventScroll: true });
      box.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'nearest' });
    } catch (error) {
      if (version !== screenVersion) return;
      showError(error, reloadSession, 'Resume session');
      // An uncertain response may already have been accepted. Never resubmit a stale token.
      announce('Unable to confirm your answer. Reload the session to continue safely.');
    } finally {
      unlock();
    }
  }
  function completion() {
    heading('SESSION COMPLETE', 'A little more understood.', session.title);
    const panel = node('section', null, 'completion panel');
    panel.append(node('div', '✓', 'completion-icon'), node('h2', 'Practice complete'), node('p', `${session.completed} / ${session.total} completed · ${percent(session.percent)}%`, 'muted'), button('Menu', endSession, 'button primary wide'));
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

/**
 * app.js — Main application entry point.
 */

import { Storage }                                        from './storage.js';
import { loadFrequencyData, loadThematicData, shouldExclude } from './loader.js';
import { Scheduler }                                      from './scheduler.js';

// ─────────────────────────────────────────────────────────────────
//  Level / progression
// ─────────────────────────────────────────────────────────────────

const LEVELS = [
  { min:    0, name: 'Débutant absolu',  stars: '⭐'        },
  { min:  100, name: 'Voyageur',         stars: '⭐⭐'       },
  { min:  200, name: 'Aventurier',       stars: '⭐⭐⭐'      },
  { min:  300, name: 'Explorateur',      stars: '🌟'        },
  { min:  400, name: 'Communicant',      stars: '🌟🌟'       },
  { min:  500, name: 'Habitant',         stars: '💫'        },
  { min:  600, name: 'Citoyen',          stars: '💫💫'       },
  { min:  700, name: 'Passionné',        stars: '✨'        },
  { min:  800, name: 'Connaisseur',      stars: '✨✨'       },
  { min:  900, name: 'Expert',           stars: '🔥'        },
  { min: 1000, name: 'Maître',           stars: '🏆'        },
  { min: 2000, name: 'Grand Maître',     stars: '🏆🏆'      },
  { min: 3000, name: 'Virtuose',         stars: '🏆🏆🏆'     },
];

const PROVERBS = [
  'Vouloir, c\'est pouvoir.',
  'Petit à petit, l\'oiseau fait son nid.',
  'L\'union fait la force.',
  'À cœur vaillant, rien d\'impossible.',
  'Qui cherche, trouve.',
  'La pratique rend parfait.',
  'Chaque jour suffit sa peine.',
  'L\'appétit vient en mangeant.',
  'Mieux vaut tard que jamais.',
  'Après la pluie, le beau temps.',
];

function getLevel(learned) {
  let lv = LEVELS[0];
  for (const l of LEVELS) { if (learned >= l.min) lv = l; }
  return lv;
}

// Build date
const BUILD = new Date().toISOString().slice(0, 10);

// ─────────────────────────────────────────────────────────────────
//  State
// ─────────────────────────────────────────────────────────────────

const state = {
  words: [], themes: {},
  wordStates: {}, session: null, settings: {},
  showTranslation: false, showIPA: false,
  currentScreen: 'main',
};
let scheduler = null;

// ─────────────────────────────────────────────────────────────────
//  Utilities
// ─────────────────────────────────────────────────────────────────

function esc(s) {
  return String(s || '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

let _tt = null;
function toast(msg, ms = 2500) {
  document.querySelector('.toast')?.remove();
  clearTimeout(_tt);
  const el = document.createElement('div');
  el.className = 'toast'; el.textContent = msg;
  document.body.appendChild(el);
  _tt = setTimeout(() => el.remove(), ms);
}

function $(id) { return document.getElementById(id); }

// ─────────────────────────────────────────────────────────────────
//  Bootstrap
// ─────────────────────────────────────────────────────────────────

function setLoadMsg(msg) {
  const el = document.querySelector('.load-text');
  if (el) el.textContent = msg;
}

async function init() {
  try {
    setLoadMsg('Loading frequency list…');
    const words = await loadFrequencyData();

    setLoadMsg('Loading themes…');
    const themes = await loadThematicData();

    setLoadMsg('Building session…');
    state.words   = words;
    state.themes  = themes;
    state.settings = Storage.getSettings();
    state.wordStates = Storage.getWordStates();
    applyExclusions();
    scheduler = new Scheduler(words);
    buildOrRestoreSession();

    setLoadMsg('Setting up UI…');
    setupEventListeners();
    // Restore theme banner if last session was a theme session
    if (state.session?.themeKey) {
      const th = state.themes[state.session.themeKey];
      $('theme-banner-title').textContent = `${themeIcon(state.session.themeKey)} ${th?.title || state.session.themeKey}`;
      $('theme-banner').classList.remove('hidden');
    }
    renderCard();
    updateStatus();

    $('loading-overlay').classList.add('hidden');
    showScreen('main');

  } catch (err) {
    const msg = err?.message || String(err) || 'unknown error';
    const stack = err?.stack || '';
    document.querySelector('.load-text').textContent = '❌ ' + msg;
    const div = document.createElement('div');
    div.style.cssText = 'font-size:12px;color:#5a3010;max-width:320px;text-align:left;padding:10px;background:#fff;border-radius:8px;margin-top:8px;white-space:pre-wrap;overflow:auto;max-height:300px';
    div.textContent = stack || msg;
    $('loading-overlay').appendChild(div);
    console.error('[init error]', err);
    // legacy innerHTML fallback
    try { $('loading-overlay').querySelector('.spin')?.remove(); } catch(_) {}
    return;
    // original fallback (unreachable but kept as template):
    $('loading-overlay').innerHTML = `
      <div style="padding:32px;text-align:center;color:#5a3010;max-width:300px">
        <div style="font-size:40px;margin-bottom:12px">⚠️</div>
        <h2 style="margin-bottom:8px">Data load failed</h2>
        <p style="font-size:13px">${esc(err.message)}</p>
        <p style="font-size:12px;margin-top:10px;opacity:.75">
          Run: <code>node scripts/prepare.js</code><br>then refresh.
        </p>
      </div>`;
  }
}

function applyExclusions() {
  let changed = false;
  for (const w of state.words) {
    if (!state.wordStates[w.id]) {
      const r = shouldExclude(w);
      if (r) { state.wordStates[w.id] = { status:'excluded', excluded:true, exclusionReason:r }; changed = true; }
    }
  }
  if (changed) Storage.setWordStates(state.wordStates);
}

function buildOrRestoreSession() {
  const today = new Date().toISOString().slice(0,10);
  const saved = Storage.getSession();
  if (saved && saved.date === today && saved.queue?.length > 0) {
    state.session = saved;
  } else {
    rebuildSession();
  }
}

function rebuildSession() {
  const queue = scheduler.buildDailyQueue(state.settings.wordsPerDay, state.wordStates);
  state.session = { date: new Date().toISOString().slice(0,10), queue, currentIndex: 0 };
  Storage.setSession(state.session);
}

function saveSession() { Storage.setSession(state.session); }

// ─────────────────────────────────────────────────────────────────
//  Screen management
// ─────────────────────────────────────────────────────────────────

// ── Theme emoji map ──────────────────────────────────────────────
const THEME_ICONS = {
  animals:'🐾', body:'🫀', food:'🍽️', family:'👨‍👩‍👧', house:'🏠',
  clothes:'👗', city:'🏙️', nature:'🌿', weather:'🌦️', travel:'✈️',
  work:'💼', school:'📚', health:'💊', sports:'⚽', music:'🎵',
  art:'🎨', technology:'💻', politics:'🏛️', economy:'💰', religion:'⛪',
  emotions:'😊', time:'🕐', colors:'🎨', numbers:'🔢', transport:'🚗',
  communication:'📱', science:'🔬',
};
const themeIcon = k => THEME_ICONS[k] || '📖';

function showScreen(name) {
  ['main','stats','search','help','themes'].forEach(s => {
    $(`screen-${s}`)?.classList.toggle('hidden', s !== name);
  });
  state.currentScreen = name;
  if (name === 'stats')  renderStats();
  if (name === 'help')   renderHelp();
  if (name === 'themes') renderThemes();
  if (name === 'search') {
    $('search-results').innerHTML = '<div class="sr-item" style="text-align:center;color:#888">Type a word to search</div>';
    setTimeout(() => $('search-input')?.focus(), 80);
  }
}

// ─────────────────────────────────────────────────────────────────
//  Themes screen
// ─────────────────────────────────────────────────────────────────

function renderThemes() {
  const cont = $('themes-content');
  const themes = state.themes;

  cont.innerHTML = Object.entries(themes).map(([key, theme]) => {
    const words = theme.words || [];
    const preview = words.slice(0, 4).map(w => w.word).join(', ');
    return `
      <div class="theme-card" data-theme="${esc(key)}">
        <div class="theme-icon">${themeIcon(key)}</div>
        <div class="theme-info">
          <div class="theme-title">${esc(theme.title || key)}</div>
          <div class="theme-meta">${words.length} words</div>
          <div class="theme-words-preview">${esc(preview)}…</div>
        </div>
        <div class="theme-arrow">›</div>
      </div>`;
  }).join('');

  cont.querySelectorAll('.theme-card').forEach(card => {
    card.addEventListener('click', () => startThemeSession(card.dataset.theme));
  });
}

function startThemeSession(themeKey) {
  const theme = state.themes[themeKey];
  if (!theme) return;

  const themeWords = theme.words || [];

  // Match thematic words to frequency dict by rank_reference or word name
  const byRank = new Map(state.words.map(w => [w.rank, w]));
  const byName = new Map(state.words.map(w => [w.word.toLowerCase(), w]));

  const queue = [];
  for (const tw of themeWords) {
    let fw = tw.rank_reference ? byRank.get(tw.rank_reference) : null;
    if (!fw) fw = byName.get(tw.word.toLowerCase());
    if (fw) {
      const ws = state.wordStates[fw.id];
      const mode = (ws?.status === 'learning' || ws?.status === 'known') ? 'review' : 'new';
      queue.push({ id: fw.id, mode });
    }
  }

  if (!queue.length) { toast('No words found for this theme'); return; }

  // Override current session with theme session
  state.session = {
    date: new Date().toISOString().slice(0, 10),
    queue,
    currentIndex: 0,
    themeKey,
    themeTitle: theme.title || themeKey,
  };
  Storage.setSession(state.session);

  // Show theme banner
  $('theme-banner-title').textContent = `${themeIcon(themeKey)} ${theme.title || themeKey}`;
  $('theme-banner').classList.remove('hidden');

  showScreen('main');
  renderCard();
  toast(`${theme.title}: ${queue.length} words`);
}

// ─────────────────────────────────────────────────────────────────
//  Card rendering
// ─────────────────────────────────────────────────────────────────

function renderCard() {
  const q   = state.session?.queue ?? [];
  const idx = state.session?.currentIndex ?? 0;

  if (!q.length) {
    $('word-card').classList.add('hidden');
    $('empty-state').classList.remove('hidden');
    $('nav-counter').textContent = '0 / 0';
    $('btn-prev').disabled = $('btn-nav-next').disabled = true;
    setActionDisabled(true);
    return;
  }

  $('word-card').classList.remove('hidden');
  $('empty-state').classList.add('hidden');
  setActionDisabled(false);

  const item = q[idx];
  if (!item) return;
  const word = scheduler.getWord(item.id);
  if (!word) return;

  // Reset toggles
  state.showTranslation = false;
  state.showIPA = false;

  // Rank + mode badge
  $('rank-label').textContent = `#${word.rank}`;
  const mb = $('mode-badge');
  mb.textContent = item.mode === 'review' ? 'REVIEW' : 'NEW';
  mb.className   = item.mode === 'review' ? 'badge-review' : 'badge-new';

  // Word
  $('word-display').textContent = word.word;

  // IPA
  const ipaEl = $('ipa-display');
  ipaEl.textContent = word.ipa || '';
  ipaEl.classList.toggle('hidden', !word.ipa);

  // Translation block — hidden
  $('translation-ru').textContent = word.translation_ru || '';
  $('translation-en').textContent = word.translation_en || '';
  $('translation-block').classList.add('hidden');
  const ra = $('btn-show-translation').querySelector('.reveal-arrow');
  if (ra) { ra.classList.remove('open'); }
  $('btn-show-translation').innerHTML =
    '<span class="reveal-arrow">&#9658;</span> Show translation';

  // Example — French italic + Russian in distinct color/style
  const exEl = $('example-display');
  if (word.example_fr) {
    exEl.innerHTML =
      `<span>${esc(word.example_fr)}</span>` +
      (word.example_en ? `<span class="ex-en">${esc(word.example_en)}</span>` : '') +
      (word.example_ru ? `<span class="ex-ru">${esc(word.example_ru)}</span>` : '');
    exEl.style.display = '';
  } else {
    exEl.innerHTML = '';
    exEl.style.display = 'none';
  }

  // Task line visibility
  $('task-line').style.display = word.example_fr ? '' : 'none';

  // Next button subtitle — interval
  $('next-sub').textContent = `≈${scheduler.nextIntervalLabel(item.id, state.wordStates)}`;

  // Remove button label
  const ws = state.wordStates[item.id];
  const btnRm = $('btn-remove');
  const rmMain = btnRm.querySelector('.act-main');
  const rmSub  = btnRm.querySelector('.act-sub');
  if (ws?.status === 'removed') {
    rmMain.textContent = 'Restore'; rmSub.textContent = 'add back';
    btnRm.style.background = '#d6f0d6'; btnRm.style.color = '#1a5c1a';
  } else {
    rmMain.textContent = 'Remove'; rmSub.textContent = 'no repeats';
    btnRm.style.background = ''; btnRm.style.color = '';
  }

  // Navigation
  $('nav-counter').textContent = `${idx + 1} / ${q.length}`;
  $('btn-prev').disabled     = (idx === 0);
  $('btn-nav-next').disabled = (idx >= q.length - 1);

  // Update Next Batch subtitle with due count info
  const stats = scheduler.getStats(state.wordStates);
  const batchSub = $('btn-next-batch-card')?.querySelector('.act-sub');
  if (batchSub) {
    batchSub.textContent = stats.dueCount > 0 ? `${stats.dueCount} due` : 'load next words';
  }
}

function setActionDisabled(v) {
  ['btn-remove','btn-next-batch-card','btn-next'].forEach(id => {
    const el = $(id); if (el) el.disabled = v;
  });
}

function updateStatus() {
  if (!scheduler) return;
  const s = scheduler.getStats(state.wordStates);
  $('status-line').textContent =
    `Ready (build ${BUILD}). ${s.learned} learned · ${s.dueCount} due. Tap Stats for summary.`;
}

// ─────────────────────────────────────────────────────────────────
//  Actions
// ─────────────────────────────────────────────────────────────────

function actionNext() {
  const item = currentItem(); if (!item) return;
  state.wordStates[item.id] = scheduler.markNext(item.id, state.wordStates);
  const q = state.session.queue;
  if (state.session.currentIndex < q.length - 1) {
    state.session.currentIndex++;
  } else {
    toast('Session complete! 🎉', 3000);
    saveSession(); updateStatus(); return;
  }
  saveSession(); updateStatus(); renderCard();
}

function actionReview() {
  // Collect all words currently due for review
  const dueQueue = [];
  for (const word of state.words) {
    const s = state.wordStates[word.id];
    if (!s || s.status === 'excluded' || s.status === 'removed' || s.status === 'new') continue;
    if ((s.status === 'learning' || s.status === 'known') && scheduler.isDue(s)) {
      dueQueue.push({ id: word.id, mode: 'review' });
    }
  }

  if (!dueQueue.length) {
    toast('No words due for review right now 👌');
    return;
  }

  const queue = dueQueue.slice(0, state.settings.wordsPerDay);
  state.session = {
    date: new Date().toISOString().slice(0, 10),
    queue,
    currentIndex: 0,
  };
  Storage.setSession(state.session);

  // Clear any theme banner
  $('theme-banner').classList.add('hidden');

  renderCard();
  toast(`Review queue: ${queue.length} word${queue.length > 1 ? 's' : ''} due`);
}

function actionRemoveToggle() {
  const item = currentItem(); if (!item) return;
  const ws = state.wordStates[item.id];
  if (ws?.status === 'removed') {
    state.wordStates[item.id] = scheduler.markRestored(item.id);
    toast('Word restored to queue');
  } else {
    state.wordStates[item.id] = scheduler.markRemoved(item.id);
    toast('Removed from learning queue');
    if (state.session.currentIndex < state.session.queue.length - 1) {
      state.session.currentIndex++;
      saveSession();
    }
  }
  updateStatus(); renderCard();
}

function actionToday() {
  rebuildSession(); renderCard(); updateStatus();
  toast(`Today: ${state.session.queue.length} words`);
}

function actionNextBatch() {
  rebuildSession(); renderCard();
  toast('Next batch loaded');
}

function navigate(dir) {
  const q = state.session?.queue ?? [];
  const n = (state.session.currentIndex ?? 0) + dir;
  if (n < 0 || n >= q.length) return;
  state.session.currentIndex = n;
  saveSession(); renderCard();
}

function currentItem() {
  const q   = state.session?.queue ?? [];
  const idx = state.session?.currentIndex ?? 0;
  return q[idx] ?? null;
}

// ─────────────────────────────────────────────────────────────────
//  Swipe
// ─────────────────────────────────────────────────────────────────

function setupSwipe(el) {
  let x0 = 0, y0 = 0, on = false;
  el.addEventListener('touchstart', e => { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; on = true; }, { passive: true });
  el.addEventListener('touchmove', e => {
    if (!on) return;
    const dx = e.touches[0].clientX - x0, dy = e.touches[0].clientY - y0;
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 10) e.preventDefault();
  }, { passive: false });
  el.addEventListener('touchend', e => {
    if (!on) return; on = false;
    const dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0;
    if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.5) navigate(dx < 0 ? 1 : -1);
  });
}

// ─────────────────────────────────────────────────────────────────
//  Search
// ─────────────────────────────────────────────────────────────────

function doSearch(q) {
  q = (q || '').toLowerCase().trim();
  const cont = $('search-results');
  if (!q) { cont.innerHTML = '<div class="sr-item" style="text-align:center;color:#888">Type a word to search</div>'; return; }

  const hits = state.words.filter(w =>
    w.word?.toLowerCase().includes(q) || w.lemma?.toLowerCase().includes(q) ||
    w.translation_en?.toLowerCase().includes(q) || w.translation_ru?.toLowerCase().includes(q)
  ).slice(0, 60);

  if (!hits.length) { cont.innerHTML = '<div class="sr-item" style="text-align:center;color:#888">No results found</div>'; return; }

  cont.innerHTML = hits.map(w => {
    const ws = state.wordStates[w.id];
    let pill = '';
    if      (ws?.status === 'removed')  pill = '<span class="spill sp-removed">Removed</span>';
    else if (ws?.status === 'known')    pill = '<span class="spill sp-known">Known</span>';
    else if (ws?.status === 'learning') pill = '<span class="spill sp-learning">Learning</span>';
    else if (ws?.status === 'excluded') pill = '<span class="spill sp-filtered">Filtered</span>';
    return `
      <div class="sr-item">
        <div class="sr-word">${esc(w.word)}<span class="spill sp-pos">${esc(w.pos)}</span>${pill}</div>
        ${w.translation_ru ? `<div class="sr-ru">${esc(w.translation_ru)}</div>` : ''}
        ${w.translation_en ? `<div class="sr-en">${esc(w.translation_en)}</div>` : ''}
        <div class="sr-meta">Rank #${w.rank}${w.ipa ? ' · ' + esc(w.ipa) : ''}</div>
        ${w.example_fr ? `<div class="sr-ex">${esc(w.example_fr)}</div>` : ''}
      </div>`;
  }).join('');
}

// ─────────────────────────────────────────────────────────────────
//  Stats
// ─────────────────────────────────────────────────────────────────

function renderStats() {
  const s  = scheduler.getStats(state.wordStates);
  const lv = getLevel(s.learned);
  const nx = LEVELS.find(l => l.min > s.learned);
  const pv = s.learned >= 10 ? PROVERBS[Math.floor(s.learned / 100) % PROVERBS.length] : null;

  $('stats-content').innerHTML = `
    <div class="level-card">
      <div class="level-stars">${lv.stars}</div>
      <div class="level-name">${esc(lv.name)}</div>
      ${nx ? `<div class="level-next">${nx.min - s.learned} words until "${esc(nx.name)}"</div>`
           : `<div class="level-next" style="color:#1a5010">Maximum level! 🏆</div>`}
    </div>

    <div class="sc">
      <div class="sc-title">Progress</div>
      <div class="bar-wrap"><div class="bar-fill" style="width:${s.pct}%"></div></div>
      <div class="bar-pct">${s.pct}%</div>
      <div class="bar-sub">${s.learned} known out of ${s.active} active words</div>
    </div>

    <div class="sc">
      <div class="sc-title">Breakdown</div>
      <div class="sc-row"><span class="sc-label">Total words</span><span class="sc-val">${s.total}</span></div>
      <div class="sc-row"><span class="sc-label">Known</span><span class="sc-val" style="color:#1a6640">${s.knownCount}</span></div>
      <div class="sc-row"><span class="sc-label">In progress</span><span class="sc-val" style="color:#8a5010">${s.learningCount}</span></div>
      <div class="sc-row"><span class="sc-label">Due today</span><span class="sc-val" style="color:#1a3f8a">${s.dueCount}</span></div>
      <div class="sc-row"><span class="sc-label">Not started</span><span class="sc-val">${s.newCount}</span></div>
      <div class="sc-row"><span class="sc-label">Removed</span><span class="sc-val" style="color:#900">${s.removedCount}</span></div>
      <div class="sc-row"><span class="sc-label">Auto-excluded</span><span class="sc-val" style="color:#888">${s.excludedCount}</span></div>
    </div>

    ${pv ? `<div class="proverb-card">"${esc(pv)}"</div>` : ''}

    <div class="sc">
      <div class="sc-title">Milestones</div>
      ${LEVELS.map(l => `
        <div class="milestone-row ${s.learned >= l.min ? 'reached' : ''}">
          <span class="ms-stars">${l.stars}</span>
          <span class="ms-name">${esc(l.name)}</span>
          <span class="ms-count">${l.min}</span>
          ${s.learned >= l.min ? '<span class="ms-check">✓</span>' : ''}
        </div>`).join('')}
    </div>`;
}

// ─────────────────────────────────────────────────────────────────
//  Help
// ─────────────────────────────────────────────────────────────────

function renderHelp() {
  $('help-content').innerHTML = `
    <div class="help-block">
      <h3>How to use</h3>
      <ul>
        <li><b>Next (≈Xd)</b> — Learned! Schedules next review in X days</li>
        <li><b>Review</b> — Need another look · appears again tomorrow</li>
        <li><b>Remove</b> — Skip forever from queue (still searchable)</li>
        <li>Swipe <b>left / right</b> on the card to navigate freely</li>
      </ul>
      <h3>Spaced Repetition Intervals</h3>
      <p>1 day → 3 days → 7 days → 14 days → 30 days → 60 days</p>
      <h3>Auto-filtered words</h3>
      <p>Articles, pronouns and prepositions are filtered out of drilling (still searchable). They are better learned through reading.</p>
      <h3>Menu</h3>
      <ul>
        <li><b>Today</b> — Rebuild today's session</li>
        <li><b>Next Batch</b> — Load next unlearned words</li>
        <li><b>Stats</b> — Your level, progress and milestones</li>
      </ul>
      <h3>Settings</h3>
      <p>Words per day: <b>${state.settings.wordsPerDay}</b></p>
      <div class="danger-zone">
        <h3>⚠️ Danger Zone</h3>
        <p>Erase all learning progress. Cannot be undone.</p>
        <button id="btn-reset-progress">Reset All Progress</button>
      </div>
    </div>`;

  $('btn-reset-progress').addEventListener('click', () => {
    if (confirm('Reset ALL progress? Cannot be undone.')) {
      if (confirm('Absolutely sure? All learned words forgotten.')) {
        Storage.clearAll(); location.reload();
      }
    }
  });
}

// ─────────────────────────────────────────────────────────────────
//  Reminders
// ─────────────────────────────────────────────────────────────────

async function enableReminder(time) {
  if (!('Notification' in window)) { toast('Notifications not supported'); return false; }
  let p = Notification.permission;
  if (p === 'default') p = await Notification.requestPermission();
  if (p !== 'granted') { toast('Notification permission denied'); return false; }
  state.settings.reminderEnabled = true;
  state.settings.reminderTime    = time;
  Storage.setSettings(state.settings);
  toast(`Reminder set for ${time} ✓`);
  return true;
}

function disableReminder() {
  state.settings.reminderEnabled = false;
  Storage.setSettings(state.settings);
  toast('Reminder off');
}

// ─────────────────────────────────────────────────────────────────
//  Event listeners
// ─────────────────────────────────────────────────────────────────

function setupEventListeners() {
  setupSwipe($('word-card'));

  // Translation toggle
  $('btn-show-translation').addEventListener('click', () => {
    state.showTranslation = !state.showTranslation;
    $('translation-block').classList.toggle('hidden', !state.showTranslation);
    $('example-display').style.display = '';  // always show example once card loaded
    const arrow = $('btn-show-translation').querySelector('.reveal-arrow');
    if (arrow) arrow.classList.toggle('open', state.showTranslation);
    $('btn-show-translation').innerHTML = state.showTranslation
      ? '<span class="reveal-arrow open">&#9658;</span> Hide translation'
      : '<span class="reveal-arrow">&#9658;</span> Show translation';
  });

  // Nav
  $('btn-prev').addEventListener('click', () => navigate(-1));
  $('btn-nav-next').addEventListener('click', () => navigate(1));

  // Actions
  $('btn-next').addEventListener('click', actionNext);
  $('btn-next-batch-card').addEventListener('click', actionNextBatch);
  $('btn-remove').addEventListener('click', actionRemoveToggle);

  // Menu
  document.querySelectorAll('.menu-btn').forEach(b => {
    b.addEventListener('click', () => {
      switch (b.dataset.action) {
        case 'today':      actionToday();          break;
        case 'review':     actionReview();         break;
        case 'themes':     showScreen('themes');   break;
        case 'stats':      showScreen('stats');    break;
        case 'help':       showScreen('help');     break;
      }
    });
  });

  // Back buttons
  document.querySelectorAll('.back-btn').forEach(b => {
    b.addEventListener('click', () => showScreen(b.dataset.back || 'main'));
  });

  // Exit theme session
  $('btn-exit-theme').addEventListener('click', () => {
    $('theme-banner').classList.add('hidden');
    state.session.themeKey = null;
    rebuildSession();
    renderCard();
    toast('Returned to daily session');
  });

  // Search on main controls
  const si = $('search-input');
  $('btn-search-go').addEventListener('click', () => {
    if (si.value.trim()) { showScreen('search'); doSearch(si.value); }
  });
  $('btn-search-clear').addEventListener('click', () => { si.value = ''; });
  si.addEventListener('keyup', e => {
    if (e.key === 'Enter' && si.value.trim()) { showScreen('search'); doSearch(si.value); }
  });

  // Reminder
  const bOff = $('btn-reminder-off'), bOn = $('btn-reminder-on'), ti = $('reminder-time');
  if (state.settings.reminderEnabled) {
    bOn.classList.add('active'); bOff.classList.remove('active');
    ti.value = state.settings.reminderTime || '09:00';
  }
  bOff.addEventListener('click', () => {
    disableReminder(); bOff.classList.add('active'); bOn.classList.remove('active');
  });
  bOn.addEventListener('click', async () => {
    if (await enableReminder(ti.value)) { bOn.classList.add('active'); bOff.classList.remove('active'); }
  });
}

// ─────────────────────────────────────────────────────────────────
//  Start
// ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);

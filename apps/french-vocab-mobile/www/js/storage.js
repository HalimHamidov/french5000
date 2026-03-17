/**
 * storage.js — All localStorage persistence.
 * Keys are prefixed with "fr5k_" to avoid collisions.
 */

const KEYS = {
  WORD_STATES: 'fr5k_word_states',
  SESSION:     'fr5k_session',
  SETTINGS:    'fr5k_settings',
};

const DEFAULTS_SETTINGS = {
  wordsPerDay:      15,
  reminderEnabled:  false,
  reminderTime:     '09:00',
};

export const Storage = {
  // ── Word states ──────────────────────────────────────────────

  getWordStates() {
    try {
      const raw = localStorage.getItem(KEYS.WORD_STATES);
      return raw ? JSON.parse(raw) : {};
    } catch {
      console.warn('storage: failed to read word states');
      return {};
    }
  },

  setWordStates(states) {
    try {
      localStorage.setItem(KEYS.WORD_STATES, JSON.stringify(states));
    } catch (e) {
      console.error('storage: failed to write word states', e);
    }
  },

  /** Merge patch into a single word's state and persist. Returns updated state. */
  updateWordState(wordId, patch) {
    const states = this.getWordStates();
    states[wordId] = { ...(states[wordId] || {}), ...patch };
    this.setWordStates(states);
    return states[wordId];
  },

  // ── Session ──────────────────────────────────────────────────

  getSession() {
    try {
      const raw = localStorage.getItem(KEYS.SESSION);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  setSession(session) {
    try {
      localStorage.setItem(KEYS.SESSION, JSON.stringify(session));
    } catch (e) {
      console.error('storage: failed to write session', e);
    }
  },

  // ── Settings ─────────────────────────────────────────────────

  getSettings() {
    try {
      const raw = localStorage.getItem(KEYS.SETTINGS);
      return raw ? { ...DEFAULTS_SETTINGS, ...JSON.parse(raw) } : { ...DEFAULTS_SETTINGS };
    } catch {
      return { ...DEFAULTS_SETTINGS };
    }
  },

  setSettings(settings) {
    try {
      localStorage.setItem(KEYS.SETTINGS, JSON.stringify(settings));
    } catch (e) {
      console.error('storage: failed to write settings', e);
    }
  },

  // ── Reset ────────────────────────────────────────────────────

  clearAll() {
    Object.values(KEYS).forEach(k => localStorage.removeItem(k));
  },
};

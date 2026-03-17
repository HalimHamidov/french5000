/**
 * scheduler.js — Spaced-repetition scheduling logic.
 *
 * Interval ladder (days after each successful "Next"):
 *   new → 1d → 3d → 7d → 14d → 30d → 60d
 *
 * Word statuses:
 *   'new'      — never seen
 *   'excluded' — auto-filtered (stopwords / grammar / noise)
 *   'learning' — in progress (step 0–4)
 *   'known'    — completed all steps (step ≥ 5)
 *   'removed'  — user-removed; kept searchable
 */

import { Storage } from './storage.js';

const INTERVALS = [1, 3, 7, 14, 30, 60]; // days

/** ISO date string for today (YYYY-MM-DD) */
function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

/** Midnight today as a Date object */
function midnight() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

/** ISO timestamp for N days from today's midnight */
function addDays(n) {
  const d = midnight();
  d.setDate(d.getDate() + n);
  return d.toISOString();
}

export class Scheduler {
  constructor(words) {
    this.words = words;
    /** Map wordId → word for fast lookup */
    this._idx = new Map(words.map(w => [w.id, w]));
  }

  getWord(id) {
    return this._idx.get(id) ?? null;
  }

  isDue(state) {
    if (!state?.nextReview) return true;
    return new Date(state.nextReview) <= midnight();
  }

  /**
   * Build the daily study queue.
   * Priority: due reviews first, then new words.
   * Returns array of { id, mode: 'new'|'review' }
   */
  buildDailyQueue(wordsPerDay, wordStates) {
    const dueReview = [];
    const newWords  = [];

    for (const word of this.words) {
      const s = wordStates[word.id];

      if (!s || s.status === 'new') {
        newWords.push(word.id);
        continue;
      }
      if (s.status === 'removed' || s.status === 'excluded') continue;

      if (s.status === 'learning' || s.status === 'known') {
        if (this.isDue(s)) dueReview.push(word.id);
      }
    }

    const queue = [];

    for (const id of dueReview) {
      if (queue.length >= wordsPerDay) break;
      queue.push({ id, mode: 'review' });
    }
    for (const id of newWords) {
      if (queue.length >= wordsPerDay) break;
      queue.push({ id, mode: 'new' });
    }

    return queue;
  }

  /**
   * User tapped "Next" — word was reviewed successfully.
   * Advances the interval step and schedules next review.
   */
  markNext(wordId, wordStates) {
    const s     = wordStates[wordId] || {};
    const step  = (s.step ?? 0) + 1;
    const days  = INTERVALS[Math.min(step - 1, INTERVALS.length - 1)];
    const status = step >= INTERVALS.length ? 'known' : 'learning';

    return Storage.updateWordState(wordId, {
      status,
      step,
      nextReview: addDays(days),
      lastSeen:   new Date().toISOString(),
    });
  }

  /**
   * User tapped "Review" — word needs another look.
   * Steps back one interval, schedules for tomorrow.
   */
  markReview(wordId, wordStates) {
    const s    = wordStates[wordId] || {};
    const step = Math.max((s.step ?? 0) - 1, 0);

    return Storage.updateWordState(wordId, {
      status:    'learning',
      step,
      nextReview: addDays(1),
      lastSeen:   new Date().toISOString(),
    });
  }

  /** User tapped "Remove" — exclude from queue forever (searchable). */
  markRemoved(wordId) {
    return Storage.updateWordState(wordId, {
      status:   'removed',
      lastSeen: new Date().toISOString(),
    });
  }

  /** Restore a removed word back to "new". */
  markRestored(wordId) {
    return Storage.updateWordState(wordId, {
      status:    'new',
      step:       0,
      nextReview: null,
      lastSeen:   new Date().toISOString(),
    });
  }

  /**
   * Compute summary statistics for the stats screen.
   */
  getStats(wordStates) {
    let newCount = 0, learningCount = 0, knownCount = 0,
        removedCount = 0, excludedCount = 0, dueCount = 0;

    for (const word of this.words) {
      const s = wordStates[word.id];

      if (s?.status === 'excluded') { excludedCount++; continue; }
      if (!s || s.status === 'new') { newCount++;       continue; }

      switch (s.status) {
        case 'learning':
          learningCount++;
          if (this.isDue(s)) dueCount++;
          break;
        case 'known':
          knownCount++;
          if (this.isDue(s)) dueCount++;
          break;
        case 'removed':
          removedCount++;
          break;
        default:
          newCount++;
      }
    }

    const total   = this.words.length;
    const active  = total - excludedCount - removedCount;
    const learned = knownCount;
    const pct     = active > 0 ? Math.round((learned / active) * 100) : 0;

    return {
      total, newCount, learningCount, knownCount,
      removedCount, excludedCount, dueCount,
      learned, active, pct,
    };
  }

  /** Interval preview string for the Next button label. */
  nextIntervalLabel(wordId, wordStates) {
    const s    = wordStates[wordId] || {};
    const step = s.step ?? 0;
    const days = INTERVALS[Math.min(step, INTERVALS.length - 1)];
    return days >= 30 ? `+${days}d` : `+${days}d`;
  }
}

/**
 * loader.js — Fetches and normalises JSON vocabulary data.
 *
 * Frequency dict schema  (french_frequency_dictionary.json):
 *   id, rank, word, lemma, ipa, pos, translation_en, translation_ru,
 *   example_fr, example_en, example_ru, collocations, semantic_cluster,
 *   audio, notes
 *
 * Thematic vocab schema  (french_thematic_vocabulary.json):
 *   { "<theme_key>": { id, title, words: [{word, ipa, translation_en,
 *     translation_ru, pos, notes, rank_reference}] } }
 *
 * The mapWord() function auto-detects field names so the loader is
 * resilient to minor schema drift.
 */

// POS tags that indicate "grammar glue" — useful to understand through
// immersion but counterproductive to drill as flashcards.
const GRAMMAR_POS = new Set([
  'determiner', 'preposition', 'pronoun', 'conjunction',
  'particle', 'interjection', 'article',
]);

// Explicit stopword list (covers top-20 most frequent French function words)
const STOPWORDS = new Set([
  'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une',
  'et', 'est', 'en', 'à', 'au', 'aux',
  'ce', 'se', 'ne', 'je', 'tu', 'il', 'elle',
  'nous', 'vous', 'ils', 'elles',
  'me', 'te', 'lui', 'y', 'que', 'qui',
  'mon', 'ma', 'mes', 'ton', 'ta', 'tes',
  'son', 'sa', 'ses', 'notre', 'votre', 'leur', 'leurs',
  'pas', 'plus', 'très', 'bien', 'non',
]);

/**
 * Safely map a raw JSON object to a normalised word record.
 * Unknown fields are tolerated; missing required fields return null.
 */
export function mapWord(raw) {
  if (!raw || typeof raw !== 'object') return null;

  const word = (raw.word || raw.lemma || '').trim();
  if (!word) return null;

  return {
    id:              raw.id   ?? raw.rank ?? 0,
    rank:            raw.rank ?? raw.id   ?? 0,
    word,
    lemma:           (raw.lemma || raw.word || '').trim(),
    ipa:             (raw.ipa  || '').trim(),
    pos:             (raw.pos  || '').trim().toLowerCase(),
    translation_en:  (raw.translation_en || raw.translation || raw.meaning || '').trim(),
    translation_ru:  (raw.translation_ru || '').trim(),
    example_fr:      (raw.example_fr || raw.example || '').trim(),
    example_en:      (raw.example_en || '').trim(),
    example_ru:      (raw.example_ru || '').trim(),
    collocations:    Array.isArray(raw.collocations) ? raw.collocations : [],
    semantic_cluster: raw.semantic_cluster ?? null,
    audio:           raw.audio ?? null,
    notes:           raw.notes ?? null,
  };
}

/**
 * Returns a string exclusion reason, or null if word should be kept.
 *
 * Excluded words are hidden from the learning queue but remain searchable.
 * Reason is stored so stats can show a breakdown.
 */
export function shouldExclude(word) {
  if (!word.word || word.word.length <= 1) return 'single_char';
  if (GRAMMAR_POS.has(word.pos))           return 'grammar_pos';
  if (STOPWORDS.has(word.word.toLowerCase())) return 'stopword';

  // Heuristic: capitalised words beyond rank 100 are likely proper nouns.
  // (rank <= 100 includes common sentence-starters like "Le", "La" etc.)
  if (
    word.rank > 100 &&
    word.word[0] === word.word[0].toUpperCase() &&
    word.word[0] !== word.word[0].toLowerCase()
  ) {
    return 'proper_name';
  }

  return null;
}

/** Fetch and parse JSON with a descriptive error on failure. */
async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} loading ${url}`);
  }
  return res.json();
}

/** Load and normalise the 5000-word frequency list. */
export async function loadFrequencyData() {
  const raw = await fetchJSON('data/french_frequency_dictionary.json');

  if (!Array.isArray(raw)) {
    throw new Error('Expected an array in french_frequency_dictionary.json');
  }

  const words    = [];
  const warnings = [];

  for (let i = 0; i < raw.length; i++) {
    try {
      const w = mapWord(raw[i]);
      if (w) {
        words.push(w);
      } else {
        warnings.push(`Row ${i}: skipped (no word field)`);
      }
    } catch (e) {
      warnings.push(`Row ${i}: ${e.message}`);
    }
  }

  if (warnings.length) {
    console.warn(`loader: ${warnings.length} warnings loading frequency data:`, warnings.slice(0, 5));
  }
  console.info(`loader: ${words.length} frequency words loaded`);
  return words;
}

/** Load the thematic vocabulary (dict of theme → word list). */
export async function loadThematicData() {
  const raw = await fetchJSON('data/french_thematic_vocabulary.json');
  console.info(`loader: ${Object.keys(raw).length} themes loaded`);
  return raw;
}

/**
 * prepare.js — Copies JSON data files from data/processed/ into www/data/
 * Run before dev server or Capacitor build.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', '..', '..');
const DATA_SRC = path.join(ROOT, 'data', 'processed');
const DATA_DST = path.join(__dirname, '..', 'www', 'data');

const FILES = [
  'french_frequency_dictionary.json',
  'french_thematic_vocabulary.json',
];

if (!fs.existsSync(DATA_DST)) {
  fs.mkdirSync(DATA_DST, { recursive: true });
}

let ok = 0;
for (const file of FILES) {
  const src = path.join(DATA_SRC, file);
  const dst = path.join(DATA_DST, file);
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dst);
    const size = (fs.statSync(dst).size / 1024).toFixed(1);
    console.log(`  ✓ ${file} (${size} KB)`);
    ok++;
  } else {
    console.error(`  ✗ Not found: ${src}`);
  }
}

if (ok === FILES.length) {
  console.log(`\nData ready in www/data/ (${ok}/${FILES.length} files)`);
} else {
  console.error(`\nWarning: only ${ok}/${FILES.length} files copied.`);
  process.exit(1);
}

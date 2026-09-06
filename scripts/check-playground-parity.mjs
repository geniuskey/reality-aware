/**
 * Replay Python's decisions through the engine the playground page actually ships.
 *
 * The page claims to re-run the benchmark's loop rather than approximate it. This
 * checks that claim against the engine embedded in the built HTML — not against a
 * copy of it — using the traces `python -m nano.playground` exported from
 * nano.agent.run_episode, and stamps the counts back into the page so the number
 * it prints is the number this script measured.
 *
 * One divergence is expected and documented on the page: `novelty` alone ties the
 * argmax constantly, because distance to the nearest measured die is quantised on
 * a die lattice. Python breaks those ties with the episode's seeded generator, the
 * browser by lowest index. A divergence under any other rule is a real defect and
 * fails this script.
 */

import { readFileSync, writeFileSync } from 'node:fs';
import vm from 'node:vm';

const PAGE = process.argv[2] ?? 'docs/public/playground.html';
const REFERENCE = process.argv[3] ?? 'playground/reference.json';

const ENGINE_START = '// ------------------------------------------------------------------ engine';
const ENGINE_END = '// ------------------------------------------------------------- colour maps';
const DATA_OPEN = '<script type="application/json" id="wafer-data">';

const html = readFileSync(PAGE, 'utf8');

function slice(text, start, end, what) {
  const a = text.indexOf(start);
  const b = text.indexOf(end, a + start.length);
  if (a === -1 || b === -1) throw new Error(`${PAGE}: could not find the ${what}`);
  return text.slice(a + start.length, b);
}

const payload = slice(html, DATA_OPEN, '</script>', 'wafer data');
const engineSource = slice(html, ENGINE_START, ENGINE_END, 'engine block');

const data = JSON.parse(payload);
const reference = JSON.parse(readFileSync(REFERENCE, 'utf8'));

const context = { module: { exports: {} } };
vm.createContext(context);
vm.runInContext(`${engineSource}\nmodule.exports = { prepareWafer, runEpisode };`, context, {
  filename: 'playground-engine.js'
});
const { prepareWafer, runEpisode } = context.module.exports;

const budget = data.loop.budget;
const wafers = new Map(data.wafers.map((raw) => [raw.id, prepareWafer(raw)]));

let checked = 0;
const failures = [];

for (const [key, expected] of Object.entries(reference)) {
  const [waferId, seed, rule] = key.split('|');
  const wafer = wafers.get(waferId);
  if (!wafer) throw new Error(`reference names ${waferId}, which the page does not carry`);
  const initial = wafer.seeds[seed].initial;
  const { observed } = runEpisode(wafer, { initial, budget, terms: rule.split('+') });
  const got = observed.slice(initial.length);
  checked++;

  let first = -1;
  for (let i = 0; i < expected.length; i++) {
    if (got[i] !== expected[i]) {
      first = i;
      break;
    }
  }
  if (first !== -1) failures.push({ key, rule, first, got: got[first], want: expected[first] });
}

const byRule = {};
for (const f of failures) byRule[f.rule] = (byRule[f.rule] || 0) + 1;

console.log(`${PAGE}`);
console.log(`  checked   ${checked} traces of ${budget} decisions each`);
console.log(`  identical ${checked - failures.length}`);
console.log(`  divergent ${failures.length}`);
for (const [rule, count] of Object.entries(byRule)) console.log(`    ${rule}: ${count}`);

const unexpected = failures.filter((f) => f.rule !== 'novelty');
if (unexpected.length) {
  console.error('\nDivergence outside the documented novelty tie-break:');
  for (const f of unexpected.slice(0, 10)) {
    console.error(`  ${f.key} at decision ${f.first}: page ${f.got}, python ${f.want}`);
  }
  process.exit(1);
}

const parity = {
  checked,
  identical: checked - failures.length,
  divergent: failures.length,
  divergentRules: Object.keys(byRule).sort()
};

const SLOT = /"parity":(?:null|\{[^{}]*\})/;
if (!SLOT.test(html)) throw new Error(`${PAGE}: no parity slot to stamp`);

// A committed page already carries the counts from the last run, so re-stamping
// is usually a no-op. That is the expected state in CI and must not fail.
const stamp = `"parity":${JSON.stringify(parity)}`;
const stamped = html.replace(SLOT, stamp);
if (stamped !== html) writeFileSync(PAGE, stamped, 'utf8');
console.log(`  stamped   ${stamp}${stamped === html ? ' (unchanged)' : ' (rewritten)'}`);

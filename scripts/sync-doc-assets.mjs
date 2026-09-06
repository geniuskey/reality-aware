#!/usr/bin/env node
/**
 * Copies published experiment figures from the canonical results/ directory into
 * docs/public/results/, where the site reads them.
 *
 * Missing figures are reported, not fatal: pages render an explicit
 * "Run benchmark to generate results" state instead of a broken image.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const from = path.join(root, 'results')
const to = path.join(root, 'docs', 'public', 'results')

/** Figures the site knows how to display. Anything else stays out of docs/. */
const published = [
  'error_curve.svg',
  'wafer_comparison.webp',
  'uncertainty_before_after.webp',
  'paired_improvement.svg',
  'demo.gif',
  'demo_step_00.webp',
  'demo_step_05.webp',
  'demo_selection.webp',
  'demo_final.webp'
]

const copied = []
const missing = []

fs.mkdirSync(to, { recursive: true })

for (const name of published) {
  const src = path.join(from, name)
  if (!fs.existsSync(src)) {
    missing.push(name)
    continue
  }
  fs.copyFileSync(src, path.join(to, name))
  const kb = (fs.statSync(src).size / 1024).toFixed(0)
  copied.push(`${name} (${kb} KB)`)
}

console.log(`sync-doc-assets: ${from} -> ${to}`)
if (copied.length) {
  console.log(`  copied ${copied.length}:`)
  for (const line of copied) console.log(`    + ${line}`)
} else {
  console.log('  copied 0')
}
if (missing.length) {
  console.log(`  not generated yet (${missing.length}): ${missing.join(', ')}`)
  console.log('  pages will show "Run benchmark to generate results" for these.')
}

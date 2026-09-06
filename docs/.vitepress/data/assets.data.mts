import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * Lists whatever the benchmark has copied into docs/public/results.
 * Pages use it so a missing figure renders an explicit "not generated yet"
 * state instead of a broken image, and the build never fails on absent assets.
 */
const here = path.dirname(fileURLToPath(import.meta.url))
const resultsDir = path.resolve(here, '../../public/results')

export type ResultAssets = { files: string[]; dir: string }

declare const data: ResultAssets
export { data }

export default {
  watch: ['../../public/results/*'],
  load(): ResultAssets {
    const dir = 'docs/public/results'
    if (!fs.existsSync(resultsDir)) return { files: [], dir }
    const files = fs
      .readdirSync(resultsDir, { withFileTypes: true })
      .filter((entry) => entry.isFile() && !entry.name.startsWith('.'))
      .map((entry) => entry.name)
      .sort()
    return { files, dir }
  }
}

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const summaryPath = path.join(root, 'results', 'benchmark_summary.json')

export type Point = { measurements: number; mean: number; std?: number }
export type Strategy = {
  label: string
  description?: string
  final: { mean: number; std?: number }
  curve?: Point[]
}
export type BenchmarkSummary = {
  schema_version: number
  generated_at?: string
  git_commit?: string
  dataset?: { name?: string; subset_file?: string; n_wafers?: number }
  experiment?: {
    seeds?: number[]
    initial_measurements?: number
    measurement_budget?: number
    grid_shape?: [number, number]
  }
  metric?: { name?: string; direction?: 'lower_is_better' | 'higher_is_better'; unit?: string }
  prior?: { initial_error?: { mean: number; std?: number } }
  strategies?: Record<string, Strategy>
  assets?: Record<string, string>
}
export type BenchmarkData = {
  available: boolean
  summary: BenchmarkSummary | null
  sourcePath: string
}

declare const data: BenchmarkData
export { data }

export default {
  watch: [summaryPath],
  load(): BenchmarkData {
    const sourcePath = 'results/benchmark_summary.json'
    if (!fs.existsSync(summaryPath)) {
      return { available: false, summary: null, sourcePath }
    }

    let parsed: BenchmarkSummary
    try {
      parsed = JSON.parse(fs.readFileSync(summaryPath, 'utf-8'))
    } catch (error) {
      throw new Error(
        `[nano] ${sourcePath} exists but is not valid JSON. Fix or delete it — the site will not invent numbers.\n${
          (error as Error).message
        }`
      )
    }

    if (typeof parsed.schema_version !== 'number' || !parsed.strategies) {
      throw new Error(
        `[nano] ${sourcePath} is missing "schema_version" or "strategies". See docs/benchmark.md for the expected schema.`
      )
    }

    return { available: true, summary: parsed, sourcePath }
  }
}

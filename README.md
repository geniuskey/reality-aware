# NANO — Reality-Aware AI Development Lifecycle for Semiconductor Manufacturing

An autonomous metrology agent that identifies what it does not know and selects the next most
valuable measurement to close the Sim2Real gap.

**Maximize knowledge of reality per measurement.**

Docs site: <https://geniuskey.github.io/reality-aware/> (Korean: <https://geniuskey.github.io/reality-aware/ko/>)

## Status

This repository currently contains the **documentation site only**. The agent, the WM-811K subset
builder and the benchmark harness are not implemented yet, so the site ships **no benchmark
numbers**: every metric, table and chart reads from `results/benchmark_summary.json` and shows
`Run benchmark to generate results` until that file exists.

See [Honest Scope](https://geniuskey.github.io/reality-aware/limitations) for what is claimed and
what is not.

## Run the docs locally

Requires Node 20 or newer.

```bash
npm ci            # or: npm install
npm run docs:dev  # http://localhost:5173/reality-aware/
```

Other scripts:

```bash
npm run docs:build    # static build into docs/.vitepress/dist
npm run docs:preview  # serve the build
npm run sync:assets   # copy figures from results/ into docs/public/results/
```

The site's base path is derived from `GITHUB_REPOSITORY`, so a fork builds at its own path with no
edits. Override it locally when needed:

```bash
DOCS_BASE=/ npm run docs:build          # user or org Pages (<owner>.github.io)
DOCS_BASE=/my-fork/ npm run docs:build  # a differently named fork
```

## Deploying to GitHub Pages

`.github/workflows/deploy-docs.yml` builds and publishes on every push to `main`.

**One manual step is required:** in the repository, go to **Settings → Pages** and set
**Source** to **GitHub Actions**. Without it the workflow builds successfully but nothing is
published.

## Layout

| Path | Contents |
| --- | --- |
| `docs/` | English Markdown pages, VitePress config, theme and Vue components |
| `docs/ko/` | Korean translation of every page |
| `docs/public/` | Logo, favicon, social card, published result figures |
| `results/` | Canonical benchmark output — `benchmark_summary.json` and generated figures |
| `scripts/` | `sync-doc-assets.mjs`, social-card source |
| `.github/workflows/` | Pages deployment |

`results/` is the single source of truth for numbers. Nothing is hand-typed into the Markdown, so a
figure cannot go stale in one place and be correct in another.

## Data

The experiment uses the **WM-811K wafer map dataset** (Wu, Jang & Chen, IEEE Transactions on
Semiconductor Manufacturing, 2015). No raw dataset files are committed here; download it locally and
check the licence on the page you download from before redistributing. Details on the
[Dataset & Design page](https://geniuskey.github.io/reality-aware/data).

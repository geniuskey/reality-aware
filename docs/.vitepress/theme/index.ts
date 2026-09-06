import { h } from 'vue'
import { inBrowser } from 'vitepress'
import type { Theme } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import './custom.css'

import AblationTable from './components/AblationTable.vue'
import AgentLoop from './components/AgentLoop.vue'
import BenchmarkChart from './components/BenchmarkChart.vue'
import BenchmarkTable from './components/BenchmarkTable.vue'
import EvidenceStrip from './components/EvidenceStrip.vue'
import MetricCard from './components/MetricCard.vue'
import PatternTable from './components/PatternTable.vue'
import PlaygroundLink from './components/PlaygroundLink.vue'
import ResultAsset from './components/ResultAsset.vue'
import WaferComparison from './components/WaferComparison.vue'

/**
 * The playground is a file in `public/`, not a VitePress route, so the SPA
 * router has no chunk for `/playground`: left alone, it renders the theme's 404
 * over a page that exists. Its own click handler bails on an event that has
 * already been handled, and this module is imported before the router is built,
 * so claiming the click here is enough to hand the link to the browser.
 *
 * Doing it once, here, means every link works — the nav, the sidebar, prose, and
 * the prev/next pager the theme generates from the sidebar without a way to mark
 * it. Modified clicks are left alone so a reader can still open a tab.
 */
if (inBrowser) {
  window.addEventListener(
    'click',
    (e) => {
      if (e.defaultPrevented || e.button !== 0) return
      if (e.ctrlKey || e.shiftKey || e.altKey || e.metaKey) return
      const link = (e.target as Element | null)?.closest?.('a')
      const href = link?.getAttribute('href')
      if (!href) return
      const to = new URL(href, link!.baseURI)
      if (to.origin !== location.origin) return
      if (!to.pathname.replace(/\.html$/, '').endsWith('/playground')) return
      e.preventDefault()
      location.href = to.href
    },
    { capture: true }
  )
}

export default {
  extends: DefaultTheme,
  Layout: () =>
    h(DefaultTheme.Layout, null, {
      // The team and event names are proper nouns, so this line is identical
      // in both locales.
      'home-hero-before': () =>
        h('p', { class: 'nano-hero-eyebrow' }, 'Team NANO · AI Development Lifecycle Hackathon')
    }),
  enhanceApp({ app }) {
    app.component('AgentLoop', AgentLoop)
    app.component('BenchmarkChart', BenchmarkChart)
    app.component('BenchmarkTable', BenchmarkTable)
    app.component('EvidenceStrip', EvidenceStrip)
    app.component('MetricCard', MetricCard)
    app.component('AblationTable', AblationTable)
    app.component('PatternTable', PatternTable)
    app.component('PlaygroundLink', PlaygroundLink)
    app.component('ResultAsset', ResultAsset)
    app.component('WaferComparison', WaferComparison)
  }
} satisfies Theme

import { h } from 'vue'
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
import ResultAsset from './components/ResultAsset.vue'
import WaferComparison from './components/WaferComparison.vue'

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
    app.component('ResultAsset', ResultAsset)
    app.component('WaferComparison', WaferComparison)
  }
} satisfies Theme

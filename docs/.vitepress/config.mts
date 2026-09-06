import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

const repo = process.env.GITHUB_REPOSITORY?.split('/')[1] ?? 'reality-aware'
const owner = process.env.GITHUB_REPOSITORY?.split('/')[0] ?? 'geniuskey'
const isUserPages = repo.endsWith('.github.io')

/** Normalise an override like `my-fork` or `/my-fork` into `/my-fork/`. */
function normaliseBase(value: string | undefined) {
  if (!value) return undefined
  const trimmed = value.trim()
  if (!trimmed || trimmed === '/') return '/'
  return `/${trimmed.replace(/^\/+|\/+$/g, '')}/`
}

const base = normaliseBase(process.env.DOCS_BASE) ?? (isUserPages ? '/' : `/${repo}/`)
const repoUrl = `https://github.com/${owner}/${repo}`
const siteUrl = `https://${owner}.github.io${base}`

const title = 'NANO'
const description =
  'An autonomous metrology agent that identifies what it does not know and selects the next most valuable measurement to close the Sim2Real gap.'

export default withMermaid(
  defineConfig({
    lang: 'en-US',
    title,
    description,
    base,
    cleanUrls: true,
    lastUpdated: true,
    ignoreDeadLinks: false,

    head: [
      ['link', { rel: 'icon', type: 'image/svg+xml', href: `${base}favicon.svg` }],
      ['meta', { name: 'theme-color', content: '#0b1017' }],
      ['meta', { property: 'og:type', content: 'website' }],
      ['meta', { property: 'og:site_name', content: 'NANO' }],
      ['meta', { property: 'og:title', content: 'NANO — Reality-Aware AI Development Lifecycle' }],
      ['meta', { property: 'og:description', content: description }],
      ['meta', { property: 'og:url', content: siteUrl }],
      ['meta', { property: 'og:image', content: `${siteUrl}social-card.png` }],
      ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
      ['meta', { name: 'twitter:title', content: 'NANO — Reality-Aware AI Development Lifecycle' }],
      ['meta', { name: 'twitter:description', content: description }],
      ['meta', { name: 'twitter:image', content: `${siteUrl}social-card.png` }]
    ],

    transformPageData(pageData) {
      const canonical =
        siteUrl + pageData.relativePath.replace(/index\.md$/, '').replace(/\.md$/, '')
      pageData.frontmatter.head ??= []
      pageData.frontmatter.head.push(['link', { rel: 'canonical', href: canonical }])
    },

    themeConfig: {
      logo: '/logo.svg',
      siteTitle: 'NANO',

      nav: [
        { text: 'Overview', link: '/problem' },
        { text: 'Approach', link: '/approach' },
        { text: 'Data', link: '/data' },
        { text: 'Results', link: '/benchmark' },
        { text: 'Demo', link: '/demo' },
        { text: 'Reproduce', link: '/reproducibility' }
      ],

      sidebar: [
        {
          text: 'Why',
          items: [
            { text: 'Why Reality Awareness?', link: '/problem' },
            { text: 'Honest Scope', link: '/limitations' }
          ]
        },
        {
          text: 'How',
          items: [
            { text: 'Agentic Active Metrology', link: '/approach' },
            { text: 'System Design', link: '/architecture' }
          ]
        },
        {
          text: 'Evidence',
          items: [
            { text: 'Dataset & Design', link: '/data' },
            { text: 'Benchmark', link: '/benchmark' },
            { text: 'Demo', link: '/demo' }
          ]
        },
        {
          text: 'Run It',
          items: [{ text: 'Reproducibility', link: '/reproducibility' }]
        }
      ],

      socialLinks: [{ icon: 'github', link: repoUrl }],

      editLink: {
        pattern: `${repoUrl}/edit/main/docs/:path`,
        text: 'Edit this page on GitHub'
      },

      search: { provider: 'local' },

      outline: { level: [2, 3], label: 'On this page' },

      footer: {
        message: 'Built for the AI Development Lifecycle Hackathon. Content is research prototype material, not production guidance.',
        copyright: `<a href="${repoUrl}">Source on GitHub</a>`
      }
    },

    vite: {
      build: {
        // Mermaid ships each diagram renderer as its own lazily-loaded chunk
        // (cytoscape, katex, cynefin and friends). This site renders flowcharts
        // only, so those chunks are never fetched by a visitor. Raise the limit
        // rather than warn about code nobody downloads.
        chunkSizeWarningLimit: 900
      }
    },

    mermaid: {
      theme: 'base',
      themeVariables: {
        fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        primaryColor: '#132030',
        primaryTextColor: '#dbe7f3',
        primaryBorderColor: '#2ec4d6',
        lineColor: '#5b7189',
        secondaryColor: '#1a2536',
        tertiaryColor: '#101a27'
      }
    },

    mermaidPlugin: {
      class: 'mermaid nano-diagram'
    }
  })
)

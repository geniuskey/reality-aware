import { defineConfig, type DefaultTheme } from 'vitepress'
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
const descriptionEn =
  'An autonomous metrology agent that identifies what it does not know and selects the next most valuable measurement to close the Sim2Real gap.'
const descriptionKo =
  '무엇을 모르는지 스스로 식별하고, Sim2Real 격차를 줄이는 데 가장 가치 있는 다음 측정을 선택하는 자율 계측 에이전트.'

/**
 * The playground is a standalone page in `public/`, not a VitePress route. The
 * theme prepends the base to a root-relative link, and the page picks its own
 * language from the query string rather than from a locale directory.
 */
const playgroundLink = (prefix: string) =>
  `/playground.html${prefix === '/ko' ? '?lang=ko' : ''}`

/** Nav and sidebar for one locale. `prefix` is '' for English, '/ko' for Korean. */
function navigation(prefix: string, l: Record<string, string>) {
  const nav: DefaultTheme.NavItem[] = [
    { text: l.overview, link: `${prefix}/problem` },
    { text: l.approach, link: `${prefix}/approach` },
    { text: l.data, link: `${prefix}/data` },
    { text: l.results, link: `${prefix}/benchmark` },
    { text: l.demo, link: `${prefix}/demo` },
    { text: l.playground, link: playgroundLink(prefix) },
    { text: l.reproduce, link: `${prefix}/reproducibility` }
  ]

  const sidebar: DefaultTheme.SidebarItem[] = [
    {
      text: l.groupWhy,
      items: [
        { text: l.problem, link: `${prefix}/problem` },
        { text: l.limitations, link: `${prefix}/limitations` }
      ]
    },
    {
      text: l.groupHow,
      items: [
        { text: l.approachPage, link: `${prefix}/approach` },
        { text: l.architecture, link: `${prefix}/architecture` }
      ]
    },
    {
      text: l.groupEvidence,
      items: [
        { text: l.dataPage, link: `${prefix}/data` },
        { text: l.benchmark, link: `${prefix}/benchmark` },
        { text: l.demoPage, link: `${prefix}/demo` },
        { text: l.playgroundPage, link: playgroundLink(prefix) }
      ]
    },
    {
      text: l.groupRun,
      items: [{ text: l.reproducePage, link: `${prefix}/reproducibility` }]
    }
  ]

  return { nav, sidebar }
}

const en = navigation('', {
  overview: 'Overview',
  approach: 'Approach',
  data: 'Data',
  results: 'Results',
  demo: 'Demo',
  playground: 'Playground',
  reproduce: 'Reproduce',
  groupWhy: 'Why',
  groupHow: 'How',
  groupEvidence: 'Evidence',
  groupRun: 'Run It',
  problem: 'Why Reality Awareness?',
  limitations: 'Honest Scope',
  approachPage: 'Agentic Active Metrology',
  architecture: 'System Design',
  dataPage: 'Dataset & Design',
  benchmark: 'Benchmark',
  demoPage: 'Demo',
  playgroundPage: 'Playground',
  reproducePage: 'Reproducibility'
})

const ko = navigation('/ko', {
  overview: '개요',
  approach: '접근 방식',
  data: '데이터',
  results: '결과',
  demo: '데모',
  playground: '플레이그라운드',
  reproduce: '재현',
  groupWhy: '왜',
  groupHow: '어떻게',
  groupEvidence: '근거',
  groupRun: '실행',
  problem: '왜 실제 인식이 필요한가',
  limitations: '정직한 범위',
  approachPage: '에이전트 기반 능동 계측',
  architecture: '시스템 설계',
  dataPage: '데이터셋과 실험 설계',
  benchmark: '벤치마크',
  demoPage: '데모',
  playgroundPage: '플레이그라운드',
  reproducePage: '재현 방법'
})

export default withMermaid(
  defineConfig({
    title,
    description: descriptionEn,
    base,
    cleanUrls: true,
    lastUpdated: true,
    ignoreDeadLinks: false,

    locales: {
      root: {
        label: 'English',
        lang: 'en-US',
        title,
        description: descriptionEn,
        themeConfig: {
          nav: en.nav,
          sidebar: en.sidebar,
          editLink: {
            pattern: `${repoUrl}/edit/main/docs/:path`,
            text: 'Edit this page on GitHub'
          },
          outline: { level: [2, 3], label: 'On this page' },
          footer: {
            message:
              'Built for the AI Development Lifecycle Hackathon. Content is research prototype material, not production guidance.',
            copyright: `<a href="${repoUrl}">Source on GitHub</a>`
          },
          docFooter: { prev: 'Previous page', next: 'Next page' },
          darkModeSwitchLabel: 'Appearance',
          returnToTopLabel: 'Return to top',
          sidebarMenuLabel: 'Menu',
          langMenuLabel: 'Change language'
        }
      },

      ko: {
        label: '한국어',
        lang: 'ko-KR',
        link: '/ko/',
        title,
        description: descriptionKo,
        themeConfig: {
          nav: ko.nav,
          sidebar: ko.sidebar,
          editLink: {
            pattern: `${repoUrl}/edit/main/docs/:path`,
            text: 'GitHub에서 이 페이지 수정하기'
          },
          outline: { level: [2, 3], label: '이 페이지에서' },
          footer: {
            message:
              'AI Development Lifecycle Hackathon 출품작입니다. 이 문서는 연구 프로토타입 자료이며 프로덕션 가이드가 아닙니다.',
            copyright: `<a href="${repoUrl}">GitHub 저장소</a>`
          },
          docFooter: { prev: '이전 페이지', next: '다음 페이지' },
          darkModeSwitchLabel: '테마',
          lightModeSwitchTitle: '라이트 모드로 전환',
          darkModeSwitchTitle: '다크 모드로 전환',
          returnToTopLabel: '맨 위로',
          sidebarMenuLabel: '메뉴',
          langMenuLabel: '언어 변경',
          notFound: {
            title: '페이지를 찾을 수 없습니다',
            quote: '요청한 페이지가 없습니다. 주소를 확인하거나 홈으로 돌아가세요.',
            linkLabel: '홈으로',
            linkText: '홈으로 돌아가기'
          }
        }
      }
    },

    head: [
      ['link', { rel: 'icon', type: 'image/svg+xml', href: `${base}favicon.svg` }],
      ['meta', { name: 'theme-color', content: '#0b1017' }],
      ['meta', { property: 'og:type', content: 'website' }],
      ['meta', { property: 'og:site_name', content: 'NANO' }],
      ['meta', { property: 'og:image', content: `${siteUrl}social-card.png` }],
      ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
      ['meta', { name: 'twitter:image', content: `${siteUrl}social-card.png` }]
    ],

    transformPageData(pageData) {
      // `benchmark.md` -> `benchmark`, `index.md` -> ``, `ko/index.md` -> `ko/`
      const rel = pageData.relativePath.replace(/index\.md$/, '').replace(/\.md$/, '')
      const isKo = rel === 'ko/' || rel.startsWith('ko/')
      const enRel = isKo ? rel.slice(3) : rel
      const koRel = isKo ? rel : `ko/${rel}`

      const description = isKo ? descriptionKo : descriptionEn
      const ogTitle = isKo
        ? 'NANO — 반도체 제조를 위한 실제 인식형 AI 개발 라이프사이클'
        : 'NANO — Reality-Aware AI Development Lifecycle'

      pageData.frontmatter.head ??= []
      pageData.frontmatter.head.push(
        ['link', { rel: 'canonical', href: siteUrl + rel }],
        // Both locales are complete translations of each other, so tell search
        // engines they are alternates rather than duplicates.
        ['link', { rel: 'alternate', hreflang: 'en', href: siteUrl + enRel }],
        ['link', { rel: 'alternate', hreflang: 'ko', href: siteUrl + koRel }],
        ['link', { rel: 'alternate', hreflang: 'x-default', href: siteUrl + enRel }],
        ['meta', { property: 'og:url', content: siteUrl + rel }],
        ['meta', { property: 'og:locale', content: isKo ? 'ko_KR' : 'en_US' }],
        ['meta', { property: 'og:title', content: ogTitle }],
        ['meta', { property: 'og:description', content: description }],
        ['meta', { name: 'twitter:title', content: ogTitle }],
        ['meta', { name: 'twitter:description', content: description }]
      )
    },

    themeConfig: {
      logo: '/logo.svg',
      siteTitle: 'NANO',

      socialLinks: [{ icon: 'github', link: repoUrl }],

      search: {
        provider: 'local',
        options: {
          locales: {
            ko: {
              translations: {
                button: { buttonText: '검색', buttonAriaLabel: '검색' },
                modal: {
                  displayDetails: '상세 보기',
                  resetButtonTitle: '검색어 지우기',
                  backButtonTitle: '뒤로',
                  noResultsText: '검색 결과가 없습니다',
                  footer: {
                    selectText: '선택',
                    selectKeyAriaLabel: 'Enter',
                    navigateText: '이동',
                    navigateUpKeyAriaLabel: '위쪽 화살표',
                    navigateDownKeyAriaLabel: '아래쪽 화살표',
                    closeText: '닫기',
                    closeKeyAriaLabel: 'Escape'
                  }
                }
              }
            }
          }
        }
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

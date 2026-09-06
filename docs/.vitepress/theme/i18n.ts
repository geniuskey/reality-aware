import { computed, type ComputedRef } from 'vue'
import { useData } from 'vitepress'

/**
 * Strings baked into components rather than Markdown. Everything here is
 * resolved during the static build, so both locales render as complete HTML
 * with no client-side translation step.
 *
 * Terminology is fixed on purpose - see docs/limitations.md. `prior`,
 * `ground truth`, `Sim2Real` and `die` stay in English in the Korean copy
 * because that is how they are used in the field.
 */
const en = {
  pending: 'Run benchmark to generate results',
  conceptual: 'Conceptual illustration',
  notMeasured: 'not measured',
  lowerIsBetter: '↓ lower is better',
  higherIsBetter: '↑ higher is better',

  loop: {
    steps: [
      {
        name: 'Observe',
        text: 'Read the sparse set of real measurements available so far, plus the simulation prior for every die.'
      },
      {
        name: 'Estimate',
        text: 'Fit a spatial model of reality and produce three maps: prediction, uncertainty, and prior-vs-reality gap.'
      },
      {
        name: 'Select',
        text: 'Score every unmeasured die with the acquisition function and pick the argmax as the next measurement.'
      },
      {
        name: 'Measure',
        text: 'Reveal the hidden real value at that die, append it to the observation set, and spend one unit of budget.'
      }
    ],
    cycle:
      'Repeat until the measurement budget is exhausted. Every iteration is logged, so the decision trace is auditable.'
  },

  wafer: {
    heading: 'One wafer, four states',
    panels: [
      {
        title: '1 · Biased Simulation Prior',
        caption: 'Smooth and confident everywhere. It under-predicts the wafer edge.',
        aria: 'Biased simulation prior across the wafer: smooth everywhere and under-predicting the wafer edge.'
      },
      {
        title: '2 · Sparse Measurements',
        caption: (observed: number, total: number) =>
          `${observed} of ${total} dies measured, and the sample is centre-biased.`,
        aria: 'Sparse measurements: a small number of measured dies, clustered near the wafer centre.'
      },
      {
        title: '3 · Predicted Reality',
        caption: 'Prior pulled towards measured evidence. White outlines mark measured dies.',
        aria: 'Predicted reality: the prior corrected towards the measurements, sharpening near the wafer edge.'
      },
      {
        title: '4 · Recommended Next Die',
        captionHtml:
          'Highest acquisition score: unknown <em>and</em> in disagreement with the prior.',
        aria: 'Uncertainty map with the recommended next die marked by a crosshair in the least-known region.'
      }
    ],
    legend: [
      'Measured die (observed)',
      'Unmeasured die (hidden from agent)',
      'Prior scale · violet, low → high',
      'Prediction scale · cyan, low → high',
      'Uncertainty scale · amber, certain → unknown',
      'Recommended next measurement'
    ],
    note: 'Schematic only. These fields come from a deterministic formula inside this page, written to explain the loop. They are not WM-811K wafers and not benchmark output.'
  },

  chart: {
    aria: (metric: string) =>
      `Reconstruction ${metric} against the number of measurements for each selection strategy. Lower is better.`,
    xTitle: 'Measurements used',
    caption: (metric: string, direction: string) =>
      `Reconstruction ${metric} ${direction} against measurement count. Shaded bands show ±1 standard deviation across seeds. The y-axis starts at zero. Generated from`,
    emptyLead: 'No error curve yet. This chart renders once',
    emptyTail: 'contains per-strategy',
    emptyTailEnd: 'arrays.',
    emptyNote:
      'The site deliberately ships with no placeholder numbers, so nothing here can be mistaken for a measured result.'
  },

  table: {
    caption: (metric: string, direction: string, wafers: string, seeds: string) =>
      `Final reconstruction ${metric} ${direction} after the full measurement budget, averaged over ${wafers} wafers × ${seeds} seeds. All strategies start from the same initial observations and spend the same budget.`,
    strategy: 'Strategy',
    rule: 'Selection rule',
    mean: (metric: string) => `${metric} mean`,
    std: '± std',
    improvement: 'Improvement vs NANO',
    reference: 'reference',
    // Korean puts the percentage before the verb, so the whole phrase is one
    // callable rather than a prefix plus a number.
    better: (pct: string) => `NANO better by ${pct}`,
    worse: (pct: string) => `NANO worse by ${pct}`,
    metaDataset: 'Wafer source',
    standIn: 'Stand-in wafers',
    noBudget: 'spends no budget',
    notSeparated: 'not separated from NANO',
    wins: (wins: string, n: string) => `NANO better in ${wins}/${n} episodes`,
    secondaryCaption:
      'The same run scored on every other metric. A number marked * is one where the paired interval spans zero, so the arms are not separated on that metric.',
    secondaryNote:
      'Metrics disagree here by construction. Plain MAE over every in-wafer die is led by the majority class when failures are rare, which is why the primary metric weights the two classes equally and why both are printed.',
    metaInitial: 'Initial measurements',
    metaBudget: 'Additional measurement budget',
    metaPrior: 'Simulation prior error before any correction',
    metaCommit: 'Commit',
    metaGenerated: 'Generated',
    metaSource: 'Source',
    emptyLead: 'No results table yet. Run the benchmark described on the',
    emptyLink: 'Reproduce',
    emptyTail: 'page; it writes',
    emptyTailEnd: 'and this table fills itself in.'
  },

  ablation: {
    caption: (metric: string) =>
      `Final ${metric} for the acquisition rule with terms dropped. Every arm ran the same loop, the same budget and the same initial observations; only the terms of the product differ.`,
    rule: 'Acquisition rule',
    std: '± std',
    verdict: 'Against the published rule',
    published: 'published rule',
    reference: 'reference',
    notSeparated: 'not separated',
    better: (pct: string) => `beats the published rule by ${pct}`,
    worse: (pct: string) => `loses to the published rule by ${pct}`,
    wins: (wins: string, n: string) =>
      `this rule better in ${wins}/${n} episodes`,
    note: 'A row that beats the published rule is a finding, not a footnote: the term it drops is costing accuracy on this wafer source rather than buying it.',
    emptyLead: 'No ablation in this results file. Run',
    emptyTail: ' and this table fills itself in.'
  },

  pattern: {
    caption: (metric: string) =>
      `Final ${metric} per failure pattern, worst margin first. Each row is the mean over that class's episodes; the margin is against whichever baseline did better on that class.`,
    pattern: 'Failure pattern',
    episodes: 'Episodes',
    margin: 'Margin over the better baseline',
    note: 'The margin column is a difference of means, not a separated result: the paired bootstrap on this page runs over all episodes, and a single pattern class holds too few to carry an interval. A row at or below zero is a class where choosing what to measure bought nothing.',
    empty: 'No per-pattern breakdown in this results file.'
  },

  evidence: {
    nano: 'NANO',
    nanoHint: (metric: string) => `Final ${metric} after the full budget`,
    random: 'Random baseline',
    randomHint: 'Same budget, same initial observations',
    grid: 'Grid baseline',
    gridHint: 'Spatially uniform selection',
    priorDrop: 'Prior error removed',
    separated: (arms: string) =>
      `Separated from ${arms} at 95% confidence, over the paired episodes.`,
    notSeparated: (arms: string) =>
      `Not separated from ${arms}: the paired interval spans zero, so the difference in means is not supported by this evidence.`,
    noComparison: 'No paired comparison is recorded in this results file.',
    priorDropHint: 'Biased simulation prior vs corrected estimate',
    footnote: (wafers: string, seeds: string, budget: string, metric: string) =>
      `${wafers} wafers × ${seeds} seeds · measurement budget ${budget} · ${metric} ↓ lower is better · generated from`,
    fullResults: 'Full results →',
    emptyLead: 'This repository ships no pre-baked numbers. Once the benchmark writes',
    emptyTail:
      'the headline metrics, the results table and the error curve all render from that one file.',
    emptyNote: 'Until then the honest answer is: unverified. See',
    emptyNoteLink: 'Reproduce',
    emptyNoteTail: 'for how to produce the evidence.'
  },

  asset: {
    producedBy: 'produced by',
    expectedAt: 'Expected at',
    expectedProducedBy: 'produced by',
    nothingDrawn: 'Nothing is drawn until the real figure exists.'
  }
}

type Strings = typeof en

const ko: Strings = {
  pending: '벤치마크를 실행하면 결과가 채워집니다',
  conceptual: '개념 설명용 도식',
  notMeasured: '측정되지 않음',
  lowerIsBetter: '↓ 낮을수록 좋음',
  higherIsBetter: '↑ 높을수록 좋음',

  loop: {
    steps: [
      {
        name: '관측 (Observe)',
        text: '지금까지 확보한 소수의 실측값과, 모든 다이에 대한 시뮬레이션 prior를 함께 읽는다.'
      },
      {
        name: '추정 (Estimate)',
        text: '실제에 대한 공간 모델을 적합해 예측, 불확실성, prior와 실제의 격차 세 가지 맵을 만든다.'
      },
      {
        name: '선택 (Select)',
        text: '측정되지 않은 모든 다이를 획득 함수로 채점하고, 최대값을 다음 측정 지점으로 고른다.'
      },
      {
        name: '측정 (Measure)',
        text: '해당 다이의 숨겨진 실제 값을 확인해 관측 집합에 추가하고, 예산 1단위를 소모한다.'
      }
    ],
    cycle:
      '측정 예산이 소진될 때까지 반복한다. 매 반복이 기록되므로 의사결정 경로를 추적할 수 있다.'
  },

  wafer: {
    heading: '하나의 웨이퍼, 네 가지 상태',
    panels: [
      {
        title: '1 · 편향된 시뮬레이션 prior',
        caption: '전 영역에서 매끄럽고 확신에 차 있다. 웨이퍼 edge를 과소예측한다.',
        aria: '웨이퍼 전체의 편향된 시뮬레이션 prior. 전 영역이 매끄럽고 웨이퍼 edge를 과소예측한다.'
      },
      {
        title: '2 · 희소한 측정',
        caption: (observed: number, total: number) =>
          `${total}개 다이 중 ${observed}개만 측정했고, 표본은 중앙에 편향돼 있다.`,
        aria: '희소한 측정. 소수의 측정된 다이가 웨이퍼 중앙 근처에 몰려 있다.'
      },
      {
        title: '3 · 예측된 실제',
        caption: 'prior가 실측 근거 쪽으로 당겨졌다. 흰 외곽선은 측정된 다이를 표시한다.',
        aria: '예측된 실제. prior가 측정값 쪽으로 보정되어 웨이퍼 edge에서 더 선명해졌다.'
      },
      {
        title: '4 · 추천된 다음 다이',
        captionHtml:
          '획득 점수가 가장 높은 곳: 아직 모르고 <em>동시에</em> prior와 불일치하는 지점.',
        aria: '불확실성 맵. 가장 정보가 부족한 영역에 추천된 다음 다이가 십자 표시로 나타나 있다.'
      }
    ],
    legend: [
      '측정된 다이 (관측됨)',
      '측정되지 않은 다이 (에이전트에게 비공개)',
      'prior 스케일 · 바이올렛, 낮음 → 높음',
      '예측 스케일 · 시안, 낮음 → 높음',
      '불확실성 스케일 · 앰버, 확실 → 미지',
      '추천된 다음 측정 지점'
    ],
    note: '도식일 뿐입니다. 이 필드는 루프를 설명하기 위해 이 페이지 안의 결정론적 수식으로 생성한 것입니다. WM-811K 웨이퍼도, 벤치마크 출력도 아닙니다.'
  },

  chart: {
    aria: (metric: string) =>
      `선택 전략별 측정 횟수에 따른 재구성 ${metric}. 낮을수록 좋습니다.`,
    xTitle: '사용한 측정 횟수',
    caption: (metric: string, direction: string) =>
      `측정 횟수에 따른 재구성 ${metric} ${direction}. 음영 띠는 시드 간 ±1 표준편차입니다. y축은 0에서 시작합니다. 생성 출처:`,
    emptyLead: '아직 오차 곡선이 없습니다. 이 차트는',
    emptyTail: '파일에 전략별',
    emptyTailEnd: '배열이 생기면 렌더링됩니다.',
    emptyNote:
      '이 사이트는 의도적으로 placeholder 숫자를 넣지 않습니다. 따라서 여기 있는 어떤 것도 측정된 결과로 오인될 수 없습니다.'
  },

  table: {
    caption: (metric: string, direction: string, wafers: string, seeds: string) =>
      `전체 측정 예산을 모두 소모한 뒤의 최종 재구성 ${metric} ${direction}, 웨이퍼 ${wafers}개 × 시드 ${seeds}개 평균. 모든 전략은 동일한 초기 관측에서 출발하고 동일한 예산을 씁니다.`,
    strategy: '전략',
    rule: '선택 규칙',
    mean: (metric: string) => `${metric} 평균`,
    std: '± 표준편차',
    improvement: 'NANO 대비 개선율',
    reference: '기준',
    better: (pct: string) => `NANO가 ${pct} 더 좋음`,
    worse: (pct: string) => `NANO가 ${pct} 더 나쁨`,
    metaDataset: '웨이퍼 출처',
    standIn: '대체 웨이퍼',
    noBudget: '예산을 쓰지 않음',
    notSeparated: 'NANO와 구분되지 않음',
    wins: (wins: string, n: string) => `${n}판 중 ${wins}판에서 NANO 우세`,
    secondaryCaption:
      '같은 실행을 나머지 모든 지표로 채점한 결과. *가 붙은 값은 페어링 신뢰구간이 0을 포함하는 경우로, 그 지표에서는 두 조건이 구분되지 않는다.',
    secondaryNote:
      '지표들이 서로 어긋나는 것은 구조상 당연하다. 웨이퍼 내부 전체 다이에 대한 단순 MAE는 불량이 드물 때 다수 클래스가 지배한다. 그래서 주 지표는 두 클래스에 같은 가중치를 주며, 두 값을 모두 출력한다.',
    metaInitial: '초기 측정 수',
    metaBudget: '추가 측정 예산',
    metaPrior: '보정 전 시뮬레이션 prior 오차',
    metaCommit: '커밋',
    metaGenerated: '생성 시각',
    metaSource: '출처',
    emptyLead: '아직 결과 표가 없습니다.',
    emptyLink: '재현 방법',
    emptyTail: '페이지의 벤치마크를 실행하면',
    emptyTailEnd: '파일이 생성되고 이 표가 스스로 채워집니다.'
  },

  ablation: {
    caption: (metric: string) =>
      `획득 규칙에서 항을 하나씩 뺐을 때의 최종 ${metric}. 모든 arm은 같은 루프, 같은 예산, 같은 초기 관측으로 실행되었고, 곱에 들어가는 항만 다르다.`,
    rule: '획득 규칙',
    std: '± 표준편차',
    verdict: '게시된 규칙과 비교',
    published: '게시된 규칙',
    reference: '기준',
    notSeparated: '구분되지 않음',
    better: (pct: string) => `게시된 규칙보다 ${pct} 더 좋음`,
    worse: (pct: string) => `게시된 규칙보다 ${pct} 더 나쁨`,
    wins: (wins: string, n: string) => `${n}판 중 ${wins}판에서 이 규칙이 우세`,
    note: '게시된 규칙을 이기는 행은 각주가 아니라 결과다. 그 행이 뺀 항은 이 웨이퍼 출처에서 정확도를 사는 것이 아니라 깎고 있다는 뜻이다.',
    emptyLead: '이 결과 파일에는 ablation이 없습니다.',
    emptyTail: ' 를 실행하면 이 표가 스스로 채워집니다.'
  },

  pattern: {
    caption: (metric: string) =>
      `불량 패턴별 최종 ${metric}, 마진이 가장 나쁜 순. 각 행은 그 클래스에 속한 에피소드의 평균이며, 마진은 그 클래스에서 더 좋았던 baseline을 기준으로 한다.`,
    pattern: '불량 패턴',
    episodes: '에피소드',
    margin: '더 좋은 baseline 대비 마진',
    note: '마진 열은 평균의 차이일 뿐 구분된 결과가 아니다. 이 페이지의 페어링 부트스트랩은 전체 에피소드에 대해 실행되며, 패턴 클래스 하나에 속한 에피소드는 신뢰구간을 붙이기에 너무 적다. 0 이하인 행은 어디를 측정할지 고르는 것이 아무것도 벌지 못한 클래스다.',
    empty: '이 결과 파일에는 패턴별 분해가 없습니다.'
  },

  evidence: {
    nano: 'NANO',
    nanoHint: (metric: string) => `전체 예산 소모 후 최종 ${metric}`,
    random: 'Random 베이스라인',
    randomHint: '동일한 예산, 동일한 초기 관측',
    grid: 'Grid 베이스라인',
    gridHint: '공간적으로 균일한 선택',
    priorDrop: '제거된 prior 오차',
    separated: (arms: string) => `95% 신뢰수준에서 ${arms}와 구분되었다(페어링 에피소드 기준).`,
    notSeparated: (arms: string) =>
      `${arms}와는 구분되지 않았다. 페어링 신뢰구간이 0을 포함하므로, 평균 차이는 이 근거로 뒷받침되지 않는다.`,
    noComparison: '이 결과 파일에는 페어링 비교가 기록되어 있지 않다.',
    priorDropHint: '편향된 시뮬레이션 prior 대비 보정된 추정',
    footnote: (wafers: string, seeds: string, budget: string, metric: string) =>
      `웨이퍼 ${wafers}개 × 시드 ${seeds}개 · 측정 예산 ${budget} · ${metric} ↓ 낮을수록 좋음 · 생성 출처:`,
    fullResults: '전체 결과 →',
    emptyLead: '이 저장소에는 미리 만들어 둔 숫자가 없습니다. 벤치마크가',
    emptyTail: '파일을 쓰는 순간 대표 지표와 결과 표, 오차 곡선이 모두 그 한 파일에서 렌더링됩니다.',
    emptyNote: '그때까지 정직한 답은 "검증되지 않음"입니다. 근거를 만드는 방법은',
    emptyNoteLink: '재현 방법',
    emptyNoteTail: '페이지를 보세요.'
  },

  asset: {
    producedBy: '생성 스크립트',
    expectedAt: '기대 경로',
    expectedProducedBy: '생성 스크립트',
    nothingDrawn: '실제 그림이 존재하기 전까지는 아무것도 그리지 않습니다.'
  }
}

/**
 * Locale-aware strings. Read `t.value` in script blocks and `t` in templates.
 */
export function useStrings(): ComputedRef<Strings> {
  const { localeIndex } = useData()
  return computed(() => (localeIndex.value === 'ko' ? ko : en))
}

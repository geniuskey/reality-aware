---
title: 시스템 설계
description: NANO를 구성하는 모듈들 - 관측 툴, 실제 모델, 획득 정책, 에이전트 루프, 평가 하네스 - 과 각각의 입력, 출력, 책임.
---

# 시스템 설계

::: danger 이 문서는 목표 설계를 설명하며, 실제 구현된 코드가 아니다
**이 저장소에는 아직 Python 패키지가 없다**. 아래의 모듈 이름, 경로, 시그니처는 의도된 구조다.
첫 구현이 충족해야 할 계약을 제시하기 위해, 그리고 나중에 이 페이지가 실제에 맞춰 수정되도록
— 그 반대가 되지 않도록 — 적어 둔 것이다.

코드가 들어오면, 아래 표의 모든 행은 실제로 존재하는 파일을 가리키거나 삭제되어야 한다.
이상적인 아키텍처 도식을 구현된 것처럼 제시하는 것, 그것이 바로 이 프로젝트가 반대하는
바로 그 허위 표현이다.
:::

## 데이터 흐름

```mermaid
flowchart TD
    A[WM-811K 실제] --> B[관측 툴]
    C[편향된 Prior] --> D[실제 모델]
    B --> D
    D --> E[예측과 불확실성]
    E --> F[획득 정책]
    F --> B
    A --> G[평가 하네스]
    E --> G
```

<p class="nano-note">실제는 오직 관측 툴을 통해서만 에이전트에 도달한다. 편향된 prior와 관측된 값이 실제 모델에 입력되고, 실제 모델은 예측과 불확실성을 내보낸다. 획득 정책은 그것들을 읽고 관측 툴에 다이 하나를 더 요청한다. 실제는 평가 하네스로도 직접 흐르며, 에이전트는 평가 하네스를 절대 읽지 않는다.</p>

이 그래프에서 가장 중요한 성질 하나: **실제는 오직 관측 툴을 통해서만 에이전트에 도달한다**.
실제에서 평가 하네스로 가는 직접 간선은 에이전트가 결코 보지 못하는 ground truth를 나른다.
그 경계를 가로지르는 어떤 지름길도 [벤치마크 페이지](./benchmark)의 모든 숫자를 무효로 만든다.

## 모듈

| 모듈 | 책임 | 입력 | 출력 |
| --- | --- | --- | --- |
| `nano.data` | WM-811K를 로드하고, 평가 서브셋을 필터링·인덱싱하며, 웨이퍼 내부 다이 마스크를 노출 | 데이터셋 경로, 시드 | 웨이퍼 레코드: 실제 필드, 다이 마스크, 패턴 레이블 |
| `nano.prior` | 실제 필드로부터 의도적으로 편향된 시뮬레이션 prior를 생성 | 실제 필드, 편향 파라미터 | 웨이퍼 내부 모든 다이에 정의된 prior 필드 |
| `nano.tools.observe` | 실제로 통하는 유일한 채널. 다이 하나의 값을 드러내고 예산 한 단위를 소모 | 다이 인덱스 | 측정값, 갱신된 관측 상태 |
| `nano.model` | prior와 관측을 조화시키고 예측, 불확실성, reality-gap 맵을 생성 | prior, 관측 마스크, 관측값 | `prediction`, `uncertainty`, `reality_gap` |
| `nano.policy` | 측정되지 않은 다이에 점수를 매기고 다음 측정 지점을 선택 | 모델 출력, 관측 마스크 | `next_index`, `next_score`, 항별 분해 |
| `nano.agent` | 예산이 소진될 때까지 관측 → 추정 → 선택 → 측정 루프를 실행 | 웨이퍼 레코드, 예산, 시드 | 결정 추적, 단계별 지표 |
| `nano.baselines` | 동일한 정책 인터페이스 뒤에 놓인 Random과 Grid 선택 규칙 | 모델 출력, 관측 마스크 | `next_index` |
| `nano.evaluate` | 숨겨진 ground truth에 대비해 예측을 채점하고 웨이퍼와 시드에 걸쳐 집계 | 예측, 실제 필드 | `results/benchmark_summary.json` |

## 중요한 경계들

**하나의 툴, 하나의 예산.** 모든 측정은 `nano.tools.observe`를 거친다. 예산 회계는 호출자가
아니라 툴 내부에 있으므로, 어떤 전략도 몰래 한 번 더 들여다볼 수 없다.

**베이스라인은 정책 인터페이스를 공유한다.** Random과 Grid는 NANO 정책과 동일한 시그니처를
구현하며 동일한 루프로 구동된다. 각 조건 사이에서 바뀌는 것은 선택 규칙뿐이며 —
이것이 비교를 의미 있게 만드는 요소다.

**평가는 모든 것의 하류에 있다.** `nano.evaluate`는 전체 실제 필드를 만지는 유일한 모듈이며,
에이전트에게 아무것도 돌려주지 않는다.

**결과 파일은 하나.** `nano.evaluate`가 `results/benchmark_summary.json`을 쓰고, 사이트가 그것을
읽는다. 이 사이트의 차트, 표, 대표 숫자는 모두 그 파일에서 파생되므로, 한 곳에서만 숫자가
갱신되고 다른 곳은 낡은 채로 남는 일이 생길 수 없다. 스키마는
[벤치마크 페이지](./benchmark)에 문서화되어 있다.

## 문서 사이트

이 사이트는 의도적으로 단조롭다. 백엔드도, 런타임 데이터 페칭도, 애널리틱스도 없는 정적
VitePress 빌드다.

| 구성 요소 | 경로 | 역할 |
| --- | --- | --- |
| 설정 | `docs/.vitepress/config.mts` | 내비게이션, 사이드바, SEO, Mermaid, 프로젝트 및 사용자 Pages를 위한 base-path 처리 |
| 결과 로더 | `docs/.vitepress/data/benchmark.data.mts` | 빌드 시점에 `results/benchmark_summary.json`을 읽고 검증 |
| 에셋 로더 | `docs/.vitepress/data/assets.data.mts` | `docs/public/results/`를 나열하여 누락된 그림이 대기 상태로 격하되도록 처리 |
| 컴포넌트 | `docs/.vitepress/theme/components/` | `AgentLoop`, `WaferComparison`, `BenchmarkChart`, `BenchmarkTable`, `EvidenceStrip`, `MetricCard`, `ResultAsset` |
| 에셋 동기화 | `scripts/sync-doc-assets.mjs` | 게시된 그림을 `results/`에서 `docs/public/results/`로 복사 |
| 배포 | `.github/workflows/deploy-docs.yml` | `main`에 푸시될 때 빌드하고 GitHub Pages에 게시 |

컴포넌트는 빌드 시점에 렌더링되므로, 페이지는 내용을 정적 HTML로 담고 있다. JavaScript를
비활성화해도 본문, 표, 웨이퍼 도식, 결과 그림은 모두 그대로 읽힌다. 클라이언트 런타임이 필요한
것은 Mermaid 다이어그램과 검색창뿐이다.

다음: [직접 실행해 보기 →](./reproducibility)

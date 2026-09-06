---
title: 재현
description: 클론, 설치, 문서 빌드, 그리고 - 에이전트가 구현되면 - 데모와 벤치마크와 테스트 실행까지. 아티팩트 위치와 시드 제어를 포함한다.
---

# 재현

이 저장소에는 두 가지가 들어 있고, 둘은 서로 다른 단계에 있다. 이 페이지는 어떤 명령이 실제로
실행되었고 어떤 명령이 그렇지 않은지를 있는 그대로 밝힌다.

| 대상 | 상태 |
| --- | --- |
| 문서 사이트 | **검증됨.** 아래 명령들은 이 저장소에서 실제로 실행되었다. |
| 에이전트, 벤치마크, 테스트 | **검증됨.** 아래 명령들은 이 저장소에서 생성된 대체 웨이퍼로 실제 실행되었다. |
| WM-811K에 대한 벤치마크 실행 | **여기에 게시되지 않음.** 데이터셋은 커밋되어 있지 않다. 내려받으면 같은 명령이 결과 파일을 만든다. |

## 문서 사이트

Node.js 22.17.1 / npm 11.5.1에서 검증됨. 워크플로는 Node.js 20에서 동일한 명령을 실행한다.

```bash
git clone https://github.com/geniuskey/reality-aware.git
cd reality-aware
npm ci
npm run docs:dev      # 핫 리로드가 되는 로컬 서버
npm run docs:build    # docs/.vitepress/dist 로의 정적 빌드
npm run docs:preview  # 빌드 결과물 서빙
```

`npm ci`는 커밋된 `package-lock.json`을 필요로 하며, 배포 워크플로도 같은 파일로부터 설치한다.

### 다른 Pages base 경로로 빌드하기

base 경로는 CI에서 `GITHUB_REPOSITORY`로부터 유도되므로, 프로젝트 Pages(`/<repo>/`)와 사용자 또는
조직 Pages(`/`) 모두 설정을 고치지 않고 동작한다. 필요하면 로컬에서 다음과 같이 덮어쓰면 됩니다:

```bash
DOCS_BASE=/ npm run docs:build           # 사용자 또는 조직 Pages
DOCS_BASE=/my-fork/ npm run docs:build   # 저장소 이름이 다른 fork
```

### 그림을 사이트에 게시하기

실험 출력의 표준 위치는 `results/`다. 사이트는 `docs/public/results/`에서 그림을 읽는다. 둘 사이의
복사는 손으로 하지 말고 동기화 스크립트로 하세요:

```bash
npm run sync:assets
```

이 스크립트는 알려진 그림 이름들을 `results/`에서 `docs/public/results/`로 복사하고, 없는 것은 건너뛰며,
무엇을 했는지 보고한다. 그림이 없는 것은 오류가 아니다. 페이지는 깨진 이미지 대신
*벤치마크를 실행하면 결과가 채워집니다* 라는 상태를 명시적으로 표시하고, 빌드는 그대로 성공한다.

## 에이전트와 벤치마크

Python 3.11에서 검증되었다.

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

pytest                                        # 테스트 스위트, 데이터셋 불필요
python -m nano.demo --wafer wm811k-645735 --seed 0    # 게시된 에피소드, 데모 그림을 기록
python -m nano.benchmark --seeds 0 1 2 3 4 --ablation # 전체 비교, 결과 파일을 기록
```

`pip install -e .`만 실행하면 numpy만 설치되며, 루프와 벤치마크를 돌리기에는 그것으로 충분하다.
`figures` 추가 항목은 matplotlib과 pillow를, `data`는 `LSWMD.pkl`을 읽기 위한 pandas를, `dev`는
그 둘에 pytest까지 더한다.

### 데이터셋 없이 실행하기

모든 명령은 `--synthetic`을 받는다. WM-811K 대신 `nano.data.synthetic_wafers`가 생성한 웨이퍼 맵을
사용한다.

```bash
python -m nano.benchmark --synthetic --wafers 12 --seeds 0 1 2 3 4
```

아무것도 내려받지 않고 파이프라인 전체 — 루프, 베이스라인, 채점, 그림 — 를 실행한다. 이것은
데이터셋이 **아니다**. 실행은 경고를 출력하고, 결과 파일은 `dataset.name`을 `synthetic-wafers`로
기록하며 주석을 남기고, [벤치마크 페이지](./benchmark)의 표는 웨이퍼 출처를 함께 출력한다. 따라서
대체 웨이퍼의 숫자를 데이터셋 숫자로 읽을 수 없다. 대체 웨이퍼 실행 결과는 이 저장소에 커밋하지
않는다.

### 데이터셋 구하기

WM-811K는 여기에 커밋되어 있지 않다 — 배포 링크와 이용 조건은 [데이터셋](./data)을 참고하세요. 예상되는
로컬 디렉터리 구조는 다음과 같다:

```text
data/
└── raw/
    └── LSWMD.pkl        # 내려받아 두는 파일, 절대 커밋하지 않음
```

여기서 유도한 서브셋 인덱스는 *버전 관리된다*. 따라서 원본 데이터를 재배포하지 않고도 평가 세트를 정확히
재구성할 수 있다.

### 아티팩트 위치

| 아티팩트 | 경로 |
| --- | --- |
| 결과 요약, 사이트의 단일 진실 공급원 | `results/benchmark_summary.json` |
| 오차 곡선, 웨이퍼 비교, 불확실성 맵 | `results/*.svg`, `results/*.webp` |
| 데모 기록 | `results/demo.gif` |
| 게시된 그림의 사이트 사본 | `docs/public/results/` |
| 버전 관리되는 평가 인덱스 | `data/subsets/wm811k_eval.json` |

벤치마크를 다시 돌리지 않고 그림만 하나씩 다시 생성할 수도 있다.

```bash
python scripts/plot_wafer_comparison.py --wafer wm811k-645735 --seed 0
python scripts/plot_uncertainty.py --wafer wm811k-645735 --seed 0
python scripts/plot_paired_improvement.py          # 결과 파일을 읽는다
python scripts/plot_calibration.py                 # 결과 파일을 읽는다
python scripts/record_demo.py --wafer wm811k-645735 --seed 0
```

`--wafer`는 웨이퍼 id 또는 위치 인덱스를 받는다. 믿을 수 있는 쪽은 id다. 인덱스는 평가 세트가 바뀌는
순간 다른 웨이퍼를 가리키게 되며, 게시된 그림이 id로 웨이퍼를 지목하는 이유가 그것이다. 게시된 그림이
어느 웨이퍼인지는 이 페이지에서 정하는 것이 아니라, 그것을 고른 규칙과 함께
`results/benchmark_summary.json`의 `figures`에 기록된다.

```bash
python -m nano.benchmark --seeds 0 1 2 3 4                              # 두 그림 웨이퍼를 모두 고른다
python -m nano.benchmark --seeds 0 1 2 3 4 --figure-wafer wm811k-19423   # 첫 번째만 바꾼다
```

벤치마크는 선택이 Random·Grid 대비 가장 적게 벌어들인 웨이퍼도 항상 함께 그리며, `--figure-wafer`로
그 웨이퍼를 바꿀 수는 없다.

그림은 결과 파일을 따라간다. `--out`을 다른 곳으로 지정하면 그 실행의 그림도 그 옆에 기록되므로,
확인용 실행이 `results/`에 있는 다른 실행의 숫자 옆에 자기 그림을 남기는 일은 일어나지 않는다.

### 시드 제어하기

시드는 명시적인 인자이며, 결코 암묵적인 전역 상태가 아니다:

```bash
python -m nano.benchmark --seeds 0 1 2 3 4     # 게시된 구성
python -m nano.benchmark --seeds 7             # 빠른 확인을 위한 단일 실행
```

결과 파일을 만들어낸 시드 집합은 그 파일 안에 기록되며, 사이트는 모든 표와 차트 아래에 그것을 표시한다.
`seeds`가 그 파일을 만들어낸 실행과 일치하지 않는 요약 파일은 보고할 만한 버그다.

## 직접 만들지 않은 결과를 검증하기

1. `results/benchmark_summary.json`에서 `dataset.name`, `experiment.seeds`,
   `experiment.initial_measurements`, `experiment.measurement_budget`를 읽는다. `dataset.note`가
   있다면 그 실행은 WM-811K를 쓰지 않은 것이다.
2. `dataset.subset_file`이 가리키는 서브셋 인덱스에 대해, 정확히 그 값들로 벤치마크를 다시
   실행한다.
3. `strategies.*.final.mean`을 자신의 실행 결과와 비교한다. 그 숫자를 만들어 낸 파라미터는
   `experiment.prior_bias`와 `experiment.model`에 기록되어 있다.

숫자가 재현되지 않는다면 결과 파일이 틀린 것이고, 이 사이트도 함께 틀린 것이다. 이 사이트는 그 파일을
읽는 일밖에 하지 않기 때문이다.

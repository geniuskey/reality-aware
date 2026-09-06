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
| 에이전트, 데이터셋, 벤치마크 | **아직 구현되지 않음.** 아래 명령들은 의도된 인터페이스일 뿐, 오늘 실행할 수 있는 것이 아니다. |

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

::: danger 아직 실행할 수 없음
이 저장소에는 Python 패키지도, 엔트리 포인트도, 테스트 스위트도 커밋되어 있지 않다. 이 절의 모든 내용은
구현이 노출할 것으로 예상되는 인터페이스다. 이것들을 동작하는 명령으로 취급하지 말고, 이 명령들의 초기
버전이 만들어낸 숫자는 `results/benchmark_summary.json`에 들어가기 전까지 게시된 결과로 취급하지
마세요.
:::

의도된 인터페이스:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

python -m nano.demo --wafer 0 --seed 0        # 단일 에피소드, 데모 그림을 기록
python -m nano.benchmark --seeds 0 1 2 3 4    # 전체 비교, 결과 파일을 기록
pytest                                        # 테스트 스위트
```

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

### 시드 제어하기

시드는 명시적인 인자이며, 결코 암묵적인 전역 상태가 아니다:

```bash
python -m nano.benchmark --seeds 0 1 2 3 4     # 게시된 구성
python -m nano.benchmark --seeds 7             # 빠른 확인을 위한 단일 실행
```

결과 파일을 만들어낸 시드 집합은 그 파일 안에 기록되며, 사이트는 모든 표와 차트 아래에 그것을 표시한다.
`seeds`가 그 파일을 만들어낸 실행과 일치하지 않는 요약 파일은 보고할 만한 버그다.

## 직접 만들지 않은 결과를 검증하기

1. `results/benchmark_summary.json`에서 `experiment.seeds`, `experiment.initial_measurements`,
   `experiment.measurement_budget`를 읽는다.
2. 정확히 그 값들로 벤치마크를 다시 실행한다.
3. `strategies.*.final.mean`을 자신의 실행 결과와 비교한다.

숫자가 재현되지 않는다면 결과 파일이 틀린 것이고, 이 사이트도 함께 틀린 것이다. 이 사이트는 그 파일을
읽는 일밖에 하지 않기 때문이다.

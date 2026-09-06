---
title: 벤치마크
description: 동일한 측정 예산, 동일한 초기 관측, 동일한 웨이퍼 조건에서 NANO를 Random 및 Grid 선택과 비교하고, 숨겨진 ground truth 기준으로 채점한다.
---

# 벤치마크

이 페이지의 모든 그림과 모든 숫자는 단 하나의 파일 `results/benchmark_summary.json` 에서 렌더링된다.
여기에 손으로 마크다운에 입력한 값은 없으므로, 표와 차트와 홈 페이지가 서로 어긋날 수 없다.

::: warning 아직 게시된 실행 결과가 없음
하네스는 구현되어 있지만(`python -m nano.benchmark`), WM-811K에 대한 실행 결과는 여기에 게시되지
않았다. 따라서 `results/benchmark_summary.json`은 존재하지 않으며, 아래의 모든 결과 블록은 그
사실을 정직하게 알린다. 파일이 나타나는 순간 자동으로 채워진다.

결과 파일은 데이터셋에 대한 실행일 때만 커밋한다. 생성된 대체 웨이퍼(`--synthetic`)로 실행해도
로컬에서 같은 파일이 만들어지고 그렇게 표시되지만 — 표에 웨이퍼 출처가 함께 출력된다 — 대체
웨이퍼의 숫자는 데이터셋 결과로 게시하지 않는다. [재현하기](./reproducibility)를 참고하세요.
:::

## 무엇을 비교하는가

세 arm 모두 동일한 웨이퍼, 동일한 시드, 동일한 초기 관측 마스크, 동일한 추가 측정 예산을 받는다.
**유일한** 차이는 각자 다음에 어떤 다이를 고르는가이다.

| 전략 | 선택 규칙 |
| --- | --- |
| **Random** | 측정되지 않은 다이를 균일하게 샘플링 |
| **Grid** | 공간적으로 균일한 격자의 다음 지점에 가장 가까운, 측정되지 않은 다이를 선택 |
| **NANO** | 획득 점수가 가장 높은, 측정되지 않은 다이를 선택 |

각 arm이 실행한 규칙은 결과 파일에 기록되며, 세 arm 모두 `nano/agent.py`의 동일한 루프가 동일한
`select(estimate, observed_mask, coords, rng)` 시그니처로 구동한다. Grid는 격자 크기를 예산에
맞추고 고정된 순서로 소비하며, Random은 에피소드의 시드 생성기로 측정되지 않은 다이에서 균일하게
뽑는다.

여기서 공정한 비교는 의도의 문제가 아니라 프로토콜의 문제다. NANO가 다른 초기 마스크에서 출발하거나
더 큰 예산을 썼다면, 어떤 개선이 나오든 해석할 수 없다.

## 핵심 결과

<BenchmarkTable />

### 상대 개선율의 정의

```text
relative improvement = (baseline error − NANO error) / baseline error × 100
```

양수는 동일한 비용에서 NANO가 베이스라인보다 웨이퍼를 더 정확하게 재구성했다는 뜻이다.
음수는 그러지 못했다는 뜻이며, 표는 그 사실도 똑같은 비중으로 출력한다.

## 측정 수 대 오차

<BenchmarkChart />

이 곡선에서 흥미로운 부분은 끝점만이 아니라 그 모양이다. 단지 운이 좋았을 뿐인 선택 규칙은 Random과
같은 속도로 수렴하며 마지막에 가서야 갈라진다. 정보량이 큰 위치를 진짜로 고르고 있는 규칙이라면
예산이 아직 남아 있을 때 일찍 갈라져야 한다.

## Prior 대 보정된 재구성

<ResultAsset
  file="wafer_comparison.webp"
  title="Prior → 재구성 → ground truth"
  caption="웨이퍼 하나를 편향된 prior, NANO 재구성, 숨겨진 ground truth로 동일한 스케일에서 보여준다."
  producedBy="scripts/plot_wafer_comparison" />

## 예산 소진 전후의 불확실성

<ResultAsset
  file="uncertainty_before_after.webp"
  title="불확실성 맵, 예산 시작 시점 대 종료 시점"
  caption="시작 시점에 에이전트가 자신이 보지 못한다고 판단한 곳, 그리고 예산을 다 쓴 뒤에도 알 수 없이 남은 곳."
  producedBy="scripts/plot_uncertainty" />

불확실성과 예측은 의도적으로 서로 다른 색상 스케일로 그린다. 둘은 서로 다른 질문에 답하므로 같은
범례로 읽어서는 안 된다.

## 웨이퍼별 개선

<ResultAsset
  file="paired_improvement.svg"
  title="쌍별 개선 분포"
  caption="NANO와 각 베이스라인의 웨이퍼별 차이. 평균으로 뭉개지 않고 이긴 경우와 진 경우를 모두 드러낸다."
  producedBy="scripts/plot_paired_improvement" />

평균 개선치는 대부분의 웨이퍼를 조금 좋게 만들고 소수의 웨이퍼를 크게 나쁘게 만드는 규칙을 감출 수
있다. 쌍별 분포는 그것을 드러낼 그림이며, 막대 하나가 아니라 이 그림을 여기에 둔 이유다.

## NANO가 실패하는 지점

::: warning 아직 답하지 않은 부분
이 절은 벤치마크가 실제로 실행되기 전까지 비어 있다. 여기에는 기대치가 아니라 결과 파일로부터
다음이 기록될 것이다.

- NANO가 Random이나 Grid를 이기지 못하는 불량 패턴,
- 우위가 사라지는 예산 구간,
- 편향된 prior가 우연히 실제와 가까워서 보정할 것이 없었던 웨이퍼,
- 평균을 무의미하게 만들 만큼 큰 시드 간 분산.

실행 결과에는 이 절에 필요한 것이 이미 기록된다. `strategies.*.by_pattern`에는 arm별·패턴별 평균과
분산이, `episodes`에는 개별 `(wafer, seed)` 결과가 모두 담기고, 위의 페어링 그림도 그로부터
그려진다. NANO가 어떤 패턴 클래스에서 진다면, 그 사실은 각주가 아니라 여기에 전부 적혀야 한다.
:::

## 결과 파일 스키마

`results/benchmark_summary.json` 이 단일 진실 공급원이다. 사이트는 빌드 시 이 파일을 검증하며,
형식이 잘못된 파일에 대해서는 그럴듯한 무언가를 렌더링하는 대신 요란하게 실패한다.

```json
{
  "schema_version": 1,
  "generated_at": "2026-01-01T00:00:00Z",
  "git_commit": "<short sha of the run>",
  "dataset": {
    "name": "WM-811K",
    "subset_file": "<path to the versioned subset index>",
    "n_wafers": 0
  },
  "experiment": {
    "seeds": [0, 1, 2],
    "initial_measurements": 0,
    "measurement_budget": 0,
    "grid_shape": [0, 0]
  },
  "metric": {
    "name": "MAE",
    "direction": "lower_is_better",
    "unit": "failure probability"
  },
  "prior": { "initial_error": { "mean": 0.0, "std": 0.0 } },
  "strategies": {
    "nano": {
      "label": "NANO",
      "description": "highest acquisition score",
      "final": { "mean": 0.0, "std": 0.0 },
      "curve": [{ "measurements": 0, "mean": 0.0, "std": 0.0 }]
    },
    "random": {
      "label": "Random",
      "description": "uniform over unmeasured dies",
      "final": { "mean": 0.0, "std": 0.0 },
      "curve": []
    },
    "grid": {
      "label": "Grid",
      "description": "spatially uniform lattice",
      "final": { "mean": 0.0, "std": 0.0 },
      "curve": []
    }
  },
  "assets": { "error_curve": "results/error_curve.svg" }
}
```

| 필드 | 필수 | 비고 |
| --- | --- | --- |
| `schema_version` | 예 | 없으면 빌드 실패 |
| `strategies` | 예 | `nano`, `random`, `grid` 키는 전용 색상과 선 스타일을 갖는다 |
| `strategies.*.final` | 예 | 표와 홈 페이지 지표 카드를 구동한다 |
| `strategies.*.curve` | 차트에 필요 | 생략하면 차트는 대기 상태로 표시되며, 표는 그대로 렌더링된다 |
| `metric.direction` | 권장 | 모든 지표 옆에 출력되는 `↓` / `↑` 표시를 결정한다 |
| `prior.initial_error` | 권장 | 보정이 prior 오차를 얼마나 제거했는지 사이트가 보고할 수 있게 한다 |
| `dataset.name` | 권장 | 표 아래에 웨이퍼 출처로 출력된다 |
| `dataset.note` | WM-811K가 아닐 때 | 대체 웨이퍼 실행은 여기에 주석을 남기고, 표는 그것을 눈에 띄게 출력한다 |

하네스가 쓰는 파일에는 최소 요건 이상이 담긴다. `experiment.acquisition_rule`,
`experiment.prior_bias`, `experiment.model`은 그 숫자를 만들어 낸 규칙과 파라미터를 기록하고,
`strategies.*.by_pattern`은 불량 패턴별로 결과를 나누며, `episodes`는 모든 `(wafer, seed)` 쌍을
나열해 에피소드별 승패를 게시된 파일에서 그대로 복원할 수 있게 한다.

[ResultAsset](./architecture)이 참조하는 그림은 `docs/public/results/` 에서 읽는다. 동기화
스크립트가 공식 `results/` 디렉터리에서 그곳으로 복사한다 —
[재현하기](./reproducibility)를 참고하세요.

다음: [단일 실행 따라가 보기 →](./demo)

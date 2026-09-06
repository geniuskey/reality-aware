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

### 모든 개선율에 구간이 붙는 이유

평균의 차이는 그 자체로 결과가 아니다. 각 arm은 NANO와 **에피소드 단위로 페어링된다** — 같은
웨이퍼, 같은 시드, 같은 prior, 같은 초기 마스크이므로 에피소드 내부의 차이는 선택 규칙만을
분리한다 — 그리고 그 페어링 차이를 부트스트랩(2000회 재표집, 시드는 결과 파일에 기록)해 95%
구간을 만든다.

그 구간이 0을 포함하면, 평균이 아무리 좋아 보여도 표는 백분율 대신 **구분되지 않음**을 출력한다.
승패 수도 함께 출력한다. "평균적으로 더 낫다"와 "대부분의 웨이퍼에서 더 낫다"는 서로 다른
주장이고, 벤치마크가 그 둘을 뒤섞이게 두어서는 안 되기 때문이다.

### 주 지표가 단순 MAE가 아닌 이유

대부분의 다이는 정상이다. 다이의 12%가 불량인 웨이퍼에서, 어디서나 *"불량 없음"*이라고만 답하고
측정을 **하나도 읽지 않는** 예측기는 훌륭한 MAE를 받는다 — 여기 있는 어떤 전략보다도 좋다. 이는
전략의 성질이 아니라, 클래스 불균형이 지식인 것처럼 채점되는 것이다.

그래서 주 지표는 **balanced MAE**다. 불량 다이에서의 오차와 정상 다이에서의 오차의 평균이다.
아무것도 모르는 예측기는 불량률과 무관하게 정확히 `0.5`를 받는다. 기준은 "우연이 우연처럼 보여야
한다"이지, 특정 arm이 이겨야 한다가 아니다.

단순 MAE도 여전히 계산되고, 결과 파일에 기록되며, 이 페이지의 두 번째 표에 출력된다. 두 지표가
어긋나면 둘 다 보여 준다. `python -m nano.benchmark --metric mae`로 선택을 바꿀 수 있다. 에피소드
단위 수치 자체는 달라지지 않고, 어느 쪽이 앞에 서는지만 달라진다.

### 예산을 쓰지 않는 두 행

표에는 *예산을 쓰지 않음*으로 표시된 예측기 둘이 함께 나온다.

| 참조 | 무엇을 답하는가 | 왜 거기 있는가 |
| --- | --- | --- |
| **무보정 prior** | 측정을 전혀 적용하지 않은 시뮬레이션 prior | 이 작업 전체가 넘어야 할 바닥 |
| **상수** | 이진 타깃에서 어디서나 `0.0` — 아무것도 읽지 않음 | 단순 MAE가 빠지는 함정을 숨기지 않고 드러낸 것 |

아무것도 읽지 않는 예측기를 이기지 못하는 선택 규칙은 자신이 쓴 장비 시간을 벌지 못한 것이다.
그 점검을 건너뛰지 않게 만드는 가장 값싼 방법이, 두 예측기를 전략과 같은 표에 넣는 것이다.

## 측정 수 대 오차

<BenchmarkChart />

이 곡선에서 흥미로운 부분은 끝점만이 아니라 그 모양이다. 단지 운이 좋았을 뿐인 선택 규칙은 Random과
같은 속도로 수렴하며 마지막에 가서야 갈라진다. 정보량이 큰 위치를 진짜로 고르고 있는 규칙이라면
예산이 아직 남아 있을 때 일찍 갈라져야 한다.

## 획득 규칙의 각 항은 제 몫을 하는가

선택 규칙은 세 항의 곱이고, 세 항의 곱은 그 자체로 하나의 주장이다 — 각 항이 결정을 더 낫게
바꾼다는 주장. 확인하는 방법은 항을 빼고 다시 돌려 보는 것뿐이다. `python -m nano.benchmark
--ablation`은 축약된 규칙들을 추가 arm으로 실행한다. 같은 루프, 같은 예산, 같은 초기 관측이고,
항만 다르다.

<AblationTable />

이 표는 이 사이트의 나머지 부분을 가장 난처하게 만들 수 있는 표이며, 바로 그래서 노트북이 아니라
여기에 있다. 축약된 규칙이 게시된 규칙을 이긴다면, 그 행이 뺀 항은 정확도를 사는 것이 아니라
깎고 있다는 뜻이다. 게시된 규칙은 WM-811K에 대한 실행이 다른 말을 하기 전까지
[접근 방식 페이지](./approach)가 문서화한 그대로 유지하며, 그 사이에는 `--terms`로 어떤 부분집합도
실행할 수 있다.

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

## 불확실성 맵은 무언가를 실제로 순위 매기는가

NANO는 불확실성으로 위치의 순위를 매긴다. 따라서 그 맵은 추정이 어디서 얼마나 틀렸는지에 따라
다이를 정렬해야 한다. 그렇지 않다면 획득 규칙은 잡음을 정렬하고 있는 것이다. 실행은 이것을 직접
확인한다. 에이전트가 한 번도 측정하지 않은 다이들을 보고된 불확실성으로 구간을 나눈 뒤, 실제로
발생한 오차를 보고한다.

<ResultAsset
  file="calibration.svg"
  title="보고된 불확실성 대 실제 발생한 오차"
  caption="예산 소진 시점의 미측정 다이를 동일 개수 구간으로 나눈 결과와, 함께 출력된 Spearman 순위 상관."
  producedBy="scripts/plot_calibration" />

측정된 다이는 의도적으로 제외한다. 그 다이들은 구조상 불확실성도 0이고 오차도 0이므로, 포함하면
툴 자신의 장부에서 상관관계를 만들어 내는 셈이 된다.

::: warning 이것은 순위 점검이지 캘리브레이션 주장이 아니다
곡선이 올라간다는 것은 불확실성이 다이를 유용하게 *정렬한다*는 뜻이다. 그 값들이 확률이라는 뜻은
아니며, 여기서 명시된 구간이 명시된 비율로 참값을 덮는지는 아무것도 평가하지 않는다 — 애초에
구간을 명시하지 않기 때문이다. 결과 파일이 그 필드를 `rank_correlation`으로 이름 붙인 이유가
그것이다. [정직한 범위](./limitations)를 참고하세요.
:::

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
| `metric.key` | 권장 | `metrics` 중 어느 항목이 표·곡선·비교를 이끄는지 |
| `metrics` | 두 번째 표에 필요 | 실행이 채점한 모든 지표와 그 이름·범위 |
| `strategies.*.metrics` | 두 번째 표에 필요 | 각 arm의 지표별 값 |
| `references` | 권장 | 측정을 쓰지 않는 행: `prior`와 `constant` |
| `comparisons` | 구간 표시에 필요 | `comparisons[metric][arm]` — 페어링 평균, 95% 구간, 승수, `separates` |

하네스가 쓰는 파일에는 최소 요건 이상이 담긴다. `experiment.acquisition_rule`,
`experiment.prior_bias`, `experiment.model`은 그 숫자를 만들어 낸 규칙과 파라미터를 기록하고,
`strategies.*.by_pattern`은 불량 패턴별로 결과를 나누며, `episodes`는 모든 `(wafer, seed)` 쌍을
나열해 에피소드별 승패를 게시된 파일에서 그대로 복원할 수 있게 한다.

[ResultAsset](./architecture)이 참조하는 그림은 `docs/public/results/` 에서 읽는다. 동기화
스크립트가 공식 `results/` 디렉터리에서 그곳으로 복사한다 —
[재현하기](./reproducibility)를 참고하세요.

다음: [단일 실행 따라가 보기 →](./demo)

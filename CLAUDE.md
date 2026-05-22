# kt_epimodel — Claude 작업 가이드

## 프로젝트 개요

수도권 metapop 인플루엔자 모델 + sick-leave 정책 ICER 분석.
정책 중심 1편 논문 목표.

## 의존성

- **kt_data** (editable, ../kt_data): 정제된 데이터 + 표준 로더
  - `from kt_data.data.load_population import load_population_15groups`
  - `from kt_data.data.load_mobility import load_mobility`
  - `from kt_data.data.load_contact import load_contact_matrices, get_contact_matrix`
  - `from kt_data.data.load_calendar import classify_date, get_daytype_for_range`
  - `from kt_data.data.load_ili import load_ili_seasons`

## 모델 명세 (확정)

### 구조
- 공간: 수도권 1,155 행정동 (load_population은 1,148 매칭)
- 연령: NIMS 15군 (5세 단위, 0-4 분리, 70+ 통합)
- 시간: 일 단위 (Δt = 1 day)
- 질병: 인플루엔자 (정상 시기 정책 가이드)
- Compartment: S, E, I, J (isolated), R

### 연령 그룹 (15군)

```python
AGE_LABELS_15 = [
    '0-4', '5-9', '10-14', '15-19', '20-24', '25-29',
    '30-34', '35-39', '40-44', '45-49', '50-54', '55-59',
    '60-64', '65-69', '70+'
]

AGE_STARTS_15 = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70]
```

### 방정식

```
dS^a_i/dt = -λ^a_i(t) · S^a_i
dE^a_i/dt = +λ^a_i(t) · S^a_i - σ · E^a_i
dI^a_i/dt = +σ · E^a_i - (γ + δ · p_iso(a)) · I^a_i
dJ^a_i/dt = +δ · p_iso(a) · I^a_i - γ · J^a_i
dR^a_i/dt = +γ · (I^a_i + J^a_i)
```

Force of infection:

```
λ^a_i(t) = β · φ_a · Σ_b C^ab(t) · Σ_j π^b_ji(t) · I^b_j / N_eff_j
```

파라미터 (잠정):
- σ ≈ 1/2 day⁻¹ (잠복기 2일)
- γ ≈ 1/4 day⁻¹ (감염기 4일)
- δ ≈ 1/1 day⁻¹ (격리까지 1일)
- β, φ_a: calibration 대상

### Contact matrix C(t)

```
C(t) = λ_home(t)·C_home + λ_work(t)·C_work + λ_school(t)·C_school + λ_other(t)·C_other
```

NIMS 측정값 4개 (15×15) 그대로 사용 (mobility로 합성 X).

λ(t) 잠정값 (NIMS notebook 04/06 확인 시 갱신):
- `weekday_school`: {home:1.0, work:1.0, school:1.0, other:1.0}
- `vacation_weekday`: {home:1.1, work:1.0, school:0.2, other:1.1}
- `weekend`: {home:1.3, work:0.2, school:0.0, other:1.2}
- `holiday`: weekend와 동일

### Contact Matrix 컨벤션

행렬 모양 기준:
- Y축(rows) = contact (응답된 상대방)
- X축(cols) = participant (응답자)
- 좌하단 (0, 0) = (contact 0-4, participant 0-4)
- 우상단 (14, 14) = (contact 70+, participant 70+)

NIMS npz 파일은 [participant, contact] 형식이므로 transpose 적용 필요.
`load_contact_matrices()` 가 이미 transpose 적용 (기본값).

### 연령별 mobility 활용 전략

| 연령 | KT mobility | 처리 |
|---|---|---|
| 0-4 (어린이집) | 사용 안 함 | 정적 (자기 행정동) |
| 5-9 (초등) | 사용 안 함 | 정적 (자기 행정동) |
| 10-14, 15-19 | 부분 (학원/other) | 학교 정적 + 학원 KT |
| 20-69 | 적극 사용 | KT mobility 사용 |
| 70+ | 사용 안 함 | 정적 (자기 행정동) |

근거:
- 0-9세 KT 검출률 0.15 (휴대폰 미보유)
- 20-69세 검출률 0.85-0.95
- 70+ 검출률 1.50 (자녀 집 거주 추정)

KT mobility 보정: 사용하는 연령은 × 1/0.9 배율.

### KT age_10 → NIMS 15군 매핑

KT 7군: [10, 20, 30, 40, 50, 60, 70+]
NIMS 15군: 위 `AGE_LABELS_15`

매핑 (인구비례 분할):
- KT [10-19] → NIMS [10-14, 15-19]
- KT [20-29] → NIMS [20-24, 25-29]
- KT [30-39] → NIMS [30-34, 35-39]
- KT [40-49] → NIMS [40-44, 45-49]
- KT [50-59] → NIMS [50-54, 55-59]
- KT [60-69] → NIMS [60-64, 65-69]
- KT [70+] → NIMS [70+]

0-9 (NIMS 0-4, 5-9)는 KT mobility 안 씀 → 행렬에서 정적 처리.

### Mobility 텐서 형태

`load_mobility()` 반환:
- `pi`: shape (n_admdong, n_admdong, 7 ages, 24 hours)
- 단위: 일평균 이동량 (해당 시간대)
- age 인덱스: 0=10-19, 1=20-29, ..., 5=60-69, 6=70+ (0-9 제외)

우리 모델에서 사용 시:
- 시간 평균 (일 단위 모델이므로) 또는 시간대별 그대로
- 15군으로 인구비례 분할 (필요 시)

## 데이터 위치

기본: `~/Documents/python/NIMS/kt_data/data/` (자동 감지)
환경변수: `KT_DATA_ROOT` 설정 가능

## 코드 스타일

- **Polars** 우선 (Pandas 회피)
- **NumPy** 행렬 연산
- **Type hint** 사용
- 한글 라벨 회피 (그래프, 변수명 모두 영어)
- 함수 단위 분리, 클래스는 상태 보존 필요 시만
- 테스트: pytest

## 미해결 사항 (작업 시 주의)

상세 내용은 [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md). 핵심 caveat:

1. **γ_report 는 ILI 분모(외래환자) 효과를 모두 흡수**
   - ILI = 외래환자 1,000명당 의사환자 수 (인구 분모 아님)
   - γ_report 절대값 해석 불가, β 와 partial confounding
   - 후속: HIRA 외래환자 데이터로 분리 (Stage 5)

2. **연령별 ILI ↔ NIMS 15군 매핑 단순화**
   - ILI 7 그룹 → NIMS 15군 (`kt_data.ILI_GROUP_TO_NIMS`)
   - 0세는 NIMS 0-4 전체에 매핑 (1/5만 차지 — 정확 분리 불가)
   - 1-6세도 NIMS 5-9 의 2년만 (오차 존재)

3. **φ_a 는 net transmissibility** (susceptibility + infectivity 통합)
   - σ_a (감수성) 과 ι_a (전염성) 분리 불가 (ILI 1D 시계열만으로)
   - 후속: 가구 secondary attack rate 또는 문헌값 ι 고정

4. λ_home, λ_work, λ_other 시간 가변 정확값
   - NIMS notebook 04, 06 결과 필요. 잠정값 사용 중

5. NIMS contact matrix 절대값 과소 추정
   - β 로 흡수 (calibration 자동 보정)

6. ILI 시도별 데이터
   - 현재 전국 평균만 사용. 시도별 협조 요청 중

7. 70+ 검출률 1.5 원인
   - 자녀 집 거주 가설. 정적 모델 결정에 영향 없음

8. School mobility 단순화
   - `M_school = identity` (통학 무시). 학원은 M_other 로 처리

9. 시즌성 cosine 단순 가정
   - amp fit, peak_day 130 고정 (1월 중순). 환경/사회 복합 요인은 amp 가 흡수

## 절대 하지 말 것

- mobility로 contact 합성 (NIMS 동료의 04/06 방법론 적용 X)
- 14군 컨벤션 사용 (15군 확정)
- pandas long DataFrame 변환 (numpy 텐서 직접)
- 0-9, 70+에 KT mobility 적용 (정적 모델 확정)

## 자주 헷갈리는 점

- 14군 vs 15군: **15군** (NIMS `empirical_matrices_15.npz` 기준)
- Contact matrix 방향: [contact, participant] (좌하단 = 0-4×0-4)
- KT age 인덱스: 0이 10-19 (0-9 제외됨)
- 시간 단위: 일 (시간대별 데이터는 일 평균으로 처리)

## 다음 단계 우선순위

Stage 2 모델 코어:
1. `parameters.py` — 파라미터 클래스
2. `compartments.py` — 상태 변수
3. `foi.py` — Force of infection
4. `dynamics.py` — ODE 우변
5. `solver.py` — scipy.integrate.solve_ivp
6. `runner.py` — 단일 시즌 실행

자세한 설계: [docs/STAGE2_DESIGN.md](docs/STAGE2_DESIGN.md)
논문 방향: [docs/PAPER_OUTLINE.md](docs/PAPER_OUTLINE.md)
로드맵: [docs/ROADMAP.md](docs/ROADMAP.md)

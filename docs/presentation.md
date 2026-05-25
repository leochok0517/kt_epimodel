---
marp: true
theme: default
paginate: true
header: 'KT mobility 기반 전염병 모델링 — 데이터부터 calibration까지'
footer: 'NIMS · 2026-05'
size: 16:9
math: mathjax
style: |
  section { font-size: 24px; }
  h1 { color: #1f3a5f; }
  h2 { color: #1f3a5f; }
  table { font-size: 18px; }
  .small { font-size: 18px; }
---

# KT mobility 기반 전염병 모델링을 위한 데이터 정제

## 수도권 metapop 인플루엔자 모델 input 구축

<br>

조형우 · NIMS 수리과학연구소

2026-05

---

## 연구 배경 — Why

**최종 목표**: 수도권 metapop **인플루엔자 모델** + **sick-leave ICER**

- 행정동 단위 (1,148개) × 연령 15군 SEIR 시뮬레이션
- 결석·병가 정책의 비용-효과 정량화 (ICER)

— *데이터 정제 단계*

| 단계 | 상태 |
|---|---|
| 데이터 수집 + 정제 + 표준 로더 | ✓ 본 발표 |
| Metapop 모델 구축 | 다음 프로젝트 (`kt_epimodel`) |
| ILI calibration / 정책 시뮬레이션 | 후속 |



---

## 사용 데이터 — 5종

| 데이터 | 출처 | 기간 | 모델 용도 |
|---|---|---|---|
| **KT LivePOP** | KT 통신 | 2018-01 ~ 2023-12 | 거주 인구 검증 |
| **KT Movement** | KT 통신 (OD) | 2018-01 ~ 2023-12 | mobility π |
| **주민등록** | 행정안전부 | 2023-01 | 공식 인구 N |
| **NIMS Contact** | NIMS 설문  | 2023-12, 2024-02 | contact matrix |
| **ILI** | 질병관리청 표본감시 | 2018 ~ 2023 (5절기) | calibration target |



---

## KT Mobility

**입력**: 250m 통신 셀 → 행정동 매핑 (178,119 셀 → 1,155 행정동)

**처리** (72 개월 일괄):
- `purpose` 코드 제거 — 분류 정확도 낮고 7+(기타) 58%
- 평일 / 주말 분리 (한국 공휴일은 주말로 처리)




![w:780](../outputs/integrated_eda/02_mobility.png)

---

## 데이터 검증 필요성

**질문**. KT mobility가 실제 사람들의 이동을 잡고 있는가?

**검증 방법** — 행정안전부 주민등록과 야간(03–05 시) LivePOP 비교

<br>

> **핵심 가정**: 새벽엔 모두 거주지에 있다.  
> ⇒ 야간 LivePOP ≈ 그 행정동의 KT-검출 거주자  
> ⇒ **KT 검출률 = (야간 LivePOP) / (주민등록 인구)**  

<br>

행정동 × 연령군 별로 검출률을 산출 → 분포 확인.

---

## KT 검출률

![w:780](../outputs/age_validation_2023_01/09_detection_rate_boxplot.png)

<div class="small">

- **10–39세**: 0.92–0.94 ✓ — KT mobility 신뢰 가능
- **0–9세**: **0.15 ❌** — KT가 실제의 약 15%만 잡음
- **70+**: 약 0.55 — 보정 필요

</div>

원인 추정: 휴대전화 미보유, 어린이 단말기 KT 외 점유율, KT 보정 한계.

---

## 연령별 mobility 활용 전략

| 연령군 | KT mobility | 모델 처리 | 근거 |
|---|---|---|---|
| **0–9세** | ❌ | **정적** (자기 행정동 고정) | 검출률 0.15 |
| **10–19세** | 학원만 | 학교 *정적* + 학원 KT | 학교 안 mixing은 위치 무관 |
| **20–69세** | ✓ 적극 활용 | KT π 사용 | 검출률 ~0.9 |
| **70+** | ❌ | **정적** | 휴대전화 보급률·활동 반경 |

<br>

**핵심 통찰**: 학교 안 mixing은 학교 *위치*와 무관 — 같은 학교 내부 contact는 행정동 이동 불필요.  
∴ 0–9세 mobility 부정확해도 모델 동학에 미치는 영향 미미.

---

## NIMS Contact Matrix — 개요

- **출처**: NIMS 호흡기 감염병 밀접접촉 설문 
- **시점**: 2023-12 (학기) + 2024-02 (방학)
- **응답자**: 1,987 명 × 평균 67 건 ≈ 약 **13만 건** 접촉
- **4 setting**: `home` (가족) · `work` (직장) · `school` (학교친구) · `other` (기타)

---
![w:760](../outputs/integrated_eda/03_contact_matrices.png)


---

## ILI 활용 방법

**정상 시기** (2018-19, 2022-23)
- Base 시뮬레이션 calibration target
- $\beta$ (전염력) · 초기 감염자 · 계절성 fitting

**코로나 시기** (2020-21, 2021-22)
- 정책 효과 검증용 **자연 실험**
- 사회적 거리두기 → ILI 90% 감소 재현 가능?

**미해결 (Open)**:
- NIMS contact matrix 절대값 과소 추정 → $\beta$ 로 흡수 vs 외부 scaling
- 시도별 raw data 확보 시 지역 calibration 가능

---

## 최종 모델 input 흐름

| Input | 차원 | 출처 | 처리 |
|---|---|---|---|
| 인구 $N$ | 1,148 × 15 | 주민등록 | 5세 → 15군, 70+ 통합 |
| Mobility $\pi$ | 1,154 × 1,154 × 7 × 24 | KT 생활이동 데이터 | 평일/주말, 가중평균 |
| Contact $C$ | 15 × 15 × 4 | NIMS 설문 | $C(t)$ 시간 가변 |

| ILI | 5 시즌 × 52 주 | 질병청 | calibration |

<br>

→ 다음 프로젝트 [`kt_epimodel`](https://github.com/leochok0517) 에서 metapop 모델 input으로 import.

---

## 결석 · 병가 효과의 명시적 표현

**정책 변수**: $p_{\text{iso}}^{a}$ — 연령군 $a$의 격리 비율

**시나리오 예시**

| 시나리오 | 대상 | $p_{\text{iso}}$ 변화 |
|---|---|---|
| 어린이집 결석 권장 | 0–4 | 0.3 → 0.8 |
| 병가 보조금 | 20–69 | 0.2 → 0.6 |
| 학교 폐쇄 | 5–19 | → 0.8 |

**Spillover 자동 처리**:  
가족 격리 → 직장 → 학교로 이어지는 전파 차단 효과가 contact matrix를 통해 자연스럽게 흘러감.

---

# Part 2

## Metapop 모델 구축 — `kt_epimodel`

<br>

데이터 정제 완료 → SEIRV metapop 모델 구축 + calibration

조형우 · NIMS 수리과학연구소

---

## 모델 구조 — SEIRV + 4채널 FOI

**Compartment** (격리 J 제거, 백신 V 추가):

$$S \xrightarrow{\lambda} E \xrightarrow{\sigma} I \xrightarrow{\gamma} R, \qquad S \xrightarrow{v(t)} V \xrightarrow{(1-V\!E)\lambda} E$$

**상태 공간**: 5 compartment × 15 연령 × 1,154 행정동

**고정 파라미터** (문헌)

| 파라미터 | 값 | 의미 |
|---|---|---|
| $\sigma$ | $1/2$ /day | 잠복기 2일 |
| $\gamma$ | $1/4$ /day | 감염기 4일 |
| $V\!E$ | $0.5$ | 백신 효과 |

**시간 의존 백신**: ISO 42주(10월 중) peak Gaussian × 연령별 coverage (0–9세 75%, 70+ 82%).

---

## FOI 4채널 분해

총 FOI: $\lambda_{i,a}(t) = \lambda^{h} + \lambda^{w} + \lambda^{s} + \lambda^{o}$

| 채널 | mobility | 적용 그룹 | p-factor |
|---|---|---|---|
| Home | 자기 행정동 | 모든 연령 | spillover $(1+\kappa\cdot\varphi)$ |
| Work | KT 9–17시 | 근로자 (20–69) | $\rho\cdot(1-p_{\text{work}})$ |
| School | identity (단순화) | 학생 (0–19) | $(1-p_{\text{school}})$ |
| Other | KT 17–22시 | 모든 연령 | — |

**Other 채널 p-factor 없음**: sick leave는 출근/등교만 변경 — 저녁 외출은 못 막음 (보수적 가정).

---

## 가구 spillover — Home 채널

$$
\lambda^{h}_{i,a} = \beta_h\,\phi_a \sum_b C^{h}[a,b]\,\frac{I_{i,b}(1 + \kappa_b\,\varphi^{\text{spill}}_{i,b})}{N_{i,b}}
$$

**핵심**: 학교/직장에 안 가는 사람들이 가구 내 노출 증가.

**$\kappa$ (가구 노출 factor)**

| 연령 | $\kappa$ | 비고 |
|---|---|---|
| 0–19 | 0.42 | 학생 |
| 20–69 | 0.60 | 근로자 |
| 70+ | 0.0 | baseline과 동일 |

**$\varphi^{\text{spill}}$**: $p_{\text{school}},\,p_{\text{work}}$가 줄면 자동 증가 → 정책 시나리오의 **비의도적 효과**(가구 노출 ↑) 자동 모델링.

---

## 시즌성 모델 — Gaussian peak

$$
\beta_{ch}(t) = \beta_{ch} \cdot \bigl[\text{base} + \text{amp}\cdot \exp\!\bigl(-(t - t_{\text{peak}})^2 / 2\sigma^2\bigr)\bigr]
$$

**왜 Gaussian인가**

- Cosine: 시즌 외에도 강한 transmission 잔존
- Gaussian: 시즌 외 → $\text{base}$ (작은 값), 시즌 내 → 좁고 강한 peak
- 한국 인플루엔자의 sharp seasonality 자연 표현

**Fit 대상**: $\text{base},\,\text{amp},\,\sigma,\,t_{\text{peak}}$ 모두 데이터로 결정.

**중요 통찰**: $t_{\text{peak}}$ (transmission peak) ≠ ILI peak (보고 peak) — 잠복 → 발병 → 의사 방문 lag로 1–2주 앞섬.

---

## ODE 정식

$$
\begin{aligned}
dS/dt &= -\lambda\,S - v(t)\,S \\
dV/dt &= +v(t)\,S - (1-V\!E)\,\lambda\,V \\
dE/dt &= +\lambda\,S + (1-V\!E)\,\lambda\,V - \sigma\,E \\
dI/dt &= +\sigma\,E - \gamma\,I \\
dR/dt &= +\gamma\,I
\end{aligned}
$$

scipy `solve_ivp` (RK45 adaptive step). Calibration은 행정동 합산 단순 모델로 진행 → 정책 시뮬은 1,154 행정동 full metapop.

---

## Calibration 설정

**Target**: 2019–2020 시즌 (monomodal, 가장 깨끗)

**ILI 연령별 데이터** (7 그룹): 0세 / 1–6 / 7–12 / 13–18 / 19–49 / 50–64 / 65+

**NIMS 15군 ↔ ILI 7군**: 인구비례 분배 매핑 (`ILI_GROUP_TO_NIMS`)

**364 데이터 포인트** (7 그룹 × 52 주) → 23개 파라미터 fit

**Loss**: Poisson NLL + first-peak-only weight (둘째 봉 = B형 무시)

**Optimizer**: Nelder–Mead + L-BFGS-B 양쪽 비교 (`calibration_04_*` 노트북)

---

## Fit 파라미터 (23-dim)

| 그룹 | 파라미터 | 설명 |
|---|---|---|
| Transmission | $\beta_h,\,\beta_w,\,\beta_s,\,\beta_o$ | 4채널 transmission rate |
| Age structure | $\varphi_a$ (14개, $\varphi_{25\text{-}29}=1$ ref) | 연령별 net transmissibility |
| Reporting | $\gamma_{\text{report}}$ | ILI scaling factor |
| Seasonality | $\text{amp},\,\text{base},\,\sigma,\,t_{\text{peak}}$ | Gaussian 4개 |

**핵심 한계**: $\varphi_a$는 명목상 susceptibility지만 실제로는 **net transmissibility** (susceptibility × infectivity 결합) — 1D ILI 데이터로 separately identifiable 불가능.

---

## Calibration 시행착오 — False peak 문제

**증상**: 시즌 시작 직후 (week 4–5) 거대한 false peak — 진짜 peak (week 17) 못 잡고 spurious outbreak 발생.

**관측 패턴**

- 7 그룹 모두 시즌 초입에 비정상 spike
- 시즌 중반 epidemic 신호 없음
- NLL은 줄어드는데 곡선은 망가짐 → 무언가 근본적 잘못

**가능 원인 후보**: seed 크기, seasonality 모양, contact 채널 weight, bounds, loss 함수, **incidence 계산** …

---

## 시행착오 — 단계적 진단

| 시도 | 가설 | 결과 |
|---|---|---|
| 1. amp lower bound 강제 | 시즌성 약함 | 부분 효과 |
| 2. 인구비례 매핑 (5세 분배) | NIMS–ILI 매핑 부정확 | OK, 본질 X |
| 3. Seed 자동 계산 (ILI 기반) | seed 너무 작음 | 오히려 악화 |
| 4. Gaussian seasonality | Cosine 한계 | OK, 본질 X |
| 5. $t_{\text{peak}}$ fit 대상 | Transmission lag | OK, 본질 X |
| 6. Bounds tightening | Corner solution | 더 심한 corner |
| 7. `min_rate` 조정 | Loss landscape | 부분 효과 |
| 8. **Incidence 계산 검증** | $\Delta R$ vs $-\Delta S$ | ★ **버그 발견** |

---

## ★ 진짜 원인 — Incidence 계산 버그

**진단 결과** (시즌 전체 flux 분해)

| 항목 | 값 |
|---|---|
| $\Delta S_{\text{total}}$ (S 감소 전량) | 5,424,588 |
| $\Delta V$ (S→V vaccination flux) | 5,424,588 |
| **진짜 $S\!\to\! E$ infection** | $\approx 1$ |
| $-\Delta S$ / 진짜 incidence 비율 | **5,424,588 ×** |

**버그 위치** (`loss.py`, by-age 경로):

```python
# 잘못된 코드 — S 감소 전량을 신규 감염으로 해석
S_age = result.states[:, IDX_S, :, :].sum(axis=-1)
daily_inc_by_age = -np.diff(S_age, axis=0)
```

**올바른 코드**: $\Delta(E + I + R)$ — vaccination flux 자동 제외.

---

## 버그의 의미

ILI prediction의 **99.99%가 vaccination flux의 가짜 신호**였음.

→ Optimizer는 가짜 신호를 ILI baseline에 맞추려 함
→ 진짜 epidemic 만들 필요 없음 ($\beta \to 0$, corner solution)
→ R₀ = 0.0001 (시즌 내내) 로 fit됨

**SEIRV 모델 일반의 함정**

- 단순 SIR에서 "$-\Delta S =$ 신규 감염자" 직관이 통용
- 백신 (V compartment) 추가 시 $\Delta S =$ 신규 감염 $+$ 백신 접종
- aggregated loss는 `daily_new_infection()` helper로 처리하고 있었음
- **by_age 경로에서만 helper 호출이 누락**된 게 결정타

---

## 버그 수정 후 결과 — 2019–2020 L-BFGS-B fit

![w:780](../outputs/calibration/2019-2020_by_age_LBFGS_fit.png)

**NLL**: $5168 \to -7815$ (Poisson NLL이 깊은 음수로) · 6,144 평가 · 60분

False peak 사라지고 7 그룹 모두 자연스러운 epidemic curve.

---

## Fit 결과 정량 평가

| Age | Observed peak (per 1000) | Predicted | Timing |
|---|---|---|---|
| 0세 | 24 @ w19 | ~25 | ✓ |
| 1–6 | 65 @ w21 | ~65 | ✓ |
| 7–12 | 130 @ w16 | ~65 | timing OK, magnitude ½ |
| 13–18 | 95 @ w18 | ~63 | timing OK |
| 19–49 | 62 @ w19 | ~62 | ✓ |
| 50–64 | 30 @ w18 | ~70 | over-predict |
| 65+ | 13 @ w18 | ~62 | over-predict |

완벽한 fit은 아니지만 **모양과 timing 모두 정확** → 의미 있는 fit.
50–64 / 65+ over-prediction은 향후 추가 점검 (백신 효과 분리, 연령별 reporting 등).

---

## 핵심 fit 파라미터 (L-BFGS-B, 실측값)

| Parameter | Value | Note |
|---|---|---|
| $\beta_h,\,\beta_w,\,\beta_s,\,\beta_o$ | 1.016, 0.947, 0.677, 0.999 | 4채널 비슷 (single channel dominance 없음) |
| seasonality amp | **0.159** | 좁고 강한 peak |
| seasonality base | 0.142 | 시즌 외 transmission 작음 |
| seasonality $\sigma$ | **15.1 days** | 시즌 폭 ≈ 2주 |
| seasonality $t_{\text{peak}}$ | **150 days**$^\dagger$ | upper bound 박힘 (=12월 말∼1월 초) |
| $\gamma_{\text{report}}$ | 0.858 | ILI scaling |
| $\varphi_a$ range | 0.58 – 1.17 | $\varphi_5=1.00$ (anchor) |

R₀ at peak > 1 (epidemic 가능) ✓ · R₀ at season start < 1 (false peak 회피) ✓

<br>

<span class="small">$^\dagger$ $t_{\text{peak}}$는 (80, 150) bound의 upper에 박힘 — bound 확장 시 더 늦어질 가능성.</span>

---

## 모델의 한계 (논문 명시 필요)

**1. ILI 분모 = 외래환자 (인구 X)**
- $\gamma_{\text{report}}$ 에 흡수 → 절대값 해석 어려움, 상대값 (정책 비교) 유효
- → Stage 5에서 HIRA 외래환자 데이터 협조 요청 예정

**2. $\varphi_a$ identifiability**
- Net transmissibility (susceptibility × infectivity 결합)
- 1D ILI로 분리 불가능

**3. ILI baseline의 정체**
- 시즌 시작 baseline 3–5는 background (RSV, 코로나, 일반감기)
- 진짜 인플루엔자 ≈ 0 가정 / Model seed $I_0 = 384$ (전 연령)

**4. 미해결 데이터 협조**
- 시도별/연령별 ILI raw data (질병청)
- $\lambda(t)$ daytype factor 정확값 (NIMS notebook 04, 06)
- 외래환자 비율 (HIRA, Stage 5용)

---

## 다음 단계 — Stage 4 정책 시나리오

**시나리오** (calibrated baseline 기준)

| 시나리오 | $p_{\text{school}}$ | $p_{\text{work}}$ | 대상 |
|---|---|---|---|
| Baseline | 1.0 | 1.0 | — |
| School closure | 0.05 | 1.0 | 학생 |
| Sick leave enhanced | 1.0 | 0.4 | 근로자 |
| Comprehensive | 0.05 | 0.4 | 둘 다 |

**비교 지표**: Attack rate (전체 + 연령별) · Peak height / timing · Hospitalization (HIRA) · ICER (cost / QALY)

**Trade-off 정량화**: 학교 휴교 시 가구 spillover로 근로자 노출 ↑

---

## Spillover trade-off — 정성적 예시

이전 모델링 단계 결과:

| 시나리오 | 학생 FOI | 근로자 FOI |
|---|---|---|
| Baseline | $3.14\times 10^{-4}$ | $2.20\times 10^{-4}$ |
| School closure | $1.42\times 10^{-4}$ (↓55%) | **$2.37\times 10^{-4}$ (↑8%)** |
| Sick leave | $3.25\times 10^{-4}$ (↑3%) | $2.10\times 10^{-4}$ (↓5%) |
| Comprehensive | $1.53\times 10^{-4}$ | $2.28\times 10^{-4}$ |

→ 학교 휴교는 학생 FOI 55% 감소시키나 가구 spillover로 근로자 FOI 8% 증가
→ ICER 계산 시 이런 trade-off 자동 반영.

---

## 요약

**완료**

- 데이터 정제: KT mobility 검출률 평가, 연령별 활용 전략
- 모델 구축: SEIRV + 4채널 FOI + spillover + Gaussian seasonality
- Calibration: 2019–2020 7그룹 동시 fit 성공 (L-BFGS-B)

**핵심 교훈**

- ODE 시뮬레이션 + compartment 추가 시 **incidence 정의 재점검 필수**
- SVEIR에서 $-\Delta S \neq$ 신규 감염 (vax flux 포함)
- $\Delta(E+I+R)$ 사용해야 정확

**진행 중**

- 다른 시즌 holdout validation
- 정책 시나리오 비교 (Stage 4)
- HIRA 데이터 협조 요청 → ICER 계산 (Stage 5)

---

## 코드 + 데이터 가용성

**GitHub repositories**

- 데이터: [`kt_data`](https://github.com/leochok0517/kt_data)
- 모델: [`kt_epimodel`](https://github.com/leochok0517/kt_epimodel)

**테스트 커버리지**: 300+ tests passing

**재현성**

- `uv` 패키지 관리
- Calibration JSON 결과 저장 (`outputs/calibration/*.json`)
- 노트북별 분리: `calibration_04_1_nelder_mead`, `04_2_lbfgsb`, `04_3_compare`

<br>

질문 환영합니다.



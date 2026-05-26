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

조현우 · NIMS 수리과학연구소

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
| 모델 구축 | ✓ 본 발표  |
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

---

## NIMS Contact Matrix — 개요

- **출처**: NIMS 호흡기 감염병 밀접접촉 설문 
- **시점**: 2023-12 (학기) + 2024-02 (방학)
- **응답자**: 1,987 명 × 평균 67 건 ≈ 약 **13만 건** 접촉
- **4 setting**: `home` (가족) · `work` (직장) · `school` (학교친구) · `other` (기타)


---

## ILI 활용 방법

**정상 시기** (2018-19, 2022-23)
- Base 시뮬레이션 calibration target
- $\beta$ (전염력) · 초기 감염자 · 계절성 fitting

**코로나 시기** (2020-21, 2021-22)
- 정책 효과 검증용 **자연 실험**
- 사회적 거리두기 → ILI 90% 감소 재현 가능?



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

## 모델 구축

<br>

데이터 정제 완료 → SEIRV metapop 모델 구축 + calibration

조현우 · NIMS 수리과학연구소

---

## 모델 구조 — SEIRV + 4채널 FOI

**Compartment** :

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

**Gaussian 사용 이유**

- Cosine: 시즌 외에도 강한 transmission 잔존
- Gaussian: 시즌 외 → $\text{base}$ (작은 값), 시즌 내 → 좁고 강한 peak
- 한국 인플루엔자의 sharp seasonality 자연 표현

**Fit 대상**: $\text{base},\,\text{amp},\,\sigma,\,t_{\text{peak}}$ 모두 데이터로 결정.

**중요 가정**: $t_{\text{peak}}$ (transmission peak) ≠ ILI peak (보고 peak) — 잠복 → 발병 → 의사 방문 lag로 1–2주 앞섬.

---

## ODE

$$
\begin{aligned}
dS/dt &= -\lambda\,S - v(t)\,S \\
dV/dt &= +v(t)\,S - (1-V\!E)\,\lambda\,V \\
dE/dt &= +\lambda\,S + (1-V\!E)\,\lambda\,V - \sigma\,E \\
dI/dt &= +\sigma\,E - \gamma\,I \\
dR/dt &= +\gamma\,I
\end{aligned}
$$

Calibration은 행정동 합산 단순 모델로 진행

---

## Calibration 설정

**Target**: 2019–2020 시즌 (monomodal, 가장 깨끗)

**ILI 연령별 데이터** (7 그룹): 0세 / 1–6 / 7–12 / 13–18 / 19–49 / 50–64 / 65+

**NIMS 15군 ↔ ILI 7군**: 인구비례 분배 매핑 (`ILI_GROUP_TO_NIMS`)

**364 데이터 포인트** (7 그룹 × 52 주) → 23개 파라미터 fit

**Loss**: Poisson NLL + first-peak-only weight (둘째 봉 = B형 무시)

**Optimizer**: Nelder–Mead + L-BFGS-B 양쪽 비교 

---

## Fit 파라미터 (23-dim)

| 그룹 | 파라미터 | 설명 |
|---|---|---|
| Transmission | $\beta_h,\,\beta_w,\,\beta_s,\,\beta_o$ | 4채널 transmission rate |
| Age structure | $\phi_a$ (14개, $\phi_{25\text{-}29}=1$ ref) | 연령별 net transmissibility |
| Seasonality | $\text{amp},\,\text{base},\,\sigma,\,t_{\text{peak}}$ | Gaussian 4개 |

**핵심 한계**: $\phi_a$는 명목상 susceptibility지만 실제로는 **net transmissibility** (susceptibility × infectivity 결합) — 1D ILI 데이터로 separately identifiable 불가능.

---

## Calibration 시행착오 — False peak 문제

**증상**: 시즌 시작 직후 (week 4–5) 거대한 false peak — 진짜 peak (week 17) 못 잡고 spurious outbreak 발생.

**관측 패턴**

- 7 그룹 모두 시즌 초입에 비정상 spike
- 시즌 중반 epidemic 신호 없음
- NLL은 줄어드는데 곡선은 망가짐 → 무언가 근본적 잘못

**가능 원인 후보**: seed 크기, seasonality 모양, contact 채널 weight, bounds, loss 함수, **incidence 계산** …


---

## Incidence 계산 버그

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

## 버그 수정 전 결과 — 2019–2020 L-BFGS-B fit

![w:780](../outputs/calibration/2019-2020_by_age_LBFGS_fit_old.png)


---

## 버그 수정 후 결과 — 2019–2020 L-BFGS-B fit

![w:780](../outputs/calibration/2019-2020_by_age_LBFGS_fit.png)

**NLL**: $5168 \to -8568$ 

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
| $\phi_a$ range | 0.58 – 1.17 | $\phi_5=1.00$ (anchor) |

R₀ at peak > 1 (epidemic 가능)  · R₀ at season start < 1 (false peak 회피) 

<br>

<span class="small">$^\dagger$ $t_{\text{peak}}$는 (80, 150) bound의 upper에 박힘 — bound 확장 시 더 늦어질 가능성.</span>

---

## $\phi_a$ · channel $\beta$ 분포 — L-BFGS-B fit

![w:880](../outputs/calibration/2019-2020_by_age_LBFGS_phi_beta.png)

<div class="small">

- **$\phi_a$ (좌)**: 0–4 / 25–29 / 45–49 / 55–59 / 70+ 가 reference (≈1.0) 근처, 나머지 연령군은 0.58–0.79 — 인접 그룹 간 큰 진동 패턴
- **$\beta_{ch}$ (우)**: home · work · other ≈ 1.0 으로 비슷, school 만 0.68 로 낮음 — single-channel dominance 없음

</div>

---

## Nelder–Mead refinement

**L-BFGS-B 의 한계**


- $\phi_a$ 인접 연령군 진동
- 50–64 / 65+ over-prediction

**Nelder–Mead 특성**

| 측면 | L-BFGS-B | Nelder–Mead |
|---|---|---|
| Gradient | 유한차분 (23-dim) | derivative-free, simplex |
| Bound 거동 | active set, corner 갇힘 | simplex 자유 탐색 |
| Local minima | 강 | 약 (탈출 가능) |

**전략**: L-BFGS-B 결과를 warm-start 로 NM chained refinement.

---

## NM fit 결과 — 2019–2020 (warm-start from L-BFGS-B)

![w:780](../outputs/calibration/2019-2020_by_age_NM_fit.png)

<div class="small">

NLL: $-8568 \to -9236$ (warm-start 에서 668 추가 감소)

- L-BFGS-B 대비 NLL **$-1421$ 추가 개선** ($-7815 \to -9236$)
- 50–64 / 65+ over-prediction 완화 — 관측 magnitude 근접
- 7–12, 13–18 peak magnitude 부족은 여전

</div>

---

## NM vs L-BFGS-B — fit overlay

![w:880](../outputs/calibration/2019-2020_compare_fit.png)

<div class="small">

- **NM (red)** vs **L-BFGS-B (blue dashed)** vs observed (black)
- 50–64 / 65+ : NM 이 L-BFGS-B over-prediction 을 정확히 보정
- 0 / 1–6 / 19–49 : 두 방법 비슷한 peak magnitude
- 7–12 : 두 방법 모두 관측 peak (~130) 의 절반 수준 — common limitation

</div>

---

## NM vs L-BFGS-B — $\phi_a$ 비교

![w:880](../outputs/calibration/2019-2020_compare_phi.png)

<div class="small">

- **NM**: 0–19 세 강하게 ↑ (1.3–1.7), 55+ 거의 0 으로 ↓ — "어린이/청소년 transmission 주도, 노인 거의 비전염" 가설로 수렴
- **L-BFGS-B**: 모든 연령군 0.58–1.17 사이 — 평탄한 패턴
- **해석**: NM 은 채널별 분배 ($\beta_s \approx 0$) 와 $\phi_a$ 모두 극단 — 노인 over-prediction 의 원인을 "$\phi_{\text{노인}} \to 0$" 로 해소
- **identifiability 경고**: $\beta_s$ 와 $\phi_{\text{학생}}$ 가 trade-off — 학교 channel 을 끈 채 $\phi$ 가 학생 transmission 흡수

</div>

---

## NM vs L-BFGS-B — β · seasonality 비교

![w:880](../outputs/calibration/2019-2020_compare_params.png)

| Parameter | L-BFGS-B | Nelder–Mead | 해석 |
|---|---|---|---|
| $\beta_h$ | 1.016 | **1.651** | NM 가구 채널 강화 |
| $\beta_w$ | 0.947 | 0.459 | NM 직장 채널 약화 |
| $\beta_s$ | 0.677 | **0.001** | NM 학교 채널 사실상 없음 |
| $\beta_o$ | 0.999 | 0.990 | 동일 |
| amp | 0.159 | 0.132 | 유사 |
| base | 0.142 | 0.140 | 동일 |
| $\sigma$ (day) | 15.1 | **22.6** | NM peak 폭 ↑ |
| $t_{\text{peak}}$ | 150$^\dagger$ | 150$^\dagger$ | 두 방법 모두 upper bound 박힘 |
| $\gamma_{\text{report}}$ | 0.858 | 1.000$^\dagger$ | NM 도 bound 근접 |

<span class="small">$^\dagger$ bound 박힘 — 후속 bound 확장 + multi-start 필요.</span>


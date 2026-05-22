# Open Questions & Modeling Caveats

Calibration·해석에 영향을 주는 미해결 사항. Stage 5 (ICER) 진입 전 우선순위로 협조 요청 또는 점검 필요.

---

## 1. γ_report — ILI 분모 정의

### 현재 상태
ILI 데이터는 **외래환자 1,000명당 의사환자 수** (분모: 외래환자, 분자: ILI 의심 환자).
모델 incidence (S→E flux) 는 인구 단위 신규감염.
변환: `ILI ≈ γ_report · incidence / population · 1000`.

### 이로 인해 γ_report 가 다음 요소를 **모두 흡수**
- 진짜 보고율 (감염자 중 외래 방문 비율)
- 외래환자/인구 비율 (의료 이용률)
- 시즌별 변동

### 한계
- γ_report 절대값 해석 불가
- 연령별 외래 이용률 차이 (예: 0-6세 자주, 19-49세 적게) 무시
- β 와 partial confounding (같은 NLL: β↑·γ↓ 또는 β↓·γ↑)

### 후속 해결 (Stage 5)
HIRA 외래환자 데이터 협조 요청:
- 연령별 외래 방문 수
- 시기별 (주별/월별)
- γ_report = 진짜 보고율 분리

---

## 2. 연령별 ILI 매핑 (5세 단위 vs 7 그룹)

### 현재 상태
- ILI 데이터: 7 그룹 (0, 1-6, 7-12, 13-18, 19-49, 50-64, 65+)
- 모델: NIMS 15군 (5세 단위)

### 매핑 (`kt_data.ILI_GROUP_TO_NIMS`)
- 0세 → NIMS 0-4 (단순 매핑, 1/5 정도 차지)
- 1-6세 → NIMS 0-4 + 5-9
- 7-12세 → NIMS 5-9 + 10-14
- 13-18세 → NIMS 10-14 + 15-19
- 19-49세 → NIMS 20-24 ~ 45-49 (6 그룹)
- 50-64세 → NIMS 50-54 ~ 60-64 (3 그룹)
- 65+ → NIMS 65-69 + 70+

### 한계
- 0세는 NIMS 0-4 안의 1/5만 차지 (정확 분리 불가)
- 1-6세도 5-9의 2년 (5세, 6세) 만 포함 — 5-9 전체 분배 시 오차

### 후속 해결
- NIMS contact matrix 를 0세, 1-6세, 7-12세 단위로 재구축 (어려움)
- 또는 ILI 데이터 5세 단위 raw 협조 요청 (질병청)

---

## 3. Identifiability — Susceptibility vs Infectivity

### 현재 상태
`φ_a` (15개) 는 명목상 susceptibility 이지만 실제로는 **net relative transmissibility**:
- σ_a (감수성)
- ι_a (전염성)
- 두 효과의 곱이 fit 됨

### 한계
- ILI 1D 시계열로는 σ_a 와 ι_a 분리 불가
- φ_a 해석은 "종합 연령별 epidemic 기여도"

### 후속 해결
- 가구 secondary attack rate 데이터로 ι_a 외부 추정
- 또는 어린이 ι 문헌값 (1.2-1.5) 으로 고정

---

## 4. λ(t) 시간 가변 정확값

### 현재 상태
`TimeVaryingParameters` 의 daytype 별 λ_*(t) 가중치는 잠정값:
- `weekday_school`: home/work/school/other 모두 1.0
- `weekend`: home 1.3, work 0.2, school 0.0, other 1.2
- 등

### 한계
- NIMS contact matrix 는 평일 학기 측정값
- 주말/방학 정확한 multiplier 측정 안 됨

### 후속 해결
- NIMS 동료 notebook 04/06 결과 확인
- 또는 자체 추정 (다른 sources)

---

## 5. Contact Matrix 절대값

### 현재 상태
NIMS 측정 contact matrix 가 일반 설문 대비 낮은 값 (under-estimate 가능성).

### 한계
- 절대 β 해석 어려움
- β 로 흡수 (calibration 통해 자동 보정)

---

## 6. KT Mobility — 검출률

### 0-9세, 70+
- 0-9세 검출률 0.15 (휴대폰 미보유)
- 70+ 검출률 1.50 (자녀 집 거주로 주민등록 분모 부정확)

### 현재 처리
- 정적 모델 (자기 행정동만)
- KT mobility 사용 안 함

### 한계
- 70+ 검출률 1.5 원인 미검증 (가설만)
- 자녀 집 거주 가정 미정량화

---

## 7. School Mobility 단순화

### 현재 상태
`M_school = identity` (학생 자기 행정동에서 학교 다닌다 가정)

### 한계
- 통학 (학교 위치가 거주지와 다름) 무시
- 학원 mobility 는 일부 KT mobility 로 (10-19세, M_other)

### 후속 해결
- 학교 통학 OD 데이터 확보 (교육청 등)

---

## 8. 시즌성 모델

### 현재 상태
`β(t) = β · (1 + amp · cos(2π·(t - peak_day) / 365))`
- amp fit 대상
- peak_day = 130 고정 (1월 중순)

### 한계
- Cosine 단순 가정
- 실제로는 환경 (온도/습도), 사회 (학기), 면역 historical 등 복합

### 후속 해결
- 더 정교한 시즌성 (예: 온도 데이터 연동)
- 또는 충분히 fit 하는지 확인 후 결정

---

## 향후 협조 요청 우선순위

1. **HIRA 외래환자 데이터** (Stage 5 ICER 필수, γ_report 분리)
2. **ILI 연령별 raw + 시도별** (정밀화)
3. **HIRA 입원/사망 데이터** (Stage 5 비용 산출)
4. **백신 접종률 raw** (시도별/연령별 정확값)

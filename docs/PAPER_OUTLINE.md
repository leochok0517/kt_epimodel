# Paper Outline — Policy-centered

## 논문 방향

정책 중심 1편. 방법론은 부록으로 축소.

가제목 후보:
- "Cost-effectiveness of sick-leave policies for seasonal influenza in Korea: a metapopulation modeling study"
- "Sick-leave and school closure policies for influenza control in Sudogwon"
- (확정 추후)

저널 타겟: 미정. 작업하며 결정.

## 핵심 메시지

정상 시기 인플루엔자 시즌에 sick-leave / 결석 정책 적용 시 비용효과 정량화.

## 정책 시나리오

### Baseline
- 현 한국 병가/결석 사용 패턴
- 자료: 통계청/노동부 병가 통계 등

### 정책 1: 병가 보조금 강화
- 변수: p_iso(20-69세) 0.2 → 0.5 또는 0.7
- 비용: 일당 보조 × 일수 × 사용자 수
- 효과: 직장 contact 차단 + 가족 보호

### 정책 2: 어린이집/유치원 결석 권장
- 변수: p_iso(0-9세) 0.3 → 0.7
- 비용: 부모 노동 손실 (간접)
- 효과: 학교 contact + 가족 전파 차단

### 정책 3: 학교 휴교 (강한 정책)
- 변수: p_iso(5-19세) → 0.95
- 비용: 부모 노동 손실 큼
- 효과: 학교 contact 완전 차단

### 정책 4: 종합 패키지
- 정책 1+2+3 동시 적용
- 중복 효과 vs 추가 효과 평가

## 핵심 Figure

1. 모델 모식도 (행정동 metapop + 연령 stratification)
2. Calibration fit (전국 ILI 2018-2019, 2022-2023)
3. 시나리오별 attack rate (연령/시도)
4. ICER plane + WTP threshold (5000만원/QALY)
5. 민감도 분석 (tornado plot)

## 본문 vs 부록 배분

본문 (Methods 짧게):
- 모델 개요 (1 문단)
- 데이터 출처 (1 문단)
- 시나리오 (1 표)
- ICER 계산 (1 문단)

부록 (Methods 디테일):
- 모델 수식 (SEIR + Isolation, FOI, mobility)
- 데이터 정제 (KT detection rate, contact matrix scaling)
- Calibration (β, φ_a 추정)
- 민감도 분석 전체

## 미정 / 추후 결정

- 저널 타겟 (작업 후반에 결정)
- 영문 vs 국문 (영문 권장)
- 공저자 + 기여도

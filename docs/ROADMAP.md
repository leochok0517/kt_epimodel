# kt_epimodel ROADMAP

> 정책 중심 1편 논문 목표 (PAPER_OUTLINE.md 참조)

## Stage 2: Metapop 프로토타입 (4-6주)

### 2-1: 모델 코어
- parameters.py: β, φ_a, σ, γ, δ, p_iso(a) 등
- compartments.py: S, E, I, J, R 상태 변수
- foi.py: Force of infection 계산
- dynamics.py: ODE 우변

### 2-2: 시뮬레이션
- solver.py: scipy.integrate.solve_ivp
- runner.py: 단일 시즌 시뮬레이션
- output.py: 결과 저장

### 2-3: 단위 테스트
- 인구 보존, 비음수
- 합리성 (attack rate 10-30%, 정점 1-2월)

### 2-4: 통합 데모
- 한 시즌 시뮬레이션 → 결과 시각화

## Stage 3: Calibration (4-6주)

### 3-1: ILI 매칭
- 정상 시즌 (2018-2019, 2022-2023) 시계열 준비
- 모델 출력 → ILI 분율 변환

### 3-2: 파라미터 fit
- β, φ_a (14개), γ_report 추정
- Nelder-Mead 또는 L-BFGS-B
- Reference: φ_25-29 = 1, 인구 가중 평균 = 1 제약

### 3-3: 검증
- Holdout (한 시즌 빼고 fit, 빼진 시즌 예측)
- 시즌별 일관성
- 자연 실험: 2020-2022 거리두기 시기 검증

## Stage 4: 정책 시나리오 (3-4주)

### 4-1: Baseline
- 한국 sick-leave 사용률 (통계)
- 결석 패턴 (NIMS)

### 4-2: 시나리오 구현
- 정책 1-4 (p_iso 변동)

### 4-3: 결과 분석
- attack rate (연령/시도)
- Spillover 효과 분해

## Stage 5: ICER (4-6주)

### 5-1: 비용
- 직접의료비 (HIRA)
- 간접비 (노동생산성)
- 정책 비용

### 5-2: QALY
- 인플루엔자 utility weight

### 5-3: ICER 계산
- WTP threshold (5000만원/QALY)
- PSA, one-way 민감도

## Stage 6: 논문 작성 (4-8주)

### 6-1: Methods + Results 초안 (5개 figure)
### 6-2: Discussion + Introduction
### 6-3: Submission

## 마일스톤

- 2개월: Stage 2 완료
- 4개월: Stage 3 완료
- 6개월: Stage 4 완료
- 8개월: Stage 5 완료
- 12개월: 논문 초안 + submission

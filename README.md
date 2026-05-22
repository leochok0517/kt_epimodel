# kt_epimodel

수도권 metapop 인플루엔자 모델 + sick-leave 정책 ICER 분석.

## 의존성
- [`kt_data`](../kt_data/) — KT mobility + NIMS contact + ILI 정제 데이터 및 로더 (`uv sources`로 editable 참조)

## 설치
같은 부모 폴더(`~/Documents/python/NIMS/`)에 `kt_data`가 있어야 함.
```bash
uv sync
```

데이터를 다른 위치에 두려면 환경변수 사용:
```bash
export KT_DATA_ROOT=/path/to/kt_data/data
```

## 구조
```
src/kt_epimodel/
├── model/         # SEIR + Isolation compartment model
├── simulation/    # ODE solver, scenario runner
├── calibration/   # ILI calibration
├── viz/           # 결과 시각화
└── scenarios/     # 정책 시나리오
tests/
notebooks/
docs/STAGE2_DESIGN.md
outputs/
```

## 진행 상태
- [ ] **Stage 2**: Metapop prototype (진행 예정)
- [ ] **Stage 3**: ILI calibration
- [ ] **Stage 4**: Sick-leave scenarios
- [ ] **Stage 5**: ICER analysis

자세한 설계: [docs/STAGE2_DESIGN.md](docs/STAGE2_DESIGN.md)

"""기본 설치 검증."""


def test_kt_data_importable() -> None:
    import kt_data
    assert kt_data.__version__ == "0.1.0"


def test_kt_epimodel_importable() -> None:
    import kt_epimodel
    assert kt_epimodel.__version__ == "0.1.0"


def test_kt_data_loader_works() -> None:
    """kt_data 로더가 kt_epimodel 환경에서 호출 가능한지."""
    from kt_data.data.load_population import load_population_15groups
    df = load_population_15groups()
    assert df.shape[0] > 0

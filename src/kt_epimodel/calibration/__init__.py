"""kt_epimodel calibration — ILI fitting, optimizer scaffolding."""

from kt_epimodel.calibration.ili_target import (
    load_ili_target,
    load_ili_target_by_age,
    poisson_log_likelihood,
    season_start_date,
    simulation_to_ili,
    simulation_to_ili_by_age,
)
from kt_epimodel.calibration.loss import (
    make_loss_function,
    make_loss_function_by_age,
)
from kt_epimodel.calibration.optimizer import (
    CalibrationResult,
    load_result,
    optimize_calibration,
    optimize_calibration_by_age,
    save_result,
)
from kt_epimodel.calibration.param_vector import (
    N_VECTOR,
    ParameterBounds,
    REF_AGE_IDX,
    get_bounds_vector,
    get_param_names,
    initial_guess,
    params_to_vector,
    vector_to_params,
)
from kt_epimodel.calibration.simple_model import (
    build_aggregated_inputs,
    estimate_initial_infected_from_ili,
    simulate_aggregated,
)

__all__ = [
    "CalibrationResult",
    "N_VECTOR",
    "ParameterBounds",
    "REF_AGE_IDX",
    "build_aggregated_inputs",
    "estimate_initial_infected_from_ili",
    "get_bounds_vector",
    "get_param_names",
    "initial_guess",
    "load_ili_target",
    "load_ili_target_by_age",
    "load_result",
    "make_loss_function",
    "make_loss_function_by_age",
    "optimize_calibration",
    "optimize_calibration_by_age",
    "params_to_vector",
    "poisson_log_likelihood",
    "save_result",
    "season_start_date",
    "simulate_aggregated",
    "simulation_to_ili",
    "simulation_to_ili_by_age",
    "vector_to_params",
]

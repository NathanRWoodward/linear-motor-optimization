"""Phase 1: property functions (Static / Calibration / ClosedForm).

Pure-logic tests (no gmsh / build123d), so they run in the Linux sandbox too.
"""

import pytest

from physical.property_functions import (
    Calibration,
    CalibrationPoint,
    ClosedForm,
    PropertyDimensionError,
    PropertyFunction,
    PropertyParameterError,
    PropertyRangeError,
    Static,
)
from physical.units import U


# --- Static ----------------------------------------------------------------


def test_static_returns_its_value():
    k = Static(value=8.7 * U.W / (U.m * U.K))
    assert k().to(U.W / (U.m * U.K)).magnitude == pytest.approx(8.7)
    assert k.parameters == {}
    # Static satisfies the PropertyFunction protocol structurally.
    assert isinstance(k, PropertyFunction)


def test_static_ignores_operating_point_kwargs():
    # Static takes 0 parameters, so an operating point (extra kwargs) is ignored
    # rather than rejected — this is what lets to_elmer(at=...) call it uniformly.
    k = Static(value=8.7 * U.W / (U.m * U.K))
    assert k(temperature=300 * U.K).magnitude == pytest.approx(8.7)


def test_static_accepts_unit_string():
    k = Static(value="8.7 W/(m*K)")
    assert k().to(U.W / (U.m * U.K)).magnitude == pytest.approx(8.7)


# --- Calibration ------------------------------------------------------------


def _two_point_line() -> Calibration:
    # A known straight line: y = 1 + 0.05*(T - 300) [W/(m*K)] sampled at 300 K
    # (-> 1.0) and 400 K (-> 6.0). Endpoints chosen so the midpoint is exact.
    return Calibration(
        param_dims={"temperature": "[temperature]"},
        points=[
            CalibrationPoint(inputs={"temperature": 300 * U.K}, output=1.0 * U.W / (U.m * U.K)),
            CalibrationPoint(inputs={"temperature": 400 * U.K}, output=6.0 * U.W / (U.m * U.K)),
        ],
    )


def test_calibration_interpolates_endpoints_and_midpoint_exactly():
    cal = _two_point_line()
    unit = U.W / (U.m * U.K)
    assert cal(temperature=300 * U.K).to(unit).magnitude == pytest.approx(1.0)
    assert cal(temperature=400 * U.K).to(unit).magnitude == pytest.approx(6.0)
    assert cal(temperature=350 * U.K).to(unit).magnitude == pytest.approx(3.5)
    assert cal.parameters == {"temperature": "[temperature]"}


def test_calibration_converts_input_units_before_interpolating():
    cal = _two_point_line()
    unit = U.W / (U.m * U.K)
    # 350 K expressed in Celsius (76.85 degC) must give the same midpoint value.
    assert cal(temperature=76.85 * U.degC).to(unit).magnitude == pytest.approx(3.5, rel=1e-3)


def test_calibration_rejects_unit_mismatched_point():
    with pytest.raises(PropertyDimensionError):
        Calibration(
            param_dims={"temperature": "[temperature]"},
            points=[CalibrationPoint(inputs={"temperature": 5 * U.kg}, output=1.0 * U.W / (U.m * U.K))],
        )


def test_calibration_out_of_range_raises_by_default():
    cal = _two_point_line()
    with pytest.raises(PropertyRangeError):
        cal(temperature=500 * U.K)


def test_calibration_extrapolation_is_opt_in():
    # With extrapolate=True, np.interp clamps to the endpoint rather than raising.
    cal = Calibration(
        param_dims={"temperature": "[temperature]"},
        points=[
            CalibrationPoint(inputs={"temperature": 300 * U.K}, output=1.0 * U.W / (U.m * U.K)),
            CalibrationPoint(inputs={"temperature": 400 * U.K}, output=6.0 * U.W / (U.m * U.K)),
        ],
        extrapolate=True,
    )
    assert cal(temperature=500 * U.K).to(U.W / (U.m * U.K)).magnitude == pytest.approx(6.0)


def test_calibration_nearest_method():
    cal = Calibration(
        param_dims={"temperature": "[temperature]"},
        points=[
            CalibrationPoint(inputs={"temperature": 300 * U.K}, output=1.0 * U.W / (U.m * U.K)),
            CalibrationPoint(inputs={"temperature": 400 * U.K}, output=6.0 * U.W / (U.m * U.K)),
        ],
        method="nearest",
    )
    assert cal(temperature=310 * U.K).to(U.W / (U.m * U.K)).magnitude == pytest.approx(1.0)
    assert cal(temperature=390 * U.K).to(U.W / (U.m * U.K)).magnitude == pytest.approx(6.0)


def test_calibration_rejects_nd_for_now():
    with pytest.raises(ValueError):
        Calibration(
            param_dims={"temperature": "[temperature]", "pressure": "[pressure]"},
            points=[
                CalibrationPoint(
                    inputs={"temperature": 300 * U.K, "pressure": 1 * U.bar},
                    output=1.0 * U.W / (U.m * U.K),
                )
            ],
        )


# --- ClosedForm -------------------------------------------------------------


def _br_of_t() -> ClosedForm:
    # Linear remanence falloff: Br(T) = Br0 * (1 + alpha*(T - T0)).
    br0 = 1.48 * U.T
    alpha = -0.0012 / U.K  # ~ -0.12 %/K, typical for NdFeB
    t0 = 293.15 * U.K

    def expression(*, temperature):
        return br0 * (1 + alpha * (temperature - t0))

    return ClosedForm(param_dims={"temperature": "[temperature]"}, result_dim="[magnetic_field]", expression=expression)


def test_closed_form_evaluates_and_round_trips_units():
    br = _br_of_t()
    # At the reference temperature it returns Br0 exactly.
    assert br(temperature=293.15 * U.K).to(U.T).magnitude == pytest.approx(1.48)
    # 100 K hotter -> 1.48 * (1 - 0.12) = 1.3024 T.
    assert br(temperature=393.15 * U.K).to(U.T).magnitude == pytest.approx(1.48 * (1 - 0.12), rel=1e-9)
    assert br.result_dimensionality == "[magnetic_field]"


def test_closed_form_result_is_a_quantity_in_expected_dimension():
    br = _br_of_t()
    result = br(temperature=300 * U.K)
    assert isinstance(result, U.Quantity)
    assert result.check("[magnetic_field]")


# --- Typed errors (shared base) --------------------------------------------


def test_missing_parameter_raises_typed_error():
    cal = _two_point_line()
    with pytest.raises(PropertyParameterError):
        cal()  # temperature not supplied


def test_wrong_dimension_parameter_raises_typed_error():
    cal = _two_point_line()
    with pytest.raises(PropertyDimensionError):
        cal(temperature=5 * U.kg)


def test_typed_errors_are_not_bare_value_errors():
    # They subclass PropertyError (and not ValueError), so callers can catch the
    # property-function family precisely.
    assert not issubclass(PropertyParameterError, ValueError)
    assert not issubclass(PropertyDimensionError, ValueError)


# --- to_elmer(at=...) for each kind -----------------------------------------


def test_to_elmer_strips_to_si_float_for_each_kind():
    from physical.materials.properties import MagneticProperties, ThermalProperties

    at = {"temperature": 393.15 * U.K}

    # Static: ignores `at`.
    static_thermal = ThermalProperties(conductivity=Static(value=8.7 * U.W / (U.m * U.K)))
    assert static_thermal.to_elmer(at=at)["Heat Conductivity"] == pytest.approx(8.7)

    # Calibration: consumes `at`. 393.15 K on the 2-point line -> 1 + 0.05*93.15.
    cal_thermal = ThermalProperties(conductivity=_two_point_line())
    assert cal_thermal.to_elmer(at=at)["Heat Conductivity"] == pytest.approx(1.0 + 0.05 * (393.15 - 300))

    # ClosedForm: a temperature-dependent remanence feeds |M| = Br/mu0.
    MU0 = 1.25663706212e-6
    magnetic = MagneticProperties(remanence=_br_of_t())
    expected_mag = (1.48 * (1 - 0.12)) / MU0
    assert magnetic.magnetization_magnitude(at=at) == pytest.approx(expected_mag, rel=1e-6)


def test_property_field_rejects_wrong_dimensionality_property():
    from physical.materials.properties import ThermalProperties

    # A Static of the wrong dimensionality assigned to a thermal-conductivity
    # field must fail at construction (the field validates result dimensionality),
    # not silently at solve time.
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ThermalProperties(conductivity=Static(value=5 * U.kg))

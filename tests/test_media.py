"""L1 media engine: distance boundaries, violations, optical budgets."""

import pytest

from netarchitect.errors import PhysicalDistanceViolationError
from netarchitect.media import optical_budget, select_media, SMF_OPTICS
from netarchitect.rationale import RationaleLog


@pytest.mark.parametrize("distance,medium,optic", [
    (1, "Cat6a UTP", "10GBASE-T (RJ-45)"),
    (100, "Cat6a UTP", "10GBASE-T (RJ-45)"),          # exactly at the 802.3an limit
    (100.01, "OM4 MMF", "10GBASE-SR"),                # just over -> fibre
    (101, "OM4 MMF", "10GBASE-SR"),
    (400, "OM4 MMF", "10GBASE-SR"),                   # exactly at the OM4 SR limit
    (400.5, "OS2 SMF", "10GBASE-LR"),
    (5_000, "OS2 SMF", "10GBASE-LR"),
    # 10 km is LR's *nominal* reach, but 4.0 dB fibre + 1.5 dB connectors + 2 splices
    # + 1 dB margin = 6.7 dB > 6.2 dB budget, so the engine correctly escalates to ER.
    (10_000, "OS2 SMF", "10GBASE-ER"),
    (10_001, "OS2 SMF", "10GBASE-ER"),
    (22_000, "OS2 SMF", "10GBASE-ER"),
    (35_000, "OS2 SMF", "10GBASE-ZR"),                # ER budget exceeded -> ZR
    (60_000, "OS2 SMF", "10GBASE-ZR"),
    (90_000, "Carrier circuit", None),                # beyond unamplified reach
])
def test_distance_rules(distance, medium, optic):
    d = select_media(distance, 10)
    assert d.medium == medium
    if optic:
        assert d.transceiver == optic


def test_copper_over_100m_raises_with_attenuation_warning():
    with pytest.raises(PhysicalDistanceViolationError) as exc:
        select_media(101, 10, preference="copper", subject="IDF-3 run")
    err = exc.value
    assert err.distance_m == 101 and err.limit_m == 100
    assert "dB" in err.attenuation_warning and "49.3" in err.attenuation_warning
    assert err.exit_code == 3
    assert err.to_dict()["code"] == "PHYSICAL_DISTANCE_VIOLATION"


def test_copper_exactly_100m_is_allowed():
    assert select_media(100, 10, preference="copper").medium == "Cat6a UTP"


def test_poe_beyond_100m_raises_even_on_auto():
    with pytest.raises(PhysicalDistanceViolationError, match="PoE"):
        select_media(120, 1, preference="auto", poe=True)


def test_copper_above_10g_raises():
    with pytest.raises(PhysicalDistanceViolationError, match="10 Gbps"):
        select_media(30, 40, preference="copper")


def test_fiber_preference_inside_copper_range_gives_om4():
    d = select_media(40, 10, preference="fiber")
    assert d.medium == "OM4 MMF"


def test_40g_over_om4_reach_escalates_to_lr4():
    log = RationaleLog()
    d = select_media(200, 40, log=log)
    assert d.transceiver == "40GBASE-LR4"
    assert any("Escalate" in e.decision for e in log.entries)


def test_100g_short_reach_uses_sr4():
    assert select_media(90, 100).transceiver == "100GBASE-SR4"


@pytest.mark.parametrize("bad", [0, -10, None])
def test_non_positive_distance_rejected(bad):
    with pytest.raises(ValueError):
        select_media(bad, 10)


def test_internet_transport_is_ipsec_overlay():
    d = select_media(5_570_000, 1, transport="internet")
    assert d.medium == "Carrier circuit" and "IPsec" in d.service
    assert 35 < d.latency_ms < 45            # 5570 km * 1.4 / 204 km/ms ~ 38 ms


def test_explainable_rationale_matches_spec_wording():
    log = RationaleLog()
    select_media(22_000, 10, log=log)
    text = log.entries[0].justification
    assert "Selected OS2 Single-Mode Fiber because link distance (22 km) exceeds the 400 m" in text
    assert "Multimode" in text and "dB" in text


def test_optical_budget_arithmetic():
    er = next(o for o in SMF_OPTICS if o.name == "10GBASE-ER")
    b = optical_budget(er, 22_000, margin_db=1.0)
    assert b.fiber_loss_db == pytest.approx(6.6)
    assert b.connector_loss_db == pytest.approx(1.5)
    assert b.splices == 5 and b.splice_loss_db == pytest.approx(0.5)
    assert b.total_loss_db == pytest.approx(8.6)
    assert b.total_with_margin_db == pytest.approx(9.6)
    assert b.headroom_db == pytest.approx(1.4)
    assert b.passes


def test_er_rejected_at_35km_because_budget_not_reach():
    er = next(o for o in SMF_OPTICS if o.name == "10GBASE-ER")
    b = optical_budget(er, 35_000, margin_db=1.0)
    assert 35_000 <= er.reach_m           # nominal reach would allow it...
    assert not b.passes                   # ...but the loss budget does not


def test_zr_on_short_link_flags_attenuator():
    d = select_media(28_000, 10)
    assert d.transceiver == "10GBASE-ZR"
    assert d.budget.attenuator_needed
    assert any("attenuator" in w for w in d.warnings)


def test_bandwidth_over_100g_rejected():
    with pytest.raises(ValueError):
        select_media(50, 400)

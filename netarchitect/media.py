"""L1/L2 Media Engine - distance & bandwidth physics.

Decision rules (assignment section 3):
  * run <= 100 m           -> Cat6a / 10GBASE-T        (IEEE 802.3an channel limit)
  * 100 m < run <= 400 m   -> OM4 MMF / 10GBASE-SR     (850 nm modal-dispersion limit)
  * run > 400 m            -> OS2 SMF / 10GBASE-LR/ER/ZR chosen by optical budget
  * copper requested > 100 m -> PhysicalDistanceViolationError

Optical link loss uses the IEEE 802.3 link model: fibre attenuation per km at
the optic's wavelength + mated connector pairs + fusion splices + a
configurable safety margin, compared against each optic's maximum channel
insertion loss.  The minimum-loss (receiver overload) check is also applied,
because long-reach optics on short fibre can saturate the receiver.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

from .errors import PhysicalDistanceViolationError
from .rationale import RationaleLog

COPPER_LIMIT_M = 100.0
OM4_SR_LIMIT_M = 400.0

# Cat6a / Class EA channel insertion-loss limit at 500 MHz (TIA-568.2-D) over 100 m.
CAT6A_IL_500MHZ_DB = 49.3

CONNECTOR_LOSS_DB = 0.75      # TIA-568 maximum per mated connector pair
CONNECTOR_PAIRS = 2           # patch panel at each end
SPLICE_LOSS_DB = 0.1          # typical fusion splice
SPLICE_INTERVAL_KM = 4.0      # one splice per ~4 km cable reel

FIBER_KM_PER_MS = 204.0       # c / n (n ~= 1.468) -> ~204 km per ms, ~4.9 us/km
INTERNET_PATH_FACTOR = 1.4    # routed Internet paths are ~1.4x the cable distance


@dataclass(frozen=True)
class Optic:
    name: str
    speed_gbps: int
    wavelength_nm: int
    fiber: str
    reach_m: float
    max_loss_db: float        # maximum channel insertion loss
    min_loss_db: float        # below this the receiver may overload
    atten_db_km: float        # IEEE link-model attenuation at this wavelength
    standard: str


MMF_OPTICS = [
    Optic("10GBASE-SR", 10, 850, "OM4", 400, 2.9, 0.0, 3.5, "IEEE 802.3ae Clause 52"),
    Optic("40GBASE-SR4", 40, 850, "OM4", 150, 1.5, 0.0, 3.5, "IEEE 802.3ba Clause 86"),
    Optic("100GBASE-SR4", 100, 850, "OM4", 100, 1.9, 0.0, 3.5, "IEEE 802.3bm Clause 95"),
]

SMF_OPTICS = [
    Optic("10GBASE-LR", 10, 1310, "OS2", 10_000, 6.2, 0.0, 0.4, "IEEE 802.3ae Clause 52"),
    Optic("10GBASE-ER", 10, 1550, "OS2", 40_000, 11.0, 5.0, 0.3, "IEEE 802.3ae Clause 52"),
    Optic("10GBASE-ZR", 10, 1550, "OS2", 80_000, 23.0, 11.0, 0.3, "SFF MSA (non-IEEE)"),
    Optic("40GBASE-LR4", 40, 1310, "OS2", 10_000, 6.7, 0.0, 0.4, "IEEE 802.3ba Clause 87"),
    Optic("40GBASE-ER4", 40, 1310, "OS2", 40_000, 18.5, 0.0, 0.4, "IEEE 802.3bm Clause 87"),
    Optic("100GBASE-LR4", 100, 1310, "OS2", 10_000, 6.3, 0.0, 0.4, "IEEE 802.3ba Clause 88"),
    Optic("100GBASE-ER4", 100, 1310, "OS2", 40_000, 18.0, 0.0, 0.4, "IEEE 802.3ba Clause 88"),
]

SPEED_TIERS = (10, 40, 100)


@dataclass
class OpticalBudget:
    optic: str
    fiber_km: float
    fiber_loss_db: float
    connector_loss_db: float
    splices: int
    splice_loss_db: float
    margin_db: float
    total_loss_db: float          # fibre + connectors + splices
    total_with_margin_db: float
    max_loss_db: float
    min_loss_db: float
    headroom_db: float
    passes: bool
    attenuator_needed: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MediaDecision:
    subject: str
    distance_m: float
    bandwidth_gbps: float
    speed_tier_gbps: int
    medium: str                 # "Cat6a UTP", "OM4 MMF", "OS2 SMF", "Carrier circuit"
    transceiver: str
    standard: str
    transport: str              # fiber | evpl | internet
    service: str = ""
    poe: bool = False
    latency_ms: float = 0.0
    budget: OpticalBudget | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["budget"] = self.budget.to_dict() if self.budget else None
        return d


def speed_tier(bandwidth_gbps: float) -> int:
    for tier in SPEED_TIERS:
        if bandwidth_gbps <= tier:
            return tier
    raise ValueError(f"bandwidth {bandwidth_gbps} Gbps exceeds the 100G single-link maximum")


def propagation_ms(distance_m: float, transport: str = "fiber") -> float:
    factor = INTERNET_PATH_FACTOR if transport == "internet" else 1.0
    return distance_m / 1000.0 * factor / FIBER_KM_PER_MS


def optical_budget(optic: Optic, distance_m: float, margin_db: float) -> OpticalBudget:
    km = distance_m / 1000.0
    fiber_loss = km * optic.atten_db_km
    connectors = CONNECTOR_PAIRS * CONNECTOR_LOSS_DB
    splices = max(0, math.ceil(km / SPLICE_INTERVAL_KM) - 1) if optic.fiber == "OS2" else 0
    splice_loss = splices * SPLICE_LOSS_DB
    total = fiber_loss + connectors + splice_loss
    applied_margin = margin_db if optic.fiber == "OS2" else 0.0  # MMF budget already includes allocation
    with_margin = total + applied_margin
    return OpticalBudget(
        optic=optic.name,
        fiber_km=round(km, 3),
        fiber_loss_db=round(fiber_loss, 2),
        connector_loss_db=round(connectors, 2),
        splices=splices,
        splice_loss_db=round(splice_loss, 2),
        margin_db=applied_margin,
        total_loss_db=round(total, 2),
        total_with_margin_db=round(with_margin, 2),
        max_loss_db=optic.max_loss_db,
        min_loss_db=optic.min_loss_db,
        headroom_db=round(optic.max_loss_db - with_margin, 2),
        passes=with_margin <= optic.max_loss_db + 1e-9 and distance_m <= optic.reach_m,
        attenuator_needed=total < optic.min_loss_db,
    )


def _copper_attenuation_warning(distance_m: float) -> str:
    projected = CAT6A_IL_500MHZ_DB * distance_m / COPPER_LIMIT_M
    return (f"Projected Cat6a insertion loss at 500 MHz over {distance_m:g} m is "
            f"{projected:.1f} dB, beyond the {CAT6A_IL_500MHZ_DB} dB Class EA channel limit; "
            f"10GBASE-T DSP cannot hold BER <= 1e-12 and PoE voltage drop rises with "
            f"loop resistance.")


def _fmt_m(distance_m: float) -> str:
    return f"{distance_m / 1000:g} km" if distance_m >= 1000 else f"{distance_m:g} m"


def select_media(distance_m: float, bandwidth_gbps: float = 10, preference: str = "auto",
                 poe: bool = False, transport: str = "fiber", subject: str = "link",
                 optical_margin_db: float = 1.0,
                 log: RationaleLog | None = None) -> MediaDecision:
    """Apply the L1 decision rules to one cable run / link and log the reasoning."""
    log = log if log is not None else RationaleLog()
    if distance_m is None or distance_m <= 0:
        raise ValueError(f"{subject}: distance must be > 0 m (got {distance_m})")
    tier = speed_tier(bandwidth_gbps)
    dist_s = _fmt_m(distance_m)
    latency = propagation_ms(distance_m, transport)

    # ---- Boundary errors: copper / PoE beyond 100 m ------------------------- #
    if (preference == "copper" or poe) and distance_m > COPPER_LIMIT_M:
        what = "PoE copper run" if poe else "Copper run"
        raise PhysicalDistanceViolationError(
            f"{subject}: {what} of {dist_s} exceeds the {COPPER_LIMIT_M:g} m IEEE 802.3an / "
            f"802.3bt channel limit. Use fibre (OM4 <= 400 m, OS2 beyond) or add an "
            f"intermediate switch/IDF.",
            distance_m=distance_m, limit_m=COPPER_LIMIT_M, medium="Cat6a UTP",
            attenuation_warning=_copper_attenuation_warning(distance_m), subject=subject)
    if preference == "copper" and tier > 10:
        raise PhysicalDistanceViolationError(
            f"{subject}: {bandwidth_gbps:g} Gbps requested on copper; Cat6a/10GBASE-T tops out "
            f"at 10 Gbps (25/40GBASE-T on Cat8 is limited to 30 m).",
            distance_m=distance_m, limit_m=30.0, medium="Cat6a UTP",
            attenuation_warning="Cat6a bandwidth (500 MHz) cannot carry >10 Gbps PAM-16 symbols.",
            subject=subject)

    # ---- Carrier / Internet transport --------------------------------------- #
    if transport == "internet":
        decision = MediaDecision(subject, distance_m, bandwidth_gbps, tier, "Carrier circuit",
                                 "Provider handoff (1000BASE-LX/10GBASE-LR UNI)",
                                 "Provider-managed", transport,
                                 service="Internet underlay + IPsec overlay", latency_ms=latency)
        log.add("L1 Media", subject, "Internet underlay with IPsec overlay",
                f"Link spans {dist_s}; owned fibre is uneconomic beyond metro reach and the "
                f"longest unamplified 10G optic (10GBASE-ZR) stops at 80 km. A carrier Internet "
                f"circuit is used and confidentiality is restored with an IPsec tunnel. "
                f"Estimated one-way propagation {latency:.1f} ms (cable distance x "
                f"{INTERNET_PATH_FACTOR} path factor / 204 km per ms in glass).",
                ["RFC 4301 (IPsec)", "ITU-T G.652"], {"latency_ms": round(latency, 3)})
        return decision

    # ---- Rule 1: <= 100 m copper -------------------------------------------- #
    if distance_m <= COPPER_LIMIT_M and preference != "fiber" and tier <= 10:
        decision = MediaDecision(subject, distance_m, bandwidth_gbps, tier, "Cat6a UTP",
                                 "10GBASE-T (RJ-45)", "IEEE 802.3an", transport, poe=poe,
                                 latency_ms=latency)
        poe_note = (" The run also carries PoE (IEEE 802.3bt Type 4, up to 90 W PSE), which is "
                    "only possible on copper and is specified to the same 100 m channel."
                    if poe else "")
        log.add("L1 Media", subject, "Cat6a UTP + 10GBASE-T",
                f"Run length {dist_s} is within the 100 m channel limit of IEEE 802.3an "
                f"(90 m permanent link + 10 m patch cords). Cat6a (Class EA, 500 MHz) supports "
                f"10GBASE-T at full reach and costs far less than optics.{poe_note}",
                ["IEEE 802.3an", "TIA-568.2-D"] + (["IEEE 802.3bt"] if poe else []),
                {"distance_m": distance_m, "limit_m": COPPER_LIMIT_M})
        return decision

    # ---- Rule 2: <= 400 m multimode ----------------------------------------- #
    if distance_m <= OM4_SR_LIMIT_M:
        mmf = next(o for o in MMF_OPTICS if o.speed_gbps == tier)
        if distance_m <= mmf.reach_m:
            budget = optical_budget(mmf, distance_m, optical_margin_db)
            decision = MediaDecision(subject, distance_m, bandwidth_gbps, tier, "OM4 MMF",
                                     mmf.name, mmf.standard, transport, budget=budget,
                                     latency_ms=latency)
            reason = ("the requester explicitly asked for fibre" if distance_m <= COPPER_LIMIT_M
                      and preference == "fiber" else
                      f"{dist_s} exceeds the 100 m copper channel limit of IEEE 802.3an")
            if tier > 10 and distance_m <= COPPER_LIMIT_M:
                reason = f"{bandwidth_gbps:g} Gbps exceeds what 10GBASE-T on Cat6a can carry"
            log.add("L1 Media", subject, f"OM4 MMF + {mmf.name}",
                    f"Selected OM4 multimode because {reason}, while staying within the "
                    f"{mmf.reach_m:g} m reach of {mmf.name} at 850 nm. Reach on multimode is "
                    f"bounded by modal dispersion (OM4 effective modal bandwidth 4700 MHz*km), "
                    f"not attenuation. Loss check: {budget.fiber_km} km x {mmf.atten_db_km} dB/km "
                    f"+ {budget.connector_loss_db} dB connectors = {budget.total_loss_db} dB "
                    f"<= {mmf.max_loss_db} dB channel budget (headroom {budget.headroom_db} dB). "
                    f"VCSEL-based SR optics are cheaper than single-mode lasers.",
                    [mmf.standard, "TIA-492AAAD (OM4)"], {"budget": budget.to_dict()})
            if budget.headroom_db < 0.3:
                msg = (f"Optical headroom only {budget.headroom_db} dB on {mmf.name}; "
                       f"clean/inspect connectors or reduce patch points.")
                decision.warnings.append(msg)
                log.warn("L1 Media", subject, msg)
            return decision
        # higher speed tiers have shorter MMF reach -> fall through to SMF
        log.add("L1 Media", subject, f"Escalate {mmf.name} -> single-mode",
                f"{bandwidth_gbps:g} Gbps over {dist_s} exceeds the {mmf.reach_m:g} m OM4 reach "
                f"of {mmf.name} (parallel 850 nm lanes suffer higher modal dispersion), so "
                f"single-mode LR4 optics are required.", [mmf.standard], level="info")

    # ---- Rule 3: > 400 m single-mode, pick optic by optical budget ----------- #
    candidates = [o for o in SMF_OPTICS if o.speed_gbps == tier]
    tried = []
    for optic in candidates:
        budget = optical_budget(optic, distance_m, optical_margin_db)
        tried.append(budget)
        if budget.passes:
            break
    else:
        # beyond unamplified reach: needs carrier transport
        max_reach = max(o.reach_m for o in candidates)
        service = "Carrier EVPL / DWDM wavelength service" if transport == "evpl" else \
            "Carrier wavelength / MPLS service"
        decision = MediaDecision(subject, distance_m, bandwidth_gbps, tier, "Carrier circuit",
                                 "Provider handoff (10GBASE-LR UNI)", "Provider-managed",
                                 transport, service=service, latency_ms=latency)
        log.add("L1 Media", subject, service,
                f"{dist_s} exceeds the {max_reach / 1000:g} km unamplified reach of every "
                f"{tier}G single-mode optic (last budget tried: {tried[-1].optic} needs "
                f"{tried[-1].total_with_margin_db} dB vs {tried[-1].max_loss_db} dB). Amplified "
                f"long-haul (EDFA/DWDM) is a carrier service, so a provider circuit is selected.",
                ["ITU-T G.652", "ITU-T G.694.1"], {"tried": [t.to_dict() for t in tried]})
        return decision

    why_not = []
    for t in tried[:-1]:
        reason = (f"{t.optic}: reach {next(o.reach_m for o in candidates if o.name == t.optic) / 1000:g} km"
                  f" < {dist_s}" if distance_m > next(o.reach_m for o in candidates if o.name == t.optic)
                  else f"{t.optic}: needs {t.total_with_margin_db} dB > {t.max_loss_db} dB budget")
        why_not.append(reason)
    service = "Carrier EVPL (MEF E-Line) over provider OS2" if transport == "evpl" else ""
    cir_note = (f" The {tier}G optic is the UNI port speed; the purchased EVC CIR of "
                f"{bandwidth_gbps:g} Gbps is enforced by an egress shaper on the router."
                if transport == "evpl" and bandwidth_gbps < tier else "")
    decision = MediaDecision(subject, distance_m, bandwidth_gbps, tier, "OS2 SMF", optic.name,
                             optic.standard, transport, service=service, budget=budget,
                             latency_ms=latency)
    rejected = f" Rejected: {'; '.join(why_not)}." if why_not else ""
    log.add("L1 Media", subject, f"OS2 SMF + {optic.name}" + (f" ({service})" if service else ""),
            f"Selected OS2 Single-Mode Fiber because link distance ({dist_s}) exceeds the 400 m "
            f"attenuation/dispersion limit of OM4 Multimode Fiber. Optical budget for "
            f"{optic.name} at {optic.wavelength_nm} nm: {budget.fiber_km} km x "
            f"{optic.atten_db_km} dB/km = {budget.fiber_loss_db} dB fibre + "
            f"{budget.connector_loss_db} dB connectors + {budget.splices} splices x "
            f"{SPLICE_LOSS_DB} dB = {budget.total_loss_db} dB, + {budget.margin_db} dB safety "
            f"margin = {budget.total_with_margin_db} dB <= {optic.max_loss_db} dB maximum "
            f"channel insertion loss (headroom {budget.headroom_db} dB).{rejected}{cir_note}",
            [optic.standard, "ITU-T G.652.D", "TIA-568.3-D"], {"budget": budget.to_dict()})
    if budget.attenuator_needed:
        msg = (f"{optic.name} link loss {budget.total_loss_db} dB is below the "
               f"{optic.min_loss_db} dB minimum; fit a "
               f"{math.ceil(optic.min_loss_db - budget.total_loss_db)} dB inline attenuator to "
               f"avoid receiver overload.")
        decision.warnings.append(msg)
        log.warn("L1 Media", subject, msg, [optic.standard])
    return decision

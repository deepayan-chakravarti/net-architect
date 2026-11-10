"""Architectural Rationale Log - the Explainable Decision Engine's output sink.

Every engine appends a :class:`Rationale` whenever it makes a choice, so the
final plan can answer *why* for each medium, transceiver, subnet, protocol and
topology tier.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Rationale:
    domain: str          # e.g. "L1 Media", "L3 VLSM", "L3 Routing"
    subject: str         # what the decision is about, e.g. "HQ <-> REMOTE-1"
    decision: str        # short statement of the choice
    justification: str   # natural-language engineering reason
    references: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    level: str = "decision"   # decision | warning | info

    def to_dict(self) -> dict:
        return asdict(self)


class RationaleLog:
    def __init__(self) -> None:
        self.entries: list[Rationale] = []

    def add(self, domain: str, subject: str, decision: str, justification: str,
            references: list[str] | None = None, data: dict | None = None,
            level: str = "decision") -> Rationale:
        entry = Rationale(domain, subject, decision, justification,
                          list(references or []), dict(data or {}), level)
        self.entries.append(entry)
        return entry

    def warn(self, domain: str, subject: str, message: str,
             references: list[str] | None = None, data: dict | None = None) -> Rationale:
        return self.add(domain, subject, "WARNING", message, references, data, "warning")

    def by_domain(self, domain: str) -> list[Rationale]:
        return [e for e in self.entries if e.domain == domain]

    def to_dicts(self) -> list[dict]:
        return [e.to_dict() for e in self.entries]

    def to_text(self) -> str:
        lines = []
        current = None
        for i, e in enumerate(self.entries, 1):
            if e.domain != current:
                current = e.domain
                lines.append("")
                lines.append(f"== {current} " + "=" * max(4, 70 - len(current)))
            tag = "[!]" if e.level == "warning" else f"[{i:03d}]"
            lines.append(f"{tag} {e.subject}: {e.decision}")
            lines.append(f"      Why: {e.justification}")
            if e.references:
                lines.append(f"      Ref: {', '.join(e.references)}")
        return "\n".join(lines).lstrip("\n")

    def to_markdown(self) -> str:
        lines = ["| # | Domain | Subject | Decision | Justification | References |",
                 "|---|---|---|---|---|---|"]
        for i, e in enumerate(self.entries, 1):
            def esc(s: str) -> str:
                return s.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {i} | {esc(e.domain)} | {esc(e.subject)} | {esc(e.decision)} | "
                         f"{esc(e.justification)} | {esc(', '.join(e.references))} |")
        return "\n".join(lines)

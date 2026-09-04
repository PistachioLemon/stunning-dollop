from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class SudoAuditResult:
    passwordless_entries: tuple[str, ...]
    secure: bool


def _iter_sudoers_text(paths: Iterable[Path]) -> Iterable[str]:
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            yield path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue


def audit_passwordless_sudo(
    sudoers_path: str | Path = "/etc/sudoers",
    sudoers_dir: str | Path = "/etc/sudoers.d",
) -> SudoAuditResult:
    paths = [Path(sudoers_path)]
    directory = Path(sudoers_dir)
    if directory.exists() and directory.is_dir():
        paths.extend(sorted(p for p in directory.iterdir() if p.is_file()))

    findings: list[str] = []
    for text in _iter_sudoers_text(paths):
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            upper = line.upper()
            if "NOPASSWD:" in upper:
                findings.append(line)

    return SudoAuditResult(passwordless_entries=tuple(findings), secure=not findings)


def require_production_sudo_hardening(
    sudoers_path: str | Path = "/etc/sudoers",
    sudoers_dir: str | Path = "/etc/sudoers.d",
) -> None:
    result = audit_passwordless_sudo(sudoers_path, sudoers_dir)
    if not result.secure:
        raise RuntimeError("production truck image permits passwordless sudo")

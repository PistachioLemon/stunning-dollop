from pathlib import Path

import pytest

from nova.truck_node.host_hardening import audit_passwordless_sudo, require_production_sudo_hardening


def test_passwordless_sudo_is_detected(tmp_path: Path):
    sudoers = tmp_path / "sudoers"
    sudoers.write_text("pi ALL=(ALL) NOPASSWD: ALL\n", encoding="utf-8")
    result = audit_passwordless_sudo(sudoers, tmp_path / "empty")
    assert result.secure is False
    assert result.passwordless_entries == ("pi ALL=(ALL) NOPASSWD: ALL",)
    with pytest.raises(RuntimeError, match="passwordless sudo"):
        require_production_sudo_hardening(sudoers, tmp_path / "empty")


def test_commented_nopasswd_is_ignored(tmp_path: Path):
    sudoers = tmp_path / "sudoers"
    sudoers.write_text("# pi ALL=(ALL) NOPASSWD: ALL\npi ALL=(ALL) ALL\n", encoding="utf-8")
    result = audit_passwordless_sudo(sudoers, tmp_path / "empty")
    assert result.secure is True

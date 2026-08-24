from datetime import datetime, timedelta, timezone

from nova.truck_node.security_guard import ArtifactEvidence, ArtifactTrustPolicy, SecurityGuard


def policy(**overrides):
    values = dict(
        allowed_repository="ggml-org/llama.cpp",
        allowed_workflow="release.yml",
        provenance_required=True,
        allow_hash_fallback=False,
        allowlist_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    values.update(overrides)
    return ArtifactTrustPolicy(**values)


def evidence(**overrides):
    digest = "a" * 64
    values = dict(
        sha256=digest,
        expected_sha256=digest,
        provenance_present=True,
        provenance_valid=True,
        source_repository="ggml-org/llama.cpp",
        source_workflow="release.yml",
    )
    values.update(overrides)
    return ArtifactEvidence(**values)


def test_valid_attested_artifact_is_admitted():
    ok, failures = SecurityGuard.verify_artifact_trust(policy(), evidence())
    assert ok is True
    assert failures == []


def test_modified_binary_is_rejected():
    ok, failures = SecurityGuard.verify_artifact_trust(policy(), evidence(sha256="b" * 64))
    assert ok is False
    assert "sha256_mismatch" in failures


def test_wrong_repository_or_workflow_is_rejected():
    ok, failures = SecurityGuard.verify_artifact_trust(
        policy(), evidence(source_repository="attacker/fork", source_workflow="other.yml")
    )
    assert ok is False
    assert {"wrong_repository", "wrong_workflow"}.issubset(failures)


def test_missing_attestation_fails_when_required():
    ok, failures = SecurityGuard.verify_artifact_trust(
        policy(), evidence(provenance_present=False, provenance_valid=False, source_repository=None, source_workflow=None)
    )
    assert ok is False
    assert "provenance_missing" in failures


def test_controlled_hash_fallback_can_be_enabled_for_supplier_without_provenance():
    fallback_policy = policy(provenance_required=False, allow_hash_fallback=True, allowed_workflow=None)
    ok, failures = SecurityGuard.verify_artifact_trust(
        fallback_policy,
        evidence(provenance_present=False, provenance_valid=False, source_repository=None, source_workflow=None),
    )
    assert ok is True
    assert failures == []


def test_expired_allowlist_is_rejected_offline():
    expired = policy(allowlist_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    ok, failures = SecurityGuard.verify_artifact_trust(expired, evidence())
    assert ok is False
    assert "allowlist_expired" in failures

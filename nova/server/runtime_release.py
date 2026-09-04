from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class RuntimeReleaseStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RuntimeReleaseEvidence:
    deployment_role: str
    llama_repository: str
    llama_commit: str
    llama_binary_sha256: str
    provenance_present: bool
    provenance_verified: bool
    provenance_repository: str
    provenance_workflow: str
    expected_repository: str
    expected_workflow: str
    model_id: str
    model_sha256: str
    expected_model_sha256: str
    quantization: str
    context_size: int
    benchmark_passed: bool
    tool_json_passed: bool
    restart_recovery_passed: bool
    soak_passed: bool
    operator_approved: bool


@dataclass(frozen=True)
class RuntimeReleaseResult:
    status: RuntimeReleaseStatus
    reasons: tuple[str, ...]


def evaluate_runtime_release(evidence: RuntimeReleaseEvidence) -> RuntimeReleaseResult:
    """Evaluate whether a llama.cpp + GGUF pair is eligible for server promotion.

    Cryptographic SLSA verification is intentionally external. This evaluator
    consumes the verified provenance claims and refuses any silent downgrade.
    """
    reasons: list[str] = []

    if evidence.deployment_role != "server":
        reasons.append("ai_runtime_not_server_role")
    if not evidence.llama_repository or not evidence.llama_commit:
        reasons.append("llama_source_identity_missing")
    if not _SHA256_RE.fullmatch(evidence.llama_binary_sha256.lower()):
        reasons.append("llama_binary_digest_invalid")
    if not evidence.provenance_present:
        reasons.append("provenance_missing")
    elif not evidence.provenance_verified:
        reasons.append("provenance_unverified")
    if evidence.provenance_repository != evidence.expected_repository:
        reasons.append("provenance_repository_mismatch")
    if evidence.provenance_workflow != evidence.expected_workflow:
        reasons.append("provenance_workflow_mismatch")
    if evidence.llama_repository != evidence.expected_repository:
        reasons.append("runtime_repository_mismatch")

    if not evidence.model_id:
        reasons.append("model_identity_missing")
    if not _SHA256_RE.fullmatch(evidence.model_sha256.lower()):
        reasons.append("model_digest_invalid")
    if not _SHA256_RE.fullmatch(evidence.expected_model_sha256.lower()):
        reasons.append("expected_model_digest_invalid")
    elif evidence.model_sha256.lower() != evidence.expected_model_sha256.lower():
        reasons.append("model_digest_mismatch")
    if not evidence.quantization:
        reasons.append("quantization_missing")
    if evidence.context_size <= 0:
        reasons.append("context_size_invalid")

    gates = {
        "benchmark_failed": evidence.benchmark_passed,
        "tool_json_failed": evidence.tool_json_passed,
        "restart_recovery_failed": evidence.restart_recovery_passed,
        "soak_failed": evidence.soak_passed,
        "operator_approval_missing": evidence.operator_approved,
    }
    reasons.extend(name for name, passed in gates.items() if not passed)

    if reasons:
        return RuntimeReleaseResult(RuntimeReleaseStatus.REJECTED, tuple(reasons))
    return RuntimeReleaseResult(RuntimeReleaseStatus.APPROVED, ())

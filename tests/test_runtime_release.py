from nova.server.runtime_release import (
    RuntimeReleaseEvidence,
    RuntimeReleaseStatus,
    evaluate_runtime_release,
)

SHA_A = "a" * 64
SHA_B = "b" * 64


def evidence(**overrides):
    values = dict(
        deployment_role="server",
        llama_repository="ggml-org/llama.cpp",
        llama_commit="deadbeef",
        llama_binary_sha256=SHA_A,
        provenance_present=True,
        provenance_verified=True,
        provenance_repository="ggml-org/llama.cpp",
        provenance_workflow=".github/workflows/build.yml",
        expected_repository="ggml-org/llama.cpp",
        expected_workflow=".github/workflows/build.yml",
        model_id="smollm2-360m-instruct-q4_k_m",
        model_sha256=SHA_B,
        expected_model_sha256=SHA_B,
        quantization="Q4_K_M",
        context_size=8192,
        benchmark_passed=True,
        tool_json_passed=True,
        restart_recovery_passed=True,
        soak_passed=True,
        operator_approved=True,
    )
    values.update(overrides)
    return RuntimeReleaseEvidence(**values)


def test_valid_server_runtime_release_is_approved():
    result = evaluate_runtime_release(evidence())
    assert result.status is RuntimeReleaseStatus.APPROVED
    assert result.reasons == ()


def test_truck_edge_runtime_release_is_rejected():
    result = evaluate_runtime_release(evidence(deployment_role="truck_edge"))
    assert result.status is RuntimeReleaseStatus.REJECTED
    assert "ai_runtime_not_server_role" in result.reasons


def test_modified_llama_binary_is_rejected():
    result = evaluate_runtime_release(evidence(llama_binary_sha256="bad"))
    assert result.status is RuntimeReleaseStatus.REJECTED
    assert "llama_binary_digest_invalid" in result.reasons


def test_missing_or_unverified_provenance_is_rejected():
    missing = evaluate_runtime_release(evidence(provenance_present=False))
    unverified = evaluate_runtime_release(evidence(provenance_verified=False))
    assert "provenance_missing" in missing.reasons
    assert "provenance_unverified" in unverified.reasons


def test_wrong_repository_or_workflow_is_rejected():
    result = evaluate_runtime_release(evidence(
        provenance_repository="attacker/fork",
        provenance_workflow=".github/workflows/evil.yml",
    ))
    assert "provenance_repository_mismatch" in result.reasons
    assert "provenance_workflow_mismatch" in result.reasons


def test_corrupted_or_swapped_model_is_rejected():
    result = evaluate_runtime_release(evidence(model_sha256=SHA_A))
    assert result.status is RuntimeReleaseStatus.REJECTED
    assert "model_digest_mismatch" in result.reasons


def test_benchmark_restart_soak_and_operator_gates_fail_closed():
    result = evaluate_runtime_release(evidence(
        benchmark_passed=False,
        tool_json_passed=False,
        restart_recovery_passed=False,
        soak_passed=False,
        operator_approved=False,
    ))
    assert set(result.reasons) >= {
        "benchmark_failed",
        "tool_json_failed",
        "restart_recovery_failed",
        "soak_failed",
        "operator_approval_missing",
    }

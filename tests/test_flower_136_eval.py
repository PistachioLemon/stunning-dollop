from nova.federation.flower_eval import FederationRun, compare_flower_runs


def test_flower_136_candidate_wins_when_transport_recovery_improves():
    baseline = FederationRun("1.35", 18, 1450, 1, 9, True, 9, 6, 0, 8, 0, 6, True, 2, 2, 1, True, True)
    candidate = FederationRun("1.36", 18, 1440, 1, 9, True, 9, 6, 0, 8, 0, 6, True, 0, 0, 0, True, True)
    result = compare_flower_runs(baseline, candidate)
    assert result.preferred == "1.36"
    assert "candidate handles duplicate content better" in result.reasons


def test_flower_136_tls_or_soak_regression_blocks_promotion():
    baseline = FederationRun("1.35", 18, 1450, 1, 9, True, tls_verified=True, soak_completed=True)
    candidate = FederationRun("1.36", 15, 1200, 0, 10, True, tls_verified=False, soak_completed=False)
    result = compare_flower_runs(baseline, candidate)
    assert result.preferred == "1.35"
    assert any("recovery/security regression" in reason for reason in result.reasons)

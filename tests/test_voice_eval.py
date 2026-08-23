from nova.server.voice_eval import VoiceGate, VoiceMetrics, compare_voice_candidates


def test_voice_gate_accepts_candidate_within_limits():
    gate = VoiceGate(0.12, 650, 0.02, 4096, 0)
    ok, failures = gate.evaluate(VoiceMetrics(0.10, 500, 0.01, 3200, 0))
    assert ok is True
    assert failures == []


def test_voice_gate_reports_contention_failures():
    gate = VoiceGate(0.12, 650, 0.02, 4096, 0)
    ok, failures = gate.evaluate(VoiceMetrics(0.15, 900, 0.03, 4600, 2))
    assert ok is False
    assert set(failures) == {
        "word_error_rate",
        "end_of_speech_latency",
        "false_vad_rate",
        "peak_ram",
        "audio_dropouts",
    }


def test_whisper_193_wins_when_accuracy_is_not_regressed_and_runtime_improves():
    baseline = VoiceMetrics(0.10, 600, 0.01, 3200, 0, 0.01, 80, 70)
    candidate = VoiceMetrics(0.09, 520, 0.009, 3000, 0, 0.009, 75, 67)
    preferred, reasons = compare_voice_candidates("1.9.2", baseline, "1.9.3", candidate)
    assert preferred == "1.9.3"
    assert "candidate_better:latency" in reasons


def test_whisper_193_is_rejected_on_false_vad_regression_even_if_faster():
    baseline = VoiceMetrics(0.10, 600, 0.01, 3200, 0, 0.01, 80, 70)
    candidate = VoiceMetrics(0.09, 450, 0.02, 2800, 0, 0.01, 70, 65)
    preferred, reasons = compare_voice_candidates("1.9.2", baseline, "1.9.3", candidate)
    assert preferred == "1.9.2"
    assert "regression:false_vad_rate" in reasons

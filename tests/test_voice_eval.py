from nova.server.voice_eval import VoiceGate, VoiceMetrics


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

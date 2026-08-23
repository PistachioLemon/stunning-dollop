from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceMetrics:
    word_error_rate: float
    end_of_speech_latency_ms: float
    false_vad_rate: float
    peak_ram_mb: float
    audio_dropouts: int = 0
    missed_speech_rate: float = 0.0
    peak_cpu_pct: float = 0.0
    peak_temp_c: float = 0.0


@dataclass(frozen=True)
class VoiceGate:
    max_word_error_rate: float
    max_end_of_speech_latency_ms: float
    max_false_vad_rate: float
    max_peak_ram_mb: float
    max_audio_dropouts: int = 0

    def evaluate(self, metrics: VoiceMetrics) -> tuple[bool, list[str]]:
        failures: list[str] = []
        if metrics.word_error_rate > self.max_word_error_rate:
            failures.append("word_error_rate")
        if metrics.end_of_speech_latency_ms > self.max_end_of_speech_latency_ms:
            failures.append("end_of_speech_latency")
        if metrics.false_vad_rate > self.max_false_vad_rate:
            failures.append("false_vad_rate")
        if metrics.peak_ram_mb > self.max_peak_ram_mb:
            failures.append("peak_ram")
        if metrics.audio_dropouts > self.max_audio_dropouts:
            failures.append("audio_dropouts")
        return not failures, failures


def compare_voice_candidates(
    baseline_version: str,
    baseline: VoiceMetrics,
    candidate_version: str,
    candidate: VoiceMetrics,
) -> tuple[str, list[str]]:
    """Conservative A/B promotion gate for server-side voice runtimes."""
    reasons: list[str] = []
    regressions = {
        "word_error_rate": candidate.word_error_rate > baseline.word_error_rate,
        "false_vad_rate": candidate.false_vad_rate > baseline.false_vad_rate,
        "missed_speech_rate": candidate.missed_speech_rate > baseline.missed_speech_rate,
        "audio_dropouts": candidate.audio_dropouts > baseline.audio_dropouts,
    }
    failed = [name for name, regressed in regressions.items() if regressed]
    if failed:
        reasons.extend(f"regression:{name}" for name in failed)
        return baseline_version, reasons

    candidate_wins = 0
    baseline_wins = 0
    lower_is_better = (
        (candidate.word_error_rate, baseline.word_error_rate, "word_error_rate"),
        (candidate.end_of_speech_latency_ms, baseline.end_of_speech_latency_ms, "latency"),
        (candidate.false_vad_rate, baseline.false_vad_rate, "false_vad_rate"),
        (candidate.peak_ram_mb, baseline.peak_ram_mb, "peak_ram"),
        (candidate.audio_dropouts, baseline.audio_dropouts, "audio_dropouts"),
        (candidate.missed_speech_rate, baseline.missed_speech_rate, "missed_speech_rate"),
        (candidate.peak_cpu_pct, baseline.peak_cpu_pct, "peak_cpu"),
        (candidate.peak_temp_c, baseline.peak_temp_c, "peak_temp"),
    )
    for candidate_value, baseline_value, name in lower_is_better:
        if candidate_value < baseline_value:
            candidate_wins += 1
            reasons.append(f"candidate_better:{name}")
        elif candidate_value > baseline_value:
            baseline_wins += 1
            reasons.append(f"baseline_better:{name}")

    if candidate_wins > baseline_wins:
        return candidate_version, reasons
    if candidate_wins == baseline_wins:
        reasons.append("no_decisive_improvement")
        return "hold", reasons
    return baseline_version, reasons

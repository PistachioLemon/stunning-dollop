from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceMetrics:
    word_error_rate: float
    end_of_speech_latency_ms: float
    false_vad_rate: float
    peak_ram_mb: float
    audio_dropouts: int = 0


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

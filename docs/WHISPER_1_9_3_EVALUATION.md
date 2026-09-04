# whisper.cpp 1.9.3 Evaluation

Status: isolated server-side evaluation only.

Baseline: whisper.cpp 1.9.2
Candidate: whisper.cpp 1.9.3

The Raspberry Pi 5 truck node does not run this workload. Audio inference remains on the mini-PC/server; the phone or approved microphone endpoint supplies audio.

## Required scenarios

- quiet cab
- diesel idle
- highway speed
- open window
- radio/music playing
- Bluetooth headset
- overlapping speech
- short dispatch commands
- long dictation
- simultaneous MQTT traffic
- simultaneous local LLM inference
- 8-12 hour soak

## Metrics

Record word-error rate, false-VAD rate, missed-speech rate, end-of-speech latency, peak RAM, peak CPU, peak temperature, and audio dropouts.

## Promotion rule

1.9.3 is not promoted because it is newer. Any regression in word-error rate, false-VAD rate, missed-speech rate, or audio dropouts keeps 1.9.2 as the preferred build. Otherwise the candidate must show a decisive aggregate improvement in measured runtime/recognition metrics.

Hardware measurements are required before promotion. GitHub CI validates the comparison logic only.

# whisper.cpp 1.9.2 Evaluation Lane

Status: approved for isolated benchmarking only. This does not replace the current voice path or enable voice inference on the truck Pi.

Candidate: whisper.cpp v1.9.2.

## Placement

Run the candidate on the Dispatcher/mini-PC voice service. The truck Pi remains deterministic and AI-disabled.

## Benchmark matrix

Replay identical speech samples under:

- quiet cab
- diesel idle
- interstate road noise
- radio/music background
- open window/wind noise
- Bluetooth headset
- overlapping speech
- simultaneous LLM inference and MQTT traffic

## Measurements

- word error rate / transcription corrections
- wake-to-text latency
- end-of-speech/VAD latency
- false VAD activations
- missed speech segments
- CPU utilization
- peak and steady RAM
- temperature/throttling
- audio dropouts under concurrent inference

## Promotion gate

v1.9.2 becomes the preferred voice build only if it meets or beats the current validated build on accuracy and latency without unacceptable contention. Record the exact source revision, compiler options, model digest, and benchmark dataset digest before promotion.

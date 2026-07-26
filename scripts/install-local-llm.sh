#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LLAMA_DIR="${PROJECT_DIR}/vendor/llama.cpp"
MODEL_PATH="${PROJECT_DIR}/models/nova-assistant.gguf"

sudo apt-get update
sudo apt-get install -y git cmake build-essential curl

if [[ ! -d "${LLAMA_DIR}/.git" ]]; then
  mkdir -p "${PROJECT_DIR}/vendor"
  git clone --depth 1 https://github.com/ggml-org/llama.cpp.git "${LLAMA_DIR}"
fi

cmake -S "${LLAMA_DIR}" -B "${LLAMA_DIR}/build" -DGGML_NATIVE=ON \
  -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build "${LLAMA_DIR}/build" --config Release -j2

mkdir -p "${PROJECT_DIR}/models"
if [[ -n "${NOVA_GGUF_URL:-}" ]]; then
  curl --fail --location --continue-at - "${NOVA_GGUF_URL}" --output "${MODEL_PATH}"
else
  echo "llama.cpp installed."
  echo "Set NOVA_GGUF_URL to a direct, license-approved GGUF URL and rerun,"
  echo "or copy your model to: ${MODEL_PATH}"
fi

echo "Start the local model with:"
echo "${LLAMA_DIR}/build/bin/llama-server -m ${MODEL_PATH} -c 2048 --host 127.0.0.1 --port 8080"

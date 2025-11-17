#!/usr/bin/env bash
set -euo pipefail

API_BASE=${API_BASE:-http://localhost:8000}

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but not installed. Please install jq first." >&2
  exit 1
fi


_echo_step() {
  printf '\n>>> %s\n' "$1"
}

_echo_step "Resetting backend"
curl -s -X DELETE "$API_BASE/reset" | jq

_echo_step "Registering dataset"
DATASET_JSON=$(curl -s -X POST "$API_BASE/artifact/dataset" \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://huggingface.co/datasets/bookcorpus"}')
echo "$DATASET_JSON" | jq
DATASET_ID=$(echo "$DATASET_JSON" | jq -r '.metadata.id')

_echo_step "Registering code"
CODE_JSON=$(curl -s -X POST "$API_BASE/artifact/code" \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://github.com/google-research/bert"}')
echo "$CODE_JSON" | jq
CODE_ID=$(echo "$CODE_JSON" | jq -r '.metadata.id')

_echo_step "Registering model"
MODEL_JSON=$(curl -s -X POST "$API_BASE/artifact/model" \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://huggingface.co/google-bert/bert-base-uncased"}')
echo "$MODEL_JSON" | jq
MODEL_ID=$(echo "$MODEL_JSON" | jq -r '.metadata.id')

_echo_step "Seed complete"
echo "MODEL_ID=$MODEL_ID"
echo "DATASET_ID=$DATASET_ID"
echo "CODE_ID=$CODE_ID"

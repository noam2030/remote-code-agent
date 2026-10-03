#!/usr/bin/env bash

# Interactive terminal client for the remote Antigravity code agent
SERVER_URL="${AGENT_URL:-http://localhost:8080/run}"
TARGET_PROJECT="${PROJECT:-${AGENT_PROJECT:-}}"

echo "============================================="
echo "  Antigravity Remote Agent Terminal Client   "
echo "  Connected to: ${SERVER_URL}                "
if [[ -n "$TARGET_PROJECT" ]]; then
echo "  Target Project: ${TARGET_PROJECT}          "
fi
echo "  Type 'exit' or 'quit' to end session       "
echo "============================================="
echo ""

while true; do
  read -r -p "You > " prompt
  
  if [[ "$prompt" == "exit" || "$prompt" == "quit" ]]; then
    echo "Goodbye!"
    break
  fi
  
  if [[ -z "$prompt" ]]; then
    continue
  fi

  echo -n "Agent > "
  PROJECT_HEADER=()
  if [[ -n "$TARGET_PROJECT" ]]; then
    PROJECT_HEADER=(-H "X-Project-Name: ${TARGET_PROJECT}")
  fi
  curl -N -s -X POST "${SERVER_URL}" \
    -H "Content-Type: text/plain" \
    "${PROJECT_HEADER[@]}" \
    -d "$prompt"
  echo ""
  echo ""
done

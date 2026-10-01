#!/usr/bin/env bash

# Interactive terminal client for the remote Antigravity code agent
SERVER_URL="${AGENT_URL:-http://localhost:8080/run}"

echo "============================================="
echo "  Antigravity Remote Agent Terminal Client   "
echo "  Connected to: ${SERVER_URL}                "
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
  curl -N -s -X POST "${SERVER_URL}" \
    -H "Content-Type: text/plain" \
    -d "$prompt"
  echo ""
  echo ""
done

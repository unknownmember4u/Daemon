#!/usr/bin/env bash
set -e

echo "[+] Updating system"
sudo pacman -Syu --noconfirm

echo "[+] Installing system dependencies"
sudo pacman -S --needed --noconfirm \
  python python-pip python-virtualenv \
  portaudio sox \
  vosk-api \
  piper \
  curl jq \
  hyprland \
  wl-clipboard

echo "[+] Installing Ollama (local LLM runtime)"
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
else
  echo "[=] Ollama already installed"
fi

echo "[+] Pulling recommended lightweight model"
ollama pull llama3.2:3b-instruct-q4_0 || true

echo "[+] Creating Python virtual environment"
python -m venv .venv
source .venv/bin/activate

echo "[+] Installing Python packages"
pip install --upgrade pip
pip install \
  sounddevice \
  requests \
  pyyaml \
  psutil

echo "[+] Done"
echo "Activate with: source .venv/bin/activate"

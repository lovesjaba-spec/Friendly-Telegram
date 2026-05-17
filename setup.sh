#!/usr/bin/env bash

set -euo pipefail

REPO_URL="https://github.com/lovesjaba-spec/Friendly-Telegram"
TARGET_DIR="Friendly-Telegram"

say() { printf '\033[1;36m::\033[0m %s\n' "$1"; }
die() { printf '\033[1;31m!!\033[0m %s\n' "$1" >&2; exit 1; }

SUDO=""
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
	SUDO="sudo"
fi

install_system_deps() {
	say "Installing system packages"
	if command -v apt >/dev/null 2>&1; then
		$SUDO apt update
		$SUDO apt install -y python3 python3-venv python3-pip python3-dev git \
			ffmpeg neofetch dialog libjpeg-dev libwebp-dev libffi-dev \
			libcairo2 libopenjp2-7 zlib1g-dev
	elif command -v pacman >/dev/null 2>&1; then
		$SUDO pacman -Sy --noconfirm python python-pip git ffmpeg neofetch \
			dialog libjpeg-turbo libwebp libffi cairo
	elif command -v pkg >/dev/null 2>&1; then
		pkg install -y python git ffmpeg dialog libjpeg-turbo libwebp libffi libcairo
	else
		say "Unknown package manager — install python3, git and ffmpeg manually"
	fi
}

clone_or_update() {
	if [ -f CLAUDE.md ] && [ -d friendly-telegram ]; then
		say "Running inside the repository — using current directory"
		return
	fi
	if [ -d "$TARGET_DIR/.git" ]; then
		say "Updating existing checkout"
		git -C "$TARGET_DIR" pull --ff-only
	else
		say "Cloning $REPO_URL"
		git clone "$REPO_URL" "$TARGET_DIR"
	fi
	cd "$TARGET_DIR"
}

setup_venv() {
	say "Creating virtual environment"
	python3 -m venv venv
	say "Installing Python requirements"
	venv/bin/pip install --upgrade pip wheel setuptools --quiet
	AIOHTTP_NO_EXTENSIONS=1 venv/bin/pip install -r requirements.txt --upgrade --quiet
}

main() {
	install_system_deps
	clone_or_update
	[ -f requirements.txt ] || die "requirements.txt not found"
	setup_venv

	if [ "$(id -u)" -eq 0 ] && [[ " $* " != *" --root "* ]]; then
		set -- "$@" --root
	fi

	say "Done — launching Friendly-Telegram"
	exec venv/bin/python3 -m friendly-telegram "$@"
}

main "$@"

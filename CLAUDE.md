# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Birdy & Llama — a Flappy Bird-style game built with Python and Pygame, packaged as a macOS app. The bird wears glasses, has hair tufts, and a llama companion runs along the ground. Leveling up triggers a burp sound with confetti from the llama's mouth. Reaching score 40 wins the game (both characters get ice cream). Background elements progressively appear: grass turns green (score 10), clouds fade in (score 20), and trees grow in (score 30).

## Commands

```bash
# Install dependencies
pipenv install

# Run the game
pipenv run python birdy_and_llama.py

# Run via macOS app bundle (uses hardcoded virtualenv path)
open BirdyAndLlama.app

# Regenerate the app icon PNG
pipenv run python create_icon.py
```

## Architecture

**Single-file game** (`birdy_and_llama.py`) — all game logic, rendering, and sound generation in one file using a state dictionary pattern (no classes).

Key design patterns:
- **State dictionary**: `reset_game()` returns a dict with all game state (`bird_y`, `bird_vel`, `pipes`, `score`, `flowers`, `clouds`, `trees`, `confetti`, etc.). This dict is passed around and mutated in-place.
- **Procedural drawing**: All sprites (bird, llama, pipes, flowers, trees, ice cream, confetti) are drawn with primitive Pygame shapes — no image assets.
- **Programmatic audio**: `create_burp_sound()` generates a burp WAV at runtime using `array.array` and math — no sound files.
- **Level progression**: Every 4 points triggers a new level via `get_level(score)`, which interpolates gravity, pipe gap, speed, and spawn rate. Level-ups spawn confetti and play the burp sound.

**`create_icon.py`** — Generates `flappy_icon.png` (512x512) by computing RGBA pixels procedurally and encoding as PNG using `struct`/`zlib` (no PIL dependency).

**`BirdyAndLlama.app`** — macOS app bundle. The launch script at `Contents/MacOS/launch` has a hardcoded path to the Pipenv virtualenv.

## Dependencies

- Python 3.13, managed via Pipenv
- `pygame` is the only dependency

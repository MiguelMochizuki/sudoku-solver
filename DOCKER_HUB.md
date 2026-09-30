# Sudoku Solver

A 9x9 Sudoku solver built on SWI-Prolog's CLP(FD) constraint solver, served by a small FastAPI app with a web interface.

## Quick Start

```bash
docker pull miguelmochizuki/sudoku-solver
docker run --rm -p 8501:8501 miguelmochizuki/sudoku-solver
```

Then open http://localhost:8501.

## Features

- Click-to-edit grid with real-time validation, preset Easy/Medium/Hard puzzles
- Solving via CLP(FD): constraint propagation with backtracking, typically under a second
- Minimal image: distroless Python base, no shell, runs as a non-root user

## Tags

| Tag | Meaning |
|-----|---------|
| `vX.Y.Z` | A specific release |
| `latest` | The most recent release |

## Platforms

This image supports both **linux/amd64** and **linux/arm64**.

## Source

https://github.com/MiguelMochizuki/sudoku-solver

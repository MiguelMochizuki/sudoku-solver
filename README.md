# Sudoku Solver

A 9×9 Sudoku solver built with Prolog's constraint logic. Originally developed for the Logic Applied to Computing course at UFPB (Federal University of Paraíba, Brazil).

## Features

- Web interface: click-to-edit cells, real-time validation, and visual distinction between clues and solved cells. Includes preset Easy/Medium/Hard puzzles.
- Solves via SWI-Prolog's CLP(FD) library: constraint propagation with backtracking, typically under a second, guaranteed correct when a solution exists.
- Runs in Docker with all dependencies included.
- FastAPI calls into SWI-Prolog in-process via Janus, with no subprocess and no Python fallback.

## Requirements

### Quick Start (Docker - Recommended)

- **Docker**: For containerized deployment with all dependencies
  ```bash
  # Build and run in one command
  docker build -t sudoku-solver . && docker run -p 8501:8501 sudoku-solver
  ```

### Local Development

- **SWI-Prolog**: Version 7.0 or higher
  ```bash
  # Ubuntu/Debian
  sudo apt-get install swi-prolog

  # macOS
  brew install swi-prolog

  # Fedora
  sudo dnf install pl
  ```

- **Python 3.12+**: With FastAPI
  ```bash
  pip install -r requirements.txt
  ```

## Installation & Usage

### Option 1: Docker (Recommended)

1. Clone this repository:
   ```bash
   git clone https://github.com/AlbertNewton/sudoku-solver.git
   cd sudoku-solver
   ```

2. Build and run the Docker container:
   ```bash
   docker build -t sudoku-solver .
   docker run -p 8501:8501 sudoku-solver
   ```

3. Open your browser to `http://localhost:8501`

### Option 2: Local Development

1. Clone and install dependencies:
   ```bash
   git clone https://github.com/AlbertNewton/sudoku-solver.git
   cd sudoku-solver
   pip install -r requirements.txt
   ```

2. Verify SWI-Prolog is installed:
   ```bash
   swipl --version
   ```

3. Run the app:
   ```bash
   uvicorn src.main:app --reload --port 8501
   ```

4. Open your browser to `http://localhost:8501`

## Using the Web Interface

1. Click any cell and type a number (1-9), or leave it empty
2. Click Easy, Medium, or Hard to load a pre-built puzzle
3. Click Solve
4. Original clues appear in light blue, solved cells in green
5. Click Try Again to edit the puzzle again
6. Click Clear to start fresh

### Direct Prolog Interface (CLI)

Run the interactive Prolog menu:
```bash
swipl -q -g main -t halt src/solver.pl
```

The menu offers:
1. Solve example puzzles (easy, medium, hard)
2. Enter a puzzle manually
3. About information
0. Exit

### Programmatic Prolog Usage

Solve a puzzle programmatically:
```bash
swipl -q -g "solve_and_print([[_,_,3,_,2,_,6,_,_],[9,_,_,3,_,5,_,_,1],...])" -t halt src/solver.pl
```

Or use example puzzles:
```bash
swipl -q -g "puzzle(easy, B), sudoku(B), display_board(B)" -t halt src/solver.pl
```

## Example Puzzles

The application includes three built-in example puzzles:

### Easy Puzzle
```
_ _ 3 | _ 2 _ | 6 _ _
9 _ _ | 3 _ 5 | _ _ 1
_ _ 1 | 8 _ 6 | 4 _ _
------+-------+------
_ _ 8 | 1 _ 2 | 9 _ _
7 _ _ | _ _ _ | _ _ 8
_ _ 6 | 7 _ 8 | 2 _ _
------+-------+------
_ _ 2 | 6 _ 9 | 5 _ _
8 _ _ | 2 _ 3 | _ _ 9
_ _ 5 | _ 1 _ | 3 _ _
```

### Medium & Hard Puzzles
Access these directly in the web interface by clicking the respective buttons.

## How It Works

### Prolog Core (solver.pl)

The solver uses Constraint Logic Programming over Finite Domains (CLP(FD)):

1. Each cell must contain a digit from 1 to 9
2. All cells in a row must be distinct
3. All cells in a column must be distinct
4. All cells in each 3×3 block must be distinct
5. Backtracking search finds values that satisfy all constraints

Key predicates:
- `sudoku/1`: Main solver predicate
- `valid_rows/1`, `valid_columns/1`, `valid_regions/1`: Constraint validators
- `display_board/1`: Pretty-prints the board
- `solve_api/2`: Entry point the web API calls via Janus (0 = empty cell in, solved board out)

### Web Interface (src/main.py + src/static/)

- Click-to-edit grid with real-time validation
- Visual distinction between clues and solved cells
- FastAPI calls solver.pl in-process via Janus (binds directly to `libswipl.so`, no subprocess)
- Plain HTML/CSS/JS frontend served by FastAPI, talking to the API via `fetch`

## Project Structure

```
sudoku-solver/
├── src/
│   ├── solver.pl        # Prolog solver core with CLP(FD)
│   ├── main.py          # FastAPI backend (Janus integration)
│   └── static/          # HTML/CSS/JS frontend
├── tests/
│   ├── test_solver.py   # Prolog/Janus smoke tests
│   └── test_main.py     # FastAPI endpoint smoke tests
├── Dockerfile           # Container definition
├── requirements.txt     # Python dependencies
├── LICENSE              # MIT License
└── README.md            # This file
```

## Technical Details

The solver uses constraint propagation with backtracking search: SWI-Prolog's `clpfd` library, with a first-fail strategy for variable assignment, guarantees a solution when one exists.

Worst case is $O(9^n)$ where $n$ is the number of empty cells, though typical performance stays under a second thanks to constraint propagation.

## Architecture

```
┌─────────────────┐
│  static/*       │  HTML/CSS/JS Frontend
│  (browser)      │  - fetch() to /api/*
└────────┬────────┘
         │ HTTP/JSON
┌────────▼────────┐
│  src/main.py    │  FastAPI
│   (Python)      │  - Janus (in-process)
└────────┬────────┘  - threading.Lock
         │
┌────────▼────────┐
│   solver.pl     │  Prolog Solver
│   (SWI-Prolog)  │  - CLP(FD) constraints
└─────────────────┘  - Backtracking search

┌─────────────────┐
│   Dockerfile    │  Containerization
│                 │  - SWI-Prolog + FastAPI
└─────────────────┘  - Production ready
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Originally developed as a final project for Logic Applied to Computing course at UFPB, 2026.*

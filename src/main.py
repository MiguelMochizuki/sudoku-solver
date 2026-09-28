"""FastAPI backend for the Sudoku solver.

Serves the static frontend and a small JSON API that calls into
solver.pl in-process via PySwip (no subprocess). All Prolog queries go
through a single shared engine guarded by a lock, since PySwip wraps
one SWI-Prolog engine per process.
"""

import logging
import threading
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from pyswip import Prolog

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

_prolog = Prolog()
_prolog.consult(str(_BASE_DIR / "solver.pl"))
_lock = threading.Lock()

# ponytail: fixed 10s ceiling (matches the old subprocess timeout); lower/raise
# if real puzzles need more or a faster failure is wanted for empty boards.
_SOLVE_TIMEOUT_SECONDS = 10


class SolveRequest(BaseModel):
    """Request body for POST /api/solve.

    Attributes:
        board: 9x9 grid of ints, 0 for an empty cell.
    """

    board: list[list[int]]

    @field_validator("board")
    @classmethod
    def validate_board(cls, board):
        """Reject any board that isn't a 9x9 grid of digits 0-9.

        Args:
            board: The raw `board` field as parsed from the request body.

        Returns:
            The same board, unchanged, once it passes validation.

        Raises:
            ValueError: If the board isn't 9x9, or a cell is outside 0-9.
        """
        if len(board) != 9 or any(len(row) != 9 for row in board):
            raise ValueError("board must be a 9x9 grid")
        for row in board:
            for cell in row:
                if not 0 <= cell <= 9:
                    raise ValueError("cells must be integers 0-9")
        return board


@app.get("/api/puzzle/{difficulty}")
def get_puzzle(difficulty: Literal["easy", "medium", "hard"]):
    """Fetch one of the built-in example puzzles.

    Args:
        difficulty: One of "easy", "medium", "hard". FastAPI returns 422
            for any other value before this function runs.

    Returns:
        dict: `{"board": [[int]]}`, a 9x9 grid with 0 for empty cells.
    """
    with _lock:
        result = list(_prolog.query(f"puzzle({difficulty}, B), puzzle_to_list(B, L)"))
    board = [list(row) for row in result[0]["L"]]
    return {"board": board}


@app.post("/api/solve")
def solve(request: SolveRequest):
    """Solve a Sudoku board via solver.pl's solve_api/2.

    Runs the query under a 10s time limit and the shared engine lock,
    since an unconstrained board (e.g. all zeros) can otherwise search
    for far longer than any request should wait.

    Args:
        request: The board to solve, already validated as 9x9, 0-9.

    Returns:
        dict: `{"solution": [[int]]}` on success; `{"error": str}` (still
        HTTP 200) if the board is unsatisfiable or the solve times out.

    Raises:
        HTTPException: 500 if the underlying Prolog query itself fails
            unexpectedly (logged server-side before the response is sent).
    """
    goal = (
        f"catch(call_with_time_limit({_SOLVE_TIMEOUT_SECONDS}, "
        f"solve_api({request.board}, Solution)), "
        f"time_limit_exceeded, Solution = timeout)"
    )
    try:
        with _lock:
            result = list(_prolog.query(goal))
    except Exception:
        logger.exception("solve_api query failed")
        raise HTTPException(status_code=500, detail="Solver failed unexpectedly.")
    if not result:
        return {"error": "No solution exists."}
    solution_term = result[0]["Solution"]
    if solution_term == "timeout":
        return {"error": "Solver timed out."}
    solution = [list(row) for row in solution_term]
    return {"solution": solution}


app.mount("/", StaticFiles(directory=str(_BASE_DIR / "static"), html=True), name="static")

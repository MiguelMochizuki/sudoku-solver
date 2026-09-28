"""FastAPI backend for the Sudoku solver.

Serves the static frontend and a small JSON API that calls into
solver.pl in-process via Janus (SWI-Prolog's own Python binding,
ships with SWI-Prolog itself). Janus attaches a Prolog engine to
whichever Python thread calls it, so it is safe to call concurrently
from FastAPI's worker threads without an app-level lock.
"""

import logging
from pathlib import Path
from typing import Literal

import janus_swi as janus
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

janus.consult(str(_BASE_DIR / "solver.pl"))

# Prolog is embedded with --no-signals when run under Janus, so
# call_with_time_limit's alarm-based interrupt is otherwise inert.
# heartbeat() makes Prolog check for it every N inferences.
janus.heartbeat(10000)

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
    result = janus.query_once("puzzle(D, L)", {"D": difficulty})
    return {"board": result["L"]}


@app.post("/api/solve")
def solve(request: SolveRequest):
    """Solve a Sudoku board via solver.pl's solve_api/2.

    Runs the query under a 10s time limit, since an unconstrained board
    (e.g. all zeros) can otherwise search for far longer than any
    request should wait.

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
        "catch(call_with_time_limit(Limit, solve_api(Board, Solution)), "
        "time_limit_exceeded, Solution = timeout)"
    )
    try:
        result = janus.query_once(
            goal, {"Board": request.board, "Limit": _SOLVE_TIMEOUT_SECONDS}
        )
    except Exception:
        logger.exception("solve_api query failed")
        raise HTTPException(status_code=500, detail="Solver failed unexpectedly.")
    if not result["truth"]:
        return {"error": "No solution exists."}
    if result["Solution"] == "timeout":
        return {"error": "Solver timed out."}
    return {"solution": result["Solution"]}


app.mount("/", StaticFiles(directory=str(_BASE_DIR / "static"), html=True), name="static")

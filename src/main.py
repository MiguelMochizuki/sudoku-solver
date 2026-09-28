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
    board: list[list[int]]

    @field_validator("board")
    @classmethod
    def validate_board(cls, board):
        if len(board) != 9 or any(len(row) != 9 for row in board):
            raise ValueError("board must be a 9x9 grid")
        for row in board:
            for cell in row:
                if not 0 <= cell <= 9:
                    raise ValueError("cells must be integers 0-9")
        return board


@app.get("/api/puzzle/{difficulty}")
def get_puzzle(difficulty: Literal["easy", "medium", "hard"]):
    with _lock:
        result = list(_prolog.query(f"puzzle({difficulty}, B), puzzle_to_list(B, L)"))
    board = [list(row) for row in result[0]["L"]]
    return {"board": board}


@app.post("/api/solve")
def solve(request: SolveRequest):
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

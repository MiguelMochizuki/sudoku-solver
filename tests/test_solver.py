"""Plain-assert smoke tests for solver.pl's solve_api/2, run via Janus.

Run from anywhere: python tests/test_solver.py  (or: pytest tests/test_solver.py)
"""
from pathlib import Path

import janus_swi as janus

SOLVER_PATH = str(Path(__file__).resolve().parent.parent / "src" / "solver.pl")
janus.consult(SOLVER_PATH)


def _all_1_to_9(cells):
    return sorted(cells) == list(range(1, 10))


def _is_valid_solution(board):
    if not all(_all_1_to_9(row) for row in board):
        return False
    columns = list(zip(*board))
    if not all(_all_1_to_9(col) for col in columns):
        return False
    for block_row in range(0, 9, 3):
        for block_col in range(0, 9, 3):
            block = [
                board[r][c]
                for r in range(block_row, block_row + 3)
                for c in range(block_col, block_col + 3)
            ]
            if not _all_1_to_9(block):
                return False
    return True


def test_solves_example_puzzles():
    for difficulty in ("easy", "medium", "hard"):
        puzzle_result = janus.query_once("puzzle(D, L)", {"D": difficulty})
        assert puzzle_result["truth"], f"expected puzzle({difficulty}, _) to exist"
        board = puzzle_result["L"]

        solve_result = janus.query_once("solve_api(Board, Solution)", {"Board": board})
        assert solve_result["truth"], f"expected {difficulty} puzzle to be solvable"

        solution = solve_result["Solution"]
        assert _is_valid_solution(solution), f"{difficulty} solution violates Sudoku rules"


def test_unsatisfiable_board_yields_no_solution():
    board = [[0] * 9 for _ in range(9)]
    board[0][0] = 5
    board[0][1] = 5  # two 5s in row 0 makes this unsatisfiable
    result = janus.query_once("solve_api(Board, Solution)", {"Board": board})
    assert result["truth"] is False


if __name__ == "__main__":
    test_solves_example_puzzles()
    test_unsatisfiable_board_yields_no_solution()
    print("All tests passed.")

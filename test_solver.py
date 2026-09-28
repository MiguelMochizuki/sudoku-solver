"""Plain-assert smoke tests for solver.pl's solve_api/2, run via PySwip.

Run from the repo root: python test_solver.py  (or: pytest test_solver.py)
"""
from pyswip import Prolog

SOLVER_PATH = "solver.pl"


def _prolog():
    prolog = Prolog()
    prolog.consult(SOLVER_PATH)
    return prolog


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
    prolog = _prolog()
    for difficulty in ("easy", "medium", "hard"):
        puzzle_results = list(
            prolog.query(f"puzzle({difficulty}, B), puzzle_to_list(B, L)")
        )
        assert len(puzzle_results) == 1, f"expected puzzle({difficulty}, _) to exist"
        board = [list(row) for row in puzzle_results[0]["L"]]

        solve_results = list(prolog.query(f"solve_api({board}, Solution)"))
        assert len(solve_results) == 1, f"expected {difficulty} puzzle to be solvable"

        solution = [list(row) for row in solve_results[0]["Solution"]]
        assert _is_valid_solution(solution), f"{difficulty} solution violates Sudoku rules"


def test_unsatisfiable_board_yields_no_solution():
    prolog = _prolog()
    board = [[0] * 9 for _ in range(9)]
    board[0][0] = 5
    board[0][1] = 5  # two 5s in row 0 makes this unsatisfiable
    result = list(prolog.query(f"solve_api({board}, Solution)"))
    assert result == []


if __name__ == "__main__":
    test_solves_example_puzzles()
    test_unsatisfiable_board_yields_no_solution()
    print("All tests passed.")

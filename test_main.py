"""Plain-assert smoke tests for the FastAPI app, using TestClient.

Run from the repo root: python test_main.py  (or: pytest test_main.py)
"""
import threading

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_get_easy_puzzle_returns_9x9_board():
    response = client.get("/api/puzzle/easy")
    assert response.status_code == 200
    board = response.json()["board"]
    assert len(board) == 9
    assert all(len(row) == 9 for row in board)


def test_get_puzzle_invalid_difficulty_returns_422():
    response = client.get("/api/puzzle/impossible")
    assert response.status_code == 422


def test_solve_valid_board_returns_solution():
    easy = client.get("/api/puzzle/easy").json()["board"]
    response = client.post("/api/solve", json={"board": easy})
    assert response.status_code == 200
    solution = response.json()["solution"]
    assert len(solution) == 9
    assert all(sorted(row) == list(range(1, 10)) for row in solution)


def test_solve_unsatisfiable_board_returns_error_not_500():
    board = [[0] * 9 for _ in range(9)]
    board[0][0] = 5
    board[0][1] = 5
    response = client.post("/api/solve", json={"board": board})
    assert response.status_code == 200
    assert response.json()["error"] == "No solution exists."


def test_solve_malformed_board_returns_422():
    response = client.post("/api/solve", json={"board": [[1, 2, 3]]})
    assert response.status_code == 422


def test_solve_empty_board_returns_some_full_solution():
    # No API-level guard against an all-empty board (that's a UI-only
    # concern) -- Prolog returns *some* valid full solution. This only
    # completes because call_with_time_limit runs solve_api like once/1:
    # plain prolog.query() has maxresult=-1 and would otherwise backtrack
    # through all ~6.7x10^21 solutions of an empty grid and never return.
    board = [[0] * 9 for _ in range(9)]
    response = client.post("/api/solve", json={"board": board})
    assert response.status_code == 200
    solution = response.json()["solution"]
    assert all(sorted(row) == list(range(1, 10)) for row in solution)


def test_solve_times_out_instead_of_hanging():
    # Force a real timeout through the actual endpoint (not a synthetic
    # goal) so the test pins main.py's real goal string, not a copy of it.
    import main

    original_timeout = main._SOLVE_TIMEOUT_SECONDS
    main._SOLVE_TIMEOUT_SECONDS = 0.001
    try:
        hard = client.get("/api/puzzle/hard").json()["board"]
        response = client.post("/api/solve", json={"board": hard})
    finally:
        main._SOLVE_TIMEOUT_SECONDS = original_timeout
    assert response.status_code == 200
    assert response.json()["error"] == "Solver timed out."


def test_solve_unexpected_error_returns_500_and_logs():
    # Spec requires 500s to have their full detail logged server-side,
    # since FastAPI does not log a raised HTTPException on its own.
    import logging

    import main

    class ListHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []

        def emit(self, record):
            self.records.append(record)

    handler = ListHandler()
    logger = logging.getLogger("main")
    logger.addHandler(handler)
    original_query = main._prolog.query

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    main._prolog.query = boom
    try:
        response = client.post("/api/solve", json={"board": [[0] * 9 for _ in range(9)]})
    finally:
        main._prolog.query = original_query
        logger.removeHandler(handler)

    assert response.status_code == 500
    assert any(r.levelno == logging.ERROR for r in handler.records), "expected an ERROR log record"


def test_concurrent_solves_do_not_interleave():
    easy = client.get("/api/puzzle/easy").json()["board"]
    hard = client.get("/api/puzzle/hard").json()["board"]
    results = {}

    def solve(name, board):
        response = client.post("/api/solve", json={"board": board})
        results[name] = response.json()["solution"]

    t1 = threading.Thread(target=solve, args=("easy", easy))
    t2 = threading.Thread(target=solve, args=("hard", hard))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    for name, board in (("easy", easy), ("hard", hard)):
        solution = results[name]
        for r in range(9):
            for c in range(9):
                if board[r][c] != 0:
                    assert solution[r][c] == board[r][c]
        assert all(sorted(row) == list(range(1, 10)) for row in solution)


if __name__ == "__main__":
    test_get_easy_puzzle_returns_9x9_board()
    test_get_puzzle_invalid_difficulty_returns_422()
    test_solve_valid_board_returns_solution()
    test_solve_unsatisfiable_board_returns_error_not_500()
    test_solve_malformed_board_returns_422()
    test_solve_empty_board_returns_some_full_solution()
    test_solve_times_out_instead_of_hanging()
    test_solve_unexpected_error_returns_500_and_logs()
    test_concurrent_solves_do_not_interleave()
    print("All tests passed.")

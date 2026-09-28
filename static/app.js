const boardEl = document.getElementById("board");
const messageEl = document.getElementById("message");
const tryAgainBtn = document.getElementById("try-again-btn");

let clueMask = Array.from({ length: 9 }, () => Array(9).fill(false));
let lastSubmittedBoard = null;

function buildGrid() {
  boardEl.innerHTML = "";
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const input = document.createElement("input");
      input.className = "cell";
      input.maxLength = 1;
      input.inputMode = "numeric";
      input.dataset.row = r;
      input.dataset.col = c;
      if (c === 2 || c === 5) input.dataset.blockRight = "true";
      if (r === 2 || r === 5) input.dataset.blockBottom = "true";
      input.addEventListener("input", onCellInput);
      boardEl.appendChild(input);
    }
  }
}

function onCellInput(event) {
  const el = event.target;
  const value = el.value;
  if (value && !/^[1-9]$/.test(value)) {
    el.value = "";
  }
}

function cellAt(r, c) {
  return boardEl.querySelector(`[data-row="${r}"][data-col="${c}"]`);
}

function readBoard() {
  const board = [];
  for (let r = 0; r < 9; r++) {
    const row = [];
    for (let c = 0; c < 9; c++) {
      const value = cellAt(r, c).value.trim();
      row.push(value === "" ? 0 : parseInt(value, 10));
    }
    board.push(row);
  }
  return board;
}

function writeBoard(board, { clues } = {}) {
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const el = cellAt(r, c);
      const value = board[r][c];
      el.value = value === 0 ? "" : String(value);
      el.disabled = Boolean(clues);
      el.classList.toggle("clue", Boolean(clues) && clueMask[r][c]);
      el.classList.toggle("solved", Boolean(clues) && !clueMask[r][c]);
    }
  }
}

function showMessage(text, kind) {
  messageEl.textContent = text;
  messageEl.className = `message show ${kind}`;
}

function clearMessage() {
  messageEl.className = "message";
}

function clearBoard() {
  clueMask = Array.from({ length: 9 }, () => Array(9).fill(false));
  lastSubmittedBoard = null;
  tryAgainBtn.classList.add("hidden");
  writeBoard(Array.from({ length: 9 }, () => Array(9).fill(0)));
  clearMessage();
}

async function loadPuzzle(difficulty) {
  clearMessage();
  const response = await fetch(`/api/puzzle/${difficulty}`);
  if (!response.ok) {
    showMessage("Failed to load puzzle.", "error");
    return;
  }
  const { board } = await response.json();
  clueMask = board.map((row) => row.map((v) => v !== 0));
  lastSubmittedBoard = null;
  tryAgainBtn.classList.add("hidden");
  writeBoard(board);
}

function tryAgain() {
  if (!lastSubmittedBoard) return;
  clueMask = lastSubmittedBoard.map((row) => row.map((v) => v !== 0));
  writeBoard(lastSubmittedBoard);
  tryAgainBtn.classList.add("hidden");
  clearMessage();
}

async function solve() {
  clearMessage();
  const board = readBoard();
  if (board.every((row) => row.every((v) => v === 0))) {
    showMessage("Enter at least one clue.", "error");
    return;
  }
  const response = await fetch("/api/solve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ board }),
  });
  if (!response.ok) {
    showMessage("Invalid puzzle input.", "error");
    return;
  }
  const data = await response.json();
  if (data.error) {
    showMessage(data.error, "error");
    return;
  }
  clueMask = board.map((row) => row.map((v) => v !== 0));
  lastSubmittedBoard = board;
  writeBoard(data.solution, { clues: true });
  tryAgainBtn.classList.remove("hidden");
  showMessage("Solved!", "success");
}

document.getElementById("clear-btn").addEventListener("click", clearBoard);
document.getElementById("solve-btn").addEventListener("click", solve);
tryAgainBtn.addEventListener("click", tryAgain);
document.querySelectorAll("[data-difficulty]").forEach((btn) => {
  btn.addEventListener("click", () => loadPuzzle(btn.dataset.difficulty));
});

buildGrid();

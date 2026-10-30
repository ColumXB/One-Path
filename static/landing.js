const COLS = 50;
const ROWS = 30;
const ISLAND_COUNT = 10;
const SVG_NS = "http://www.w3.org/2000/svg";

const grid = document.getElementById("grid");
let lineLayer = null;
let selectedCell = null;

// Build the grid cells and the SVG layer that holds the lines
function createGrid() {
  grid.style.gridTemplateColumns = `repeat(${COLS}, 1fr)`;
  grid.style.gridTemplateRows = `repeat(${ROWS}, 1fr)`;

  const cells = [];
  for (let row = 0; row < ROWS; row++) {
    for (let col = 0; col < COLS; col++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.dataset.row = row;
      cell.dataset.col = col;
      grid.appendChild(cell);
      cells.push(cell);
    }
  }

  // Overlay for lines. Its coordinates are in grid units, so lines
  // stay aligned with the cells when the window is resized.
  lineLayer = document.createElementNS(SVG_NS, "svg");
  lineLayer.setAttribute("viewBox", `0 0 ${COLS} ${ROWS}`);
  lineLayer.setAttribute("preserveAspectRatio", "none");
  lineLayer.classList.add("line-layer");
  grid.appendChild(lineLayer);

  return cells;
}

// Randomly pick `count` different cells and turn them into islands
function placeIslands(cells, count) {
  const pool = [...cells];
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  pool.slice(0, count).forEach((cell) => cell.classList.add("island"));
}

// Draw a straight line between the centers of two cells
function connectCells(cellA, cellB) {
  const line = document.createElementNS(SVG_NS, "line");
  line.setAttribute("x1", Number(cellA.dataset.col) + 0.5);
  line.setAttribute("y1", Number(cellA.dataset.row) + 0.5);
  line.setAttribute("x2", Number(cellB.dataset.col) + 0.5);
  line.setAttribute("y2", Number(cellB.dataset.row) + 0.5);
  line.setAttribute("stroke", "#29c215");
  line.setAttribute("stroke-width", "2");
  line.setAttribute("stroke-linecap", "round");
  line.setAttribute("vector-effect", "non-scaling-stroke");
  lineLayer.appendChild(line);
}

// First click selects a cell, second click connects it to the first
function handleCellClick(cell) {
  if (!selectedCell) {
    selectedCell = cell;
    cell.classList.add("selected");
    return;
  }

  if (selectedCell !== cell) {
    connectCells(selectedCell, cell);
  }

  selectedCell.classList.remove("selected");
  selectedCell = null;
}

const cells = createGrid();
placeIslands(cells, ISLAND_COUNT);

grid.addEventListener("click", (event) => {
  const cell = event.target.closest(".cell");
  if (cell) handleCellClick(cell);
});
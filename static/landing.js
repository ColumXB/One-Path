const COLS = 50;
const ROWS = 30;
const SVG_NS = "http://www.w3.org/2000/svg";
const ISLAND_IMAGES = [
  "island_images/Volcano_Island.png",
  "island_images/Tropical.png",
  "island_images/Skull_Island.png",
  "island_images/Monkey_Island.png",
  "island_images/Jungle_Island.png",
  "island_images/Ice_Island.png",
  "island_images/Haunted_Island.png",
  "island_images/Desert_Island.png",
];

const grid = document.getElementById("grid");
let lineLayer = null;
let boatLayer = null;
let selectedCell = null;
let completedGeneration = null;

/* ------------------------------------------------------------------ */
/* Grid                                                                */
/* ------------------------------------------------------------------ */

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

  boatLayer = document.createElementNS(SVG_NS, "svg");
  boatLayer.setAttribute("viewBox", `0 0 ${COLS} ${ROWS}`);
  boatLayer.setAttribute("preserveAspectRatio", "none");
  boatLayer.classList.add("boat-layer");
  grid.appendChild(boatLayer);

  return cells;
}

// Remove existing islands, then randomly pick `count` different cells
// and turn them into islands
function placeIslands(cells, count) {
  cells.forEach((cell) => {
    cell.classList.remove("island");
    delete cell.dataset.islandId;
    cell.style.backgroundImage = "";
  });

  const pool = [...cells];

  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }

  pool.slice(0, count).forEach((cell, index) => {
    cell.classList.add("island");
    cell.dataset.islandId = String.fromCharCode(65 + index);
    const image = ISLAND_IMAGES[
      Math.floor(Math.random() * ISLAND_IMAGES.length)
    ];
    cell.style.backgroundImage = `url("/static/${image}")`;
  });
}

function getIslandCoordinates() {
  const islands = {};

  document.querySelectorAll(".cell.island").forEach((cell) => {
    const id = cell.dataset.islandId;

    islands[id] = [
      Number(cell.dataset.col),
      Number(cell.dataset.row)
    ];
  });

  return islands;
}

// Remove all drawn lines and any pending selection
function clearLines() {
  lineLayer.replaceChildren();
  clearBoats();
  if (selectedCell) selectedCell.classList.remove("selected");
  selectedCell = null;
}

// Draw a straight line between the centers of two cells
function connectCells(cellA, cellB, color = "#29c215", className = "") {
  const line = document.createElementNS(SVG_NS, "line");
  line.setAttribute("x1", Number(cellA.dataset.col) + 0.5);
  line.setAttribute("y1", Number(cellA.dataset.row) + 0.5);
  line.setAttribute("x2", Number(cellB.dataset.col) + 0.5);
  line.setAttribute("y2", Number(cellB.dataset.row) + 0.5);
  line.setAttribute("stroke", color);
  line.setAttribute("stroke-width", "2");
  line.setAttribute("stroke-linecap", "round");
  line.setAttribute("vector-effect", "non-scaling-stroke");
  if (className) line.classList.add(className);
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

/* ------------------------------------------------------------------ */
function clearBoats() {
  boatLayer.replaceChildren();
}

function cellsByIsland() {
  return new Map(
    [...document.querySelectorAll(".cell.island")]
      .map((cell) => [cell.dataset.islandId, cell])
  );
}

function routeCoordinates(genes, islandCells) {
  const routeCells = [...genes].map((gene) => islandCells.get(gene));
  if (routeCells.some((cell) => !cell)) {
    throw new Error("The generated route does not match the islands on the map.");
  }
  return routeCells.map((cell) => ({
    x: Number(cell.dataset.col) + 0.5,
    y: Number(cell.dataset.row) + 0.5,
  }));
}

function drawRoute(genes, color, className) {
  const islandCells = cellsByIsland();
  const routeCells = [...genes].map((gene) => islandCells.get(gene));
  if (routeCells.some((cell) => !cell)) {
    throw new Error("The generated route does not match the islands on the map.");
  }

  routeCells.forEach((cell, index) => {
    connectCells(
      cell,
      routeCells[(index + 1) % routeCells.length],
      color,
      className
    );
  });
}

function renderFinalRoutes() {
  if (!completedGeneration) return;
  lineLayer.replaceChildren();
  const routes = [
    ["show-best", completedGeneration.best, "#2563eb", "best-route"],
    ["show-median", completedGeneration.median, "#f59e0b", "median-route"],
    ["show-worst", completedGeneration.worst, "#dc2626", "worst-route"],
  ];
  routes.forEach(([id, individual, color, className]) => {
    if (document.getElementById(id).checked && individual) {
      drawRoute(individual.genes, color, className);
    }
  });
}

function selectedAnimationRoutes(generation) {
  return [
    ["show-best", generation.best, "#2563eb"],
    ["show-median", generation.median, "#f59e0b"],
    ["show-worst", generation.worst, "#dc2626"],
  ]
    .filter(([id, individual]) =>
      individual && document.getElementById(id).checked
    )
    .map(([, individual, color]) => ({ individual, color }));
}

function animationPath(genes, islandCells) {
  const start = genes.indexOf("A");
  const orderedGenes = [...genes.slice(start), ...genes.slice(0, start), "A"];
  return routeCoordinates(orderedGenes, islandCells);
}

function pathDistances(path) {
  const distances = [0];
  for (let index = 1; index < path.length; index++) {
    distances.push(
      distances[index - 1] + Math.hypot(
        path[index].x - path[index - 1].x,
        path[index].y - path[index - 1].y
      )
    );
  }
  return distances;
}

function animateBoats(selectedRoutes) {
  const islandCells = cellsByIsland();
  clearLines();
  if (!selectedRoutes.length) return Promise.resolve();

  const paths = selectedRoutes.map(({ individual }) =>
    animationPath(individual.genes, islandCells)
  );
  const distances = paths.map(pathDistances);
  const longestRoute = Math.max(...distances.map((route) => route.at(-1)));
  const duration = 5600;
  const speed = longestRoute / duration;
  const boats = paths.map((path, index) => {
    const boat = document.createElementNS(SVG_NS, "circle");
    boat.setAttribute("r", "0.35");
    boat.setAttribute("fill", selectedRoutes[index].color);
    boat.setAttribute("stroke", "#ffffff");
    boat.setAttribute("stroke-width", "0.12");
    boat.setAttribute("vector-effect", "non-scaling-stroke");
    boatLayer.appendChild(boat);
    const lines = path.slice(0, -1).map((from) => {
          const line = document.createElementNS(SVG_NS, "line");
          line.setAttribute("x1", from.x);
          line.setAttribute("y1", from.y);
          line.setAttribute("x2", from.x);
          line.setAttribute("y2", from.y);
          line.setAttribute("stroke", selectedRoutes[index].color);
          line.setAttribute("stroke-width", "2");
          line.setAttribute("stroke-linecap", "round");
          line.setAttribute("vector-effect", "non-scaling-stroke");
          line.style.opacity = "0";
          lineLayer.appendChild(line);
          return line;
        });
    return { boat, path, distances: distances[index], lines };
  });

  return new Promise((resolve) => {
    const started = performance.now();
    const frame = (now) => {
      boats.forEach(({ boat, path, distances: routeDistances, lines }) => {
        const distanceTravelled = Math.min(
          (now - started) * speed,
          routeDistances.at(-1)
        );
        const nextPoint = routeDistances.findIndex(
          (distance) => distance > distanceTravelled
        );
        const segment = nextPoint === -1
          ? path.length - 1
          : Math.min(nextPoint, path.length - 1);
        const segmentStart = Math.max(segment - 1, 0);
        const previousDistance = routeDistances[segmentStart];
        const segmentLength = routeDistances[segment] - previousDistance;
        const fraction = segmentLength
          ? (distanceTravelled - previousDistance) / segmentLength
          : 0;
        const from = path[segmentStart];
        const to = path[segment];
        boat.setAttribute("cx", from.x + (to.x - from.x) * fraction);
        boat.setAttribute("cy", from.y + (to.y - from.y) * fraction);

        lines.forEach((line, index) => {
          if (index < segmentStart) {
            line.setAttribute("x2", path[index + 1].x);
            line.setAttribute("y2", path[index + 1].y);
            line.style.opacity = "1";
          } else if (index === segmentStart) {
            line.setAttribute("x2", from.x + (to.x - from.x) * fraction);
            line.setAttribute("y2", from.y + (to.y - from.y) * fraction);
            line.style.opacity = "1";
          } else {
            line.style.opacity = "0";
          }
        });
      });
      if ((now - started) * speed < longestRoute) {
        window.requestAnimationFrame(frame);
      } else {
        clearBoats();
        resolve();
      }
    };
    window.requestAnimationFrame(frame);
  });
}

/* ------------------------------------------------------------------ */
/* Side panel                                                          */
/* ------------------------------------------------------------------ */

const LABELS = {
  islands: "Number of Islands",
  boats: "Number of Boats",
  tournamentSize: "Tournament Size",
  generations: "Max Number of Generations",
  mutation: "Mutation Rate",
  crossover: "Crossover Rate",
  elitism: "Elitism Count",
};

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const params = {};          // current slider values, keyed by data-id
const onChange = {};        // optional per-parameter callbacks
const sliderControls = {};

// Build each slider + manual input pair from its data-* attributes
function buildSliders() {
  document.querySelectorAll("[data-slider]").forEach((el) => {
    const id = el.dataset.id;
    const min = Number(el.dataset.min);
    let max = Number(el.dataset.max);
    const step = Number(el.dataset.step);
    const unit = el.dataset.unit || "";
    const def = Number(el.dataset.value);

    el.innerHTML = `
      <div class="param-head">
        <label for="${id}-num">${LABELS[id]}</label>
        <span class="num">
          <input type="number" id="${id}-num" min="${min}" max="${max}" step="${step}" inputmode="numeric">
          ${unit ? `<span class="unit">${unit}</span>` : ""}
        </span>
      </div>
      <input type="range" id="${id}-range" min="${min}" max="${max}" step="${step}" aria-label="${LABELS[id]}">
      <div class="range-limits"><span>${min}${unit}</span><span>${max}${unit}</span></div>`;

    const range = el.querySelector("input[type=range]");
    const num = el.querySelector("input[type=number]");
    const paint = (v) =>
      range.style.setProperty("--fill", ((v - min) / (max - min)) * 100 + "%");

    function update(v, syncBox) {
      v = clamp(Math.round(v), min, max);
      const changed = params[id] !== v;
      params[id] = v;
      range.value = v;
      if (syncBox) num.value = v;
      paint(v);
      if (changed && onChange[id]) onChange[id](v);
    }

    sliderControls[id] = {
      setMax(nextMax) {
        max = Math.min(Number(el.dataset.max), nextMax);
        range.max = max;
        num.max = max;
        el.querySelector(".range-limits span:last-child").textContent = `${max}${unit}`;
        update(params[id], true);
      },
    };

    range.addEventListener("input", () => update(Number(range.value), true));

    // Typing is free-form; the box is tidied once the person finishes
    num.addEventListener("input", () => {
      if (num.value === "" || isNaN(Number(num.value))) return;
      update(Number(num.value), false);
    });
    num.addEventListener("change", () =>
      update(num.value === "" ? def : Number(num.value), true)
    );

    params[id] = undefined;
    update(def, true);
  });
}

function setupPanel() {
  buildSliders();
  onChange.boats = (count) => {
    sliderControls.tournamentSize.setMax(count);
  };
  sliderControls.tournamentSize.setMax(params.boats);

  // Brute force dims the genetic-algorithm section (unused in that mode)
  const brute = document.getElementById("bruteForce");
  const ga = document.getElementById("gaSection");
  const syncMode = () => {
    ga.classList.toggle("is-off", brute.checked);
    ga.querySelectorAll("input").forEach((i) => (i.disabled = brute.checked));
  };
  brute.addEventListener("change", syncMode);
  syncMode();

  // Fitness function: tick boxes that behave as a single choice
  const boxes = document.querySelectorAll("#fitness input");
  boxes.forEach((box) => {
    box.addEventListener("change", () => {
      if (box.checked) boxes.forEach((o) => { if (o !== box) o.checked = false; });
      else box.checked = true; // always keep one selected
    });
  });

  // Run button: announces a run with the current parameters.
  // Algorithm code listens with:
  //   document.addEventListener("onepath:run", (e) => { e.detail ... });
  document.getElementById("runButton").addEventListener("click", () => {
    document.dispatchEvent(
      new CustomEvent("onepath:run", {
        detail: {
          parameters: window.OnePath.getParameters(),
          islands: getIslandCoordinates()
        }
      })
    );
  });

  // Public hooks for the algorithm code
  window.OnePath = {
    getParameters() {
      const fit = document.querySelector("#fitness input:checked");
      return {
        bruteForce: brute.checked,
        islands: params.islands,
        boats: params.boats,
        tournamentSize: params.tournamentSize,
        maxGenerations: params.generations,
        mutationRate: params.mutation / 100,
        crossoverRate: params.crossover / 100,
        elitism: params.elitism / 100,
        fitnessFunction: fit ? fit.value : "euclidean",
      };
    },
    // After a completed run: setResults({ best, median, worst }).
    // Missing or null values show as NA; call with no argument to reset.
    setResults(r = {}) {
      [["best", "res-best"], ["median", "res-median"], ["worst", "res-worst"]]
        .forEach(([key, id]) => {
          const el = document.getElementById(id);
          const has = r[key] !== undefined && r[key] !== null;
          el.textContent = has ? r[key] : "NA";
          el.classList.toggle("is-na", !has);
        });
    },
  };
}

/* ------------------------------------------------------------------ */
/* Run handling - TODO: Change to fit spec                            */
/* ------------------------------------------------------------------ */

function formatRoute(individual) {
  return `${individual.genes}${individual.genes[0]} (${individual.distance.toFixed(2)})`;
}

async function readJsonResponse(response) {
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed (${response.status}).`);
  }
  return payload;
}

function demonstrationGenerations(totalGenerations) {
  const count = Math.min(10, totalGenerations);
  if (count <= 1) return new Set([0]);
  return new Set(
    Array.from({ length: count }, (_, index) =>
      Math.round(index * (totalGenerations - 1) / (count - 1))
    )
  );
}

async function pollRun(runId) {
  let lastGeneration = -1;
  const totalGenerations = params.generations;
  const demonstrationNumbers = demonstrationGenerations(totalGenerations);
  const statusElement = document.getElementById("runStatus");

  while (true) {
    const response = await fetch(
      `/run/${encodeURIComponent(runId)}/?after=${lastGeneration}`
    );
    const payload = await readJsonResponse(response);
    for (const generation of payload.generations) {
      lastGeneration = generation.number;
      completedGeneration = generation;
      window.OnePath.setResults({
        best: formatRoute(generation.best),
        median: formatRoute(generation.median),
        worst: formatRoute(generation.worst),
      });
      statusElement.textContent =
        `Generation ${generation.number + 1} - best distance ` +
        generation.best.distance.toFixed(2);
      if (demonstrationNumbers && demonstrationNumbers.has(generation.number)) {
        await animateBoats(selectedAnimationRoutes(generation));
      }
      await new Promise((resolve) => window.requestAnimationFrame(resolve));
    }

    if (payload.status === "completed") {
      renderFinalRoutes();
      statusElement.textContent = `Completed ${lastGeneration + 1} generations.`;
      return;
    }
    if (payload.status === "failed") {
      throw new Error(payload.error || "The algorithm run failed.");
    }

    await new Promise((resolve) => window.setTimeout(resolve, 200));
  }
}

async function handleRun(event) {
  const runButton = document.getElementById("runButton");
  const statusElement = document.getElementById("runStatus");
  const inputs = [...document.querySelectorAll(".left input")];
  const previousDisabledStates = inputs.map((input) => input.disabled);
  const previousPointerEvents = grid.style.pointerEvents;
  const csrfToken = document.querySelector(
    "#csrfForm input[name=csrfmiddlewaretoken]"
  ).value;

  runButton.disabled = true;
  inputs.forEach((input) => { input.disabled = true; });
  grid.style.pointerEvents = "none";
  statusElement.textContent = "Starting run...";
  window.OnePath.setResults();
  clearLines();
  completedGeneration = null;

  try {
    const response = await fetch("/run/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(event.detail),
    });
    const payload = await readJsonResponse(response);
    await pollRun(payload.runId);
  } catch (error) {
    statusElement.textContent = `Run failed: ${error.message}`;
  } finally {
    runButton.disabled = false;
    inputs.forEach((input, index) => {
      input.disabled = previousDisabledStates[index];
    });
    grid.style.pointerEvents = previousPointerEvents;
  }
}

/* ------------------------------------------------------------------ */
/* Start up                                                            */
/* ------------------------------------------------------------------ */

const cells = createGrid();

// Changing "Number of Islands" re-rolls the islands and clears any lines
onChange.islands = (count) => {
  clearLines();
  placeIslands(cells, count);
};

setupPanel();                       // sets params.islands to its default (5)
placeIslands(cells, params.islands);
document.querySelectorAll(".route-visibility input").forEach((input) => {
  input.addEventListener("change", renderFinalRoutes);
});
// TODO Check this is good too and fits spec
document.addEventListener("onepath:run", handleRun);

grid.addEventListener("click", (event) => {
  const cell = event.target.closest(".cell");
  if (cell) handleCellClick(cell);
});

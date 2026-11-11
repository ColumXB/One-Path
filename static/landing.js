const COLS = 50;
const ROWS = 30;
const SVG_NS = "http://www.w3.org/2000/svg";
const BOAT_SPEED = 0.033;
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
let islandLabelLayer = null;
let selectedCell = null;
let completedGeneration = null;
let activeRun = null;
const BRUTE_FORCE_LIMIT = 12;

// Build the grid cells and the SVG layer that holds the lines.
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

  islandLabelLayer = document.createElementNS(SVG_NS, "svg");
  islandLabelLayer.setAttribute("viewBox", `0 0 ${COLS} ${ROWS}`);
  islandLabelLayer.setAttribute("preserveAspectRatio", "none");
  islandLabelLayer.classList.add("island-label-layer");
  grid.appendChild(islandLabelLayer);

  return cells;
}

// Remove existing islands, then randomly pick different cells for the new ones.
function placeIslands(cells, count) {
  cells.forEach((cell) => {
    cell.classList.remove("island");
    delete cell.dataset.islandId;
    cell.style.backgroundImage = "";
  });
  islandLabelLayer.replaceChildren();

  const pool = [...cells];
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }

  pool.slice(0, count).forEach((cell, index) => {
    cell.classList.add("island");
    cell.dataset.islandId = String.fromCharCode(65 + index);
    const label = document.createElementNS(SVG_NS, "text");
    label.classList.add("island-label");
    label.setAttribute("x", Number(cell.dataset.col) + 0.5);
    label.setAttribute("y", Number(cell.dataset.row) - 0.25);
    label.textContent = cell.dataset.islandId;
    islandLabelLayer.appendChild(label);
    const image = ISLAND_IMAGES[
      Math.floor(Math.random() * ISLAND_IMAGES.length)
    ];
    cell.style.backgroundImage = `url("/static/${image}")`;
  });
}

function getIslandCoordinates() {
  const islands = {};
  document.querySelectorAll(".cell.island").forEach((cell) => {
    islands[cell.dataset.islandId] = [
      Number(cell.dataset.col),
      Number(cell.dataset.row),
    ];
  });
  return islands;
}

function clearLines() {
  lineLayer.replaceChildren();
  clearBoats();
  if (selectedCell) selectedCell.classList.remove("selected");
  selectedCell = null;
}

// Draw a straight line between the centers of two cells
function connectCells(
  cellA,
  cellB,
  color = "#29c215",
  className = "",
  strokeWidth = 2
) {
  const line = document.createElementNS(SVG_NS, "line");
  line.setAttribute("x1", Number(cellA.dataset.col) + 0.5);
  line.setAttribute("y1", Number(cellA.dataset.row) + 0.5);
  line.setAttribute("x2", Number(cellB.dataset.col) + 0.5);
  line.setAttribute("y2", Number(cellB.dataset.row) + 0.5);
  line.setAttribute("stroke", color);
  line.setAttribute("stroke-width", String(strokeWidth));
  line.setAttribute("stroke-linecap", "round");
  line.setAttribute("vector-effect", "non-scaling-stroke");
  if (className) line.classList.add(className);
  lineLayer.appendChild(line);
}

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
      className,
      3
    );
  });
}

function renderFinalRoutes() {
  if (!completedGeneration) return;
  lineLayer.replaceChildren();
  const routes = [
    ["show-median", completedGeneration.median, "#f59e0b", "median-route"],
    ["show-worst", completedGeneration.worst, "#dc2626", "worst-route"],
    ["show-best", completedGeneration.best, "#16a34a", "best-route"],
  ];
  routes.forEach(([id, individual, color, className]) => {
    if (document.getElementById(id).checked && individual) {
      drawRoute(individual.genes, color, className);
    }
  });
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

function animateBoats(generation) {
  const islandCells = cellsByIsland();
  clearLines();
  const displayedIndividuals = generation.all.slice(
    0,
    20
  );
  if (!displayedIndividuals.length) return Promise.resolve();

  const colors = ["#2563eb", "#dc2626", "#f59e0b", "#a855f7", "#f97316",
    "#ea580c", "#16a34a", "#db2777", "#4f46e5", "#65a30d"];
  const paths = displayedIndividuals.map((individual) =>
    animationPath(individual.genes, islandCells)
  );
  const distances = paths.map(pathDistances);
  const longestRoute = Math.max(...distances.map((route) => route.at(-1)));
  const bestIndex = displayedIndividuals.findIndex(
    (individual) =>
      individual.genes === generation.best.genes
      && individual.distance === generation.best.distance
  );
  const boats = paths.map((path, index) => {
    const boat = document.createElementNS(SVG_NS, "circle");
    boat.setAttribute("r", "0.2625");
    boat.setAttribute("fill", colors[index % colors.length]);
    boat.setAttribute("stroke", "#ffffff");
    boat.setAttribute("stroke-width", "0.12");
    boat.setAttribute("vector-effect", "non-scaling-stroke");
    boatLayer.appendChild(boat);
    const lines = index === bestIndex
      ? path.slice(0, -1).map((from) => {
          const line = document.createElementNS(SVG_NS, "line");
          line.setAttribute("x1", from.x);
          line.setAttribute("y1", from.y);
          line.setAttribute("x2", from.x);
          line.setAttribute("y2", from.y);
          line.setAttribute("stroke", "#16a34a");
          line.setAttribute("stroke-width", "3");
          line.setAttribute("stroke-linecap", "round");
          line.setAttribute("vector-effect", "non-scaling-stroke");
          line.style.opacity = "0";
          lineLayer.appendChild(line);
          return line;
        })
      : [];
    return { boat, path, distances: distances[index], lines };
  });

  return new Promise((resolve) => {
    const started = performance.now();
    const frame = (now) => {
      boats.forEach(({ boat, path, distances: routeDistances, lines }) => {
        const distanceTravelled = Math.min(
          (now - started) * BOAT_SPEED,
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
      if ((now - started) * BOAT_SPEED < longestRoute) {
        window.requestAnimationFrame(frame);
      } else {
        clearBoats();
        resolve();
      }
    };
    window.requestAnimationFrame(frame);
  });
}

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
const params = {};
const onChange = {};
const sliderControls = {};

function buildSliders() {
  document.querySelectorAll("[data-slider]").forEach((el) => {
    const id = el.dataset.id;
    const min = Number(el.dataset.min);
    const scaleMax = Number(el.dataset.max);
    let max = scaleMax;
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
      <div class="slider-track">
        <input type="range" id="${id}-range" min="${min}" max="${max}" step="${step}" aria-label="${LABELS[id]}">
        <span class="slider-boundary" hidden aria-hidden="true"></span>
      </div>
      <p class="slider-limit-note" hidden></p>
      <div class="range-limits"><span>${min}${unit}</span><span>${max}${unit}</span></div>`;

    const range = el.querySelector("input[type=range]");
    const num = el.querySelector("input[type=number]");
    const boundary = el.querySelector(".slider-boundary");
    const limitNote = el.querySelector(".slider-limit-note");
    const paint = (v) =>
      range.style.setProperty("--fill", ((v - min) / (Number(range.max) - min)) * 100 + "%");

    function update(v, syncBox) {
      v = clamp(Math.round(v), min, max);
      const changed = params[id] !== v;
      params[id] = v;
      range.value = v;
      if (syncBox || Number(num.value) > max || Number(num.value) < min) num.value = v;
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
      setLimit(nextMax) {
        max = Math.min(scaleMax, nextMax);
        num.max = max;
        range.setAttribute("aria-valuemax", max);
        boundary.hidden = max === scaleMax;
        limitNote.hidden = max === scaleMax;
        const position = (max - min) / (scaleMax - min);
        // Align with the range thumb's centre, accounting for its 16px width.
        boundary.style.left = `calc(${position * 100}% - ${position * 16}px + 8px)`;
        limitNote.textContent = `Brute force limit · ${max} islands`;
        update(params[id], true);
      },
    };

    range.addEventListener("input", () => update(Number(range.value), true));
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

  const brute = document.getElementById("bruteForce");
  const ga = document.getElementById("gaSection");
  const gaInputs = document.querySelectorAll("#gaSection input, #boats-num, #boats-range");
  const syncMode = () => {
    sliderControls.islands.setLimit(
      brute.checked ? BRUTE_FORCE_LIMIT : Number(document.getElementById("islands-range").max)
    );
    ga.classList.toggle("is-off", brute.checked);
    gaInputs.forEach((input) => { input.disabled = brute.checked; });
  };
  document.getElementById("cancelButton").addEventListener("click", requestCancel);
  brute.addEventListener("change", syncMode);
  syncMode();

  const boxes = document.querySelectorAll("#fitness input");
  boxes.forEach((box) => {
    box.addEventListener("change", () => {
      if (!box.checked) {
        box.checked = true;
        return;
      }
      boxes.forEach((other) => { if (other !== box) other.checked = false; });
      clearTiming();
    });
  });

  document.getElementById("runButton").addEventListener("click", () => {
    document.dispatchEvent(
      new CustomEvent("onepath:run", {
        detail: {
          parameters: window.OnePath.getParameters(),
          islands: getIslandCoordinates(),
        },
      })
    );
  });

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
    setResults(r = {}, bruteForce = false) {
      const outputs = bruteForce
        ? [["best", "res-brute-force"]]
        : [["best", "res-best"], ["median", "res-median"], ["worst", "res-worst"]];
      outputs.forEach(([key, id]) => {
          const el = document.getElementById(id);
          const has = r[key] !== undefined && r[key] !== null;
          el.textContent = has ? r[key] : "NA";
          el.classList.toggle("is-na", !has);
        });
    },
  };
}

function setRunTime(bruteForce, elapsedMs = null, running = false) {
  const id = bruteForce ? "time-brute-force" : "time-genetic";
  const output = document.getElementById(id);
  output.textContent = running
    ? "Running…"
    : elapsedMs === null ? "--" : `${elapsedMs.toFixed(3)} ms`;
  output.classList.toggle("is-na", elapsedMs === null && !running);
  output.classList.toggle("is-running", running);
}

function clearTiming() {
  setRunTime(false);
  setRunTime(true);
}

function formatRoute(individual) {
  if (!individual) return null;
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
  const count = Math.min(5, totalGenerations);
  if (count <= 1) return new Set([0]);
  return new Set(
    Array.from({ length: count }, (_, index) =>
      Math.round(index * (totalGenerations - 1) / (count - 1))
    )
  );
}

function waitForPlayback(milliseconds, signal) {
  if (signal.aborted) return Promise.resolve();
  return new Promise((resolve) => {
    const finish = () => {
      window.clearTimeout(timer);
      signal.removeEventListener("abort", finish);
      resolve();
    };
    const timer = window.setTimeout(finish, milliseconds);
    signal.addEventListener("abort", finish, { once: true });
  });
}

function requestCancel() {
  if (!activeRun || activeRun.cancelRequested) return;
  activeRun.cancelRequested = true;
  activeRun.playback.abort();
  const button = document.getElementById("cancelButton");
  button.disabled = true;
  button.textContent = "Cancelling…";
  document.getElementById("runStatus").textContent = "Cancelling run…";
}

async function cancelRun(run) {
  const response = await fetch(`/run/${encodeURIComponent(run.id)}/cancel/`, {
    method: "POST",
    headers: { "X-CSRFToken": run.csrfToken },
  });
  let payload = await readJsonResponse(response);
  while (payload.status === "running" || payload.status === "cancelling") {
    await new Promise((resolve) => window.setTimeout(resolve, 200));
    const progress = await fetch(`/run/${encodeURIComponent(run.id)}/?after=-1`);
    payload = await readJsonResponse(progress);
  }
  if (payload.status === "failed") {
    throw new Error(payload.error || "The algorithm run failed.");
  }
}

async function pollRun(run, bruteForce) {
  let lastGeneration = -1;
  const totalGenerations = params.generations;
  const demonstrationNumbers = demonstrationGenerations(totalGenerations);
  const statusElement = document.getElementById("runStatus");

  while (true) {
    if (run.cancelRequested) {
      await cancelRun(run);
      setRunTime(bruteForce);
      statusElement.textContent = "Cancelled";
      document.getElementById("cancelButton").textContent = "Cancelled";
      return;
    }

    const response = await fetch(
      `/run/${encodeURIComponent(run.id)}/?after=${lastGeneration}`
    );
    const payload = await readJsonResponse(response);
    if (run.cancelRequested) continue;
    if (payload.status === "failed") {
      throw new Error(payload.error || "The algorithm run failed.");
    }
    if (payload.status === "cancelled") {
      setRunTime(bruteForce);
      statusElement.textContent = "Cancelled";
      document.getElementById("cancelButton").textContent = "Cancelled";
      return;
    }
    if (payload.status === "completed") {
      setRunTime(bruteForce, payload.elapsedMs);
    }

    for (const generation of payload.generations) {
      if (run.cancelRequested) break;
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
      if (!bruteForce && demonstrationNumbers.has(generation.number)) {
        await animateBoats(generation);
      }
      await new Promise((resolve) => window.requestAnimationFrame(resolve));
      if (bruteForce) {
        window.OnePath.setResults(
          { best: formatRoute(generation.best) },
          true
        );
        lineLayer.replaceChildren();
        drawRoute(generation.best.genes, "#16a34a", "best-route");
        statusElement.textContent =
          `Best tour update ${generation.number + 1} - best distance ` +
          `${generation.best.distance.toFixed(2)}`;
        await waitForPlayback(150, run.playback.signal);
      }
    }

    if (run.cancelRequested) continue;
    if (payload.status === "completed") {
      renderFinalRoutes();
      statusElement.textContent = bruteForce
        ? "Completed exhaustive search."
        : `Completed ${lastGeneration + 1} generations.`;
      return;
    }
    await waitForPlayback(200, run.playback.signal);
  }
}

async function handleRun(event) {
  if (activeRun) return;

  const panel = document.querySelector(".left");
  const statusElement = document.getElementById("runStatus");
  const cancelButton = document.getElementById("cancelButton");
  const controls = [...panel.querySelectorAll("input, select, textarea, button")]
    .filter((control) => control !== cancelButton);
  const previousDisabledStates = controls.map((control) => control.disabled);
  const previousPointerEvents = grid.style.pointerEvents;
  const { bruteForce } = event.detail.parameters;
  const run = {
    id: null,
    cancelRequested: false,
    playback: new AbortController(),
    csrfToken: document.querySelector("#csrfForm input[name=csrfmiddlewaretoken]").value,
  };
  activeRun = run;

  panel.classList.add("is-running");
  controls.forEach((control) => { control.disabled = true; });
  grid.style.pointerEvents = "none";
  cancelButton.hidden = false;
  cancelButton.disabled = false;
  cancelButton.textContent = "Cancel";
  statusElement.textContent = "Starting run…";
  window.OnePath.setResults({}, bruteForce);
  setRunTime(bruteForce, null, true);
  clearLines();
  completedGeneration = null;

  try {
    const response = await fetch("/run/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": run.csrfToken,
      },
      body: JSON.stringify(event.detail),
    });
    const payload = await readJsonResponse(response);
    run.id = payload.runId;
    await pollRun(run, bruteForce);
  } catch (error) {
    setRunTime(bruteForce);
    statusElement.textContent = `Run failed: ${error.message}`;
  } finally {
    run.playback.abort();
    activeRun = null;
    cancelButton.hidden = true;
    panel.classList.remove("is-running");
    controls.forEach((control, index) => {
      control.disabled = previousDisabledStates[index];
    });
    grid.style.pointerEvents = previousPointerEvents;
  }
}


const cells = createGrid();

onChange.islands = (count) => {
  clearLines();
  clearTiming();
  placeIslands(cells, count);
};

setupPanel();
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

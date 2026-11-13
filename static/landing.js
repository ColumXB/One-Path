const COLS = 50;
const ROWS = 30;
const SVG_NS = "http://www.w3.org/2000/svg";

const grid = document.getElementById("grid");
let lineLayer = null;
let selectedCell = null;
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

  return cells;
}

// Remove existing islands, then randomly pick different cells for the new ones.
function placeIslands(cells, count) {
  cells.forEach((cell) => {
    cell.classList.remove("island");
    delete cell.dataset.islandId;
  });

  const pool = [...cells];
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }

  pool.slice(0, count).forEach((cell, index) => {
    cell.classList.add("island");
    cell.dataset.islandId = String.fromCharCode(65 + index);
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
  if (selectedCell) selectedCell.classList.remove("selected");
  selectedCell = null;
}

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

function drawRoute(genes) {
  const cellsByIsland = new Map(
    [...document.querySelectorAll(".cell.island")]
      .map((cell) => [cell.dataset.islandId, cell])
  );
  const routeCells = [...genes].map((gene) => cellsByIsland.get(gene));
  if (routeCells.some((cell) => !cell)) {
    throw new Error("The generated route does not match the islands on the map.");
  }

  clearLines();
  routeCells.forEach((cell, index) => {
    connectCells(cell, routeCells[(index + 1) % routeCells.length]);
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
  const runStatus = document.getElementById("runStatus");
  const lastRunResults = document.getElementById("lastRunResults");
  const bruteResults = document.querySelector(".brute-result");
  const gaInputs = document.querySelectorAll("#gaSection .controls input");
  const syncMode = () => {
    sliderControls.islands.setLimit(
      brute.checked ? BRUTE_FORCE_LIMIT : Number(document.getElementById("islands-range").max)
    );
    ga.classList.toggle("is-off", brute.checked);
    gaInputs.forEach((input) => { input.disabled = brute.checked; });
    (brute.checked ? bruteResults : lastRunResults).append(runStatus);
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
      window.OnePath.setResults({
        best: formatRoute(generation.best),
        median: formatRoute(generation.median),
        worst: formatRoute(generation.worst),
      }, bruteForce);
      drawRoute(generation.best.genes);
      const step = bruteForce ? "Best tour update" : "Generation";
      statusElement.textContent =
        `${step} ${generation.number + 1} - best distance ${generation.best.distance.toFixed(2)}`;
      await waitForPlayback(bruteForce ? 150 : 16, run.playback.signal);
    }

    if (run.cancelRequested) continue;
    if (payload.status === "completed") {
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
  cancelButton.disabled = false;
  cancelButton.textContent = "Cancel";
  statusElement.textContent = "Starting run…";
  window.OnePath.setResults({}, bruteForce);
  setRunTime(bruteForce, null, true);
  clearLines();

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
    cancelButton.disabled = true;
    cancelButton.textContent = "Cancel";
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
document.addEventListener("onepath:run", handleRun);

grid.addEventListener("click", (event) => {
  const cell = event.target.closest(".cell");
  if (cell) handleCellClick(cell);
});

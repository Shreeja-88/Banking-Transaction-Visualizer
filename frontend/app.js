const DEFAULT_ACCOUNTS = {
  A: { id: "A", name: "Alice Sharma", type: "Savings", number: "4821", balance: 10000 },
  B: { id: "B", name: "Bob Mehta", type: "Current", number: "7394", balance: 8000 },
  C: { id: "C", name: "Carol Rao", type: "Salary", number: "1180", balance: 6000 },
  D: { id: "D", name: "Dev Patel", type: "Premium", number: "9042", balance: 15000 },
  E: { id: "E", name: "Enterprise Escrow", type: "Business", number: "6675", balance: 22000 },
  X: { id: "X", name: "Xavier Khan", type: "NRI", number: "5509", balance: 5000 },
};

const PRESETS = {
  "Core Banking Rush Hour": [
    ["T1", "read", "A", 0],
    ["T2", "transfer", "A", "B", 2200],
    ["T3", "read", "C", 0],
    ["T4", "withdraw", "B", 700],
    ["T5", "deposit", "A", 900],
    ["T6", "transfer", "C", "A", 1200],
    ["T7", "transfer", "D", "E", 5000],
    ["T3", "withdraw", "C", 800],
    ["T4", "read", "A", 0],
    ["T6", "deposit", "E", 600],
    ["T5", "transfer", "E", "B", 1300],
    ["T7", "read", "B", 0],
  ],
  "ATM + Mobile Conflict": [
    ["T1", "read", "A", 0],
    ["T2", "transfer", "A", "B", 3500],
    ["T1", "withdraw", "A", 2500],
    ["T2", "read", "B", 0],
  ],
  "Fund Transfer": [
    ["T1", "read", "A", 0],
    ["T1", "transfer", "A", "B", 1500],
    ["T2", "deposit", "C", 700],
    ["T3", "transfer", "B", "C", 900],
  ],
  "Unsafe Shared Account": [
    ["T1", "read", "A", 0],
    ["T2", "deposit", "A", 1000],
    ["T1", "withdraw", "A", 500],
    ["T2", "read", "A", 0],
  ],
  "Safe Schedule": [
    ["T1", "withdraw", "A", 1200],
    ["T2", "deposit", "B", 800],
    ["T3", "transfer", "C", "X", 600],
  ],
};

const QUIZ_SCENARIOS = [
  {
    schedule: [
      ["T1", "read", "A", 0],
      ["T2", "deposit", "A", 1000],
      ["T1", "withdraw", "A", 500],
    ],
    hint: "T1 reads A before T2 writes A, then T1 writes A after T2. The graph has T1->T2 and T2->T1.",
  },
  {
    schedule: [
      ["T1", "withdraw", "A", 1200],
      ["T2", "deposit", "B", 800],
      ["T3", "transfer", "C", "X", 600],
    ],
    hint: "The transactions write different accounts, so no cycle appears in the precedence graph.",
  },
  {
    schedule: [
      ["T1", "transfer", "A", "B", 500],
      ["T2", "read", "B", 0],
      ["T2", "withdraw", "B", 300],
    ],
    hint: "T1 must precede T2 on account B, but there is no edge back from T2 to T1.",
  },
];

const ACCOUNT_KEY = "btv.accounts";
const HISTORY_KEY = "btv.history";
const q = (id) => document.getElementById(id);

const els = {
  accountCards: q("accountCards"),
  accountSelect: q("accountSelect"),
  accountAmount: q("accountAmount"),
  depositBtn: q("depositBtn"),
  withdrawBtn: q("withdrawBtn"),
  resetAccountsBtn: q("resetAccountsBtn"),
  transferFrom: q("transferFrom"),
  transferTo: q("transferTo"),
  transferAmount: q("transferAmount"),
  transferBtn: q("transferBtn"),
  accountHistory: q("accountHistory"),
  presetSelect: q("presetSelect"),
  scheduleEditor: q("scheduleEditor"),
  runBtn: q("runBtn"),
  resetBtn: q("resetBtn"),
  rollbackBtn: q("rollbackBtn"),
  transactionList: q("transactionList"),
  executionLog: q("executionLog"),
  systemStatus: q("systemStatus"),
  ledgerVolume: q("ledgerVolume"),
  activeTxnCount: q("activeTxnCount"),
  conflictCount: q("conflictCount"),
  riskState: q("riskState"),
  stepMetric: q("stepMetric"),
  graphMetric: q("graphMetric"),
  conflictNote: q("conflictNote"),
  graphCanvas: q("graphCanvas"),
  quizQuestion: q("quizQuestion"),
  quizSafeBtn: q("quizSafeBtn"),
  quizUnsafeBtn: q("quizUnsafeBtn"),
  quizNextBtn: q("quizNextBtn"),
  quizScore: q("quizScore"),
  quizResult: q("quizResult"),
};

const money = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

let accounts = loadAccounts();
let history = loadHistory();
let checkpoint = null;
let currentSchedule = PRESETS["Core Banking Rush Hour"].map(stepFromTuple);
let animationTimer = null;
let animationIndex = 0;
let conflictRows = new Set();
let logs = [];
let quizIndex = 0;
let quizCorrect = 0;
let quizTotal = 0;

function init() {
  renderAccounts();
  renderHistory();
  updateOperationsSummary(currentSchedule);

  if (els.accountSelect) initAccountsPage();
  if (els.presetSelect) initGraphPage();
  if (els.quizQuestion) initQuizPage();

  window.addEventListener("resize", () => {
    if (els.graphCanvas) drawGraph(currentSchedule.slice(0, animationIndex || currentSchedule.length));
  });
}

function initAccountsPage() {
  fillAccountSelects();
  els.depositBtn.addEventListener("click", () => runAccountOperation("deposit"));
  els.withdrawBtn.addEventListener("click", () => runAccountOperation("withdraw"));
  els.resetAccountsBtn.addEventListener("click", resetAccounts);
  els.transferBtn.addEventListener("click", runTransfer);
  setStatus("Teller Ready", "safe");
}

function initGraphPage() {
  Object.keys(PRESETS).forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    els.presetSelect.appendChild(option);
  });

  els.presetSelect.addEventListener("change", () => loadPreset(els.presetSelect.value));
  els.runBtn.addEventListener("click", runAnimation);
  els.resetBtn.addEventListener("click", resetGraphPage);
  els.rollbackBtn.addEventListener("click", rollback);
  loadPreset("Core Banking Rush Hour");
}

function initQuizPage() {
  els.quizSafeBtn.addEventListener("click", () => answerQuiz("safe"));
  els.quizUnsafeBtn.addEventListener("click", () => answerQuiz("unsafe"));
  els.quizNextBtn.addEventListener("click", nextQuiz);
  loadQuiz();
  drawGraph([]);
  setStatus("Quiz Ready", "safe");
}

function cloneAccounts(source) {
  return Object.fromEntries(Object.entries(source).map(([id, account]) => [id, { ...account }]));
}

function loadAccounts() {
  try {
    const stored = JSON.parse(localStorage.getItem(ACCOUNT_KEY)) || {};
    return Object.fromEntries(
      Object.entries(DEFAULT_ACCOUNTS).map(([id, account]) => [
        id,
        { ...account, ...(stored[id] || {}) },
      ])
    );
  } catch {
    return cloneAccounts(DEFAULT_ACCOUNTS);
  }
}

function saveAccounts() {
  localStorage.setItem(ACCOUNT_KEY, JSON.stringify(accounts));
}

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
  } catch {
    return [];
  }
}

function addHistory(line) {
  history.unshift(`${new Date().toLocaleTimeString()}  ${line}`);
  history = history.slice(0, 40);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  renderHistory();
}

function fillAccountSelects() {
  [els.accountSelect, els.transferFrom, els.transferTo].filter(Boolean).forEach((select) => {
    select.replaceChildren();
    Object.values(accounts).forEach((account) => {
      const option = document.createElement("option");
      option.value = account.id;
      option.textContent = `${account.id} - ${account.name}`;
      select.appendChild(option);
    });
  });
  if (els.transferTo) els.transferTo.value = "B";
}

function renderAccounts() {
  if (!els.accountCards) return;
  els.accountCards.replaceChildren();
  Object.values(accounts).forEach((account) => {
    const card = document.createElement("article");
    card.className = "account-card";
    card.innerHTML = `
      <div class="account-id"><span>Account ${account.id}</span><span>${account.type}</span></div>
      <div class="account-name">${account.name}</div>
      <div class="account-meta">A/C **** ${account.number} | RBI insured ledger</div>
      <div class="account-balance">${money.format(account.balance)}</div>
    `;
    els.accountCards.appendChild(card);
  });
}

function renderHistory() {
  if (!els.accountHistory) return;
  els.accountHistory.textContent = history.length ? history.join("\n") : "No account operations yet.";
}

function runAccountOperation(type) {
  const id = els.accountSelect.value;
  const amount = Number(els.accountAmount.value);
  if (!Number.isFinite(amount) || amount <= 0) return setStatus("Enter a valid amount", "unsafe");

  const account = accounts[id];
  if (type === "withdraw" && account.balance < amount) {
    return setStatus("Insufficient Balance", "unsafe");
  }

  account.balance += type === "deposit" ? amount : -amount;
  saveAccounts();
  renderAccounts();
  addHistory(`${type.toUpperCase()} ${account.id} ${money.format(amount)} | Balance ${money.format(account.balance)}`);
  setStatus(`${type === "deposit" ? "Deposit" : "Withdrawal"} Posted`, "safe");
}

function runTransfer() {
  const from = accounts[els.transferFrom.value];
  const to = accounts[els.transferTo.value];
  const amount = Number(els.transferAmount.value);
  if (from.id === to.id) return setStatus("Choose two accounts", "unsafe");
  if (!Number.isFinite(amount) || amount <= 0) return setStatus("Enter a valid amount", "unsafe");
  if (from.balance < amount) return setStatus("Insufficient Balance", "unsafe");

  from.balance -= amount;
  to.balance += amount;
  saveAccounts();
  renderAccounts();
  addHistory(`TRANSFER ${from.id}->${to.id} ${money.format(amount)} | ${from.id} ${money.format(from.balance)}, ${to.id} ${money.format(to.balance)}`);
  setStatus("Transfer Settled", "safe");
}

function resetAccounts() {
  accounts = cloneAccounts(DEFAULT_ACCOUNTS);
  history = [];
  localStorage.removeItem(ACCOUNT_KEY);
  localStorage.removeItem(HISTORY_KEY);
  fillAccountSelects();
  renderAccounts();
  renderHistory();
  setStatus("Accounts Reset", "safe");
}

function stepFromTuple(tuple) {
  const [tid, op, account, fourth = 0, fifth = 0] = tuple;
  if (op === "transfer") {
    return { tid, op, account, target: fourth, amount: Number(fifth) || 0 };
  }
  return { tid, op, account, amount: Number(fourth) || 0 };
}

function presetToText(steps) {
  return steps.map((tuple) => {
    const step = stepFromTuple(tuple);
    return step.op === "transfer"
      ? `${step.tid}  transfer  ${step.account}  ${step.target}  ${step.amount}`
      : `${step.tid}  ${step.op}  ${step.account}  ${step.amount}`;
  }).join("\n");
}

function loadPreset(name) {
  cancelAnimation();
  els.presetSelect.value = name;
  currentSchedule = PRESETS[name].map(stepFromTuple);
  animationIndex = currentSchedule.length;
  conflictRows = new Set();
  logs = [];
  els.scheduleEditor.value = presetToText(PRESETS[name]);
  renderTransactions(currentSchedule);
  drawGraph(currentSchedule);
  updateLog("Schedule loaded. Graph preview is ready; run animation for live execution.");
  setStatus("Schedule Loaded", "safe");
}

function parseSchedule() {
  const lines = els.scheduleEditor.value.trim().split(/\n+/).filter(Boolean);
  return lines.map((line, index) => {
    const parts = line.trim().split(/\s+/);
    if (parts.length < 3) throw new Error(`Line ${index + 1}: expected TID OP ACCOUNT.`);

    const [tid, opRaw, accountRaw, fourth = "0", fifth = "0"] = parts;
    const op = opRaw.toLowerCase();
    if (!["read", "write", "deposit", "withdraw", "transfer"].includes(op)) {
      throw new Error(`Line ${index + 1}: invalid operation.`);
    }

    if (op === "transfer") {
      const amount = Number(fifth);
      if (parts.length < 5 || !Number.isFinite(amount) || amount <= 0) {
        throw new Error(`Line ${index + 1}: transfer needs FROM TO AMOUNT.`);
      }
      return { tid: tid.toUpperCase(), op, account: accountRaw.toUpperCase(), target: fourth.toUpperCase(), amount };
    }

    const amount = Number(fourth);
    if (!Number.isFinite(amount)) throw new Error(`Line ${index + 1}: amount must be numeric.`);
    if ((op === "deposit" || op === "withdraw") && amount <= 0) {
      throw new Error(`Line ${index + 1}: amount must be positive.`);
    }
    return { tid: tid.toUpperCase(), op, account: accountRaw.toUpperCase(), amount };
  });
}

function runAnimation() {
  cancelAnimation();
  try {
    currentSchedule = parseSchedule();
  } catch (error) {
    return setStatus(error.message, "unsafe");
  }

  checkpoint = cloneAccounts(accounts);
  animationIndex = 0;
  conflictRows = getConflictIndexes(currentSchedule);
  logs = ["============================================", " EXECUTING BANKING SCHEDULE", "============================================"];
  renderTransactions(currentSchedule);
  updateLog(logs.join("\n"));
  drawGraph([]);
  els.runBtn.disabled = true;
  setStatus("Running", "safe");
  animateNextStep();
}

function animateNextStep() {
  if (animationIndex >= currentSchedule.length) return finishAnimation();
  const index = animationIndex;
  setTransactionState(index, "active");
  drawGraph(currentSchedule.slice(0, index + 1));
  if (els.stepMetric) els.stepMetric.textContent = `${index + 1} / ${currentSchedule.length}`;
  animationTimer = window.setTimeout(() => commitStep(index), 650);
}

function commitStep(index) {
  const step = currentSchedule[index];
  logs.push(applyStep(step));
  updateLog(logs.join("\n"));
  renderAccounts();
  setTransactionState(index, conflictRows.has(index) ? "conflict" : "done");
  animationIndex += 1;
  animationTimer = window.setTimeout(animateNextStep, 300);
}

function finishAnimation() {
  cancelAnimation();
  saveAccounts();
  const result = evaluateSchedule(currentSchedule);
  logs.push("");
  logs.push("--------------------------------------------");
  logs.push(` CONFLICTS DETECTED: ${result.conflicts.length}`);
  result.conflicts.forEach((item) => logs.push(`  ${item.from} -> ${item.to} on ${item.account} [${item.reason}]`));
  logs.push("");
  logs.push(result.safe ? " SCHEDULE IS SAFE" : ` CYCLE DETECTED: ${result.cycle.join(" -> ")}`);
  logs.push(result.safe ? " NO ROLLBACK REQUIRED" : " ROLLBACK RECOMMENDED");
  logs.push("============================================");
  updateLog(logs.join("\n"));
  drawGraph(currentSchedule);
  setStatus(result.safe ? "Safe Schedule" : "Unsafe Schedule", result.safe ? "safe" : "unsafe");
  if (els.conflictNote) {
    els.conflictNote.textContent = result.conflicts.length
      ? `${result.conflicts.length} conflict edge(s): ${result.conflicts.map((item) => `${item.from}->${item.to} on ${item.account}`).join(", ")}`
      : "No conflicts: the precedence graph has no dependency edges.";
    els.conflictNote.style.borderColor = result.safe ? "var(--emerald)" : "var(--burgundy)";
  }
}

function applyStep(step) {
  const account = accounts[step.account];
  if (!account) return `[ERROR] ${step.tid}: Account ${step.account} not found.`;
  if (step.op === "read") return `[${step.tid}] READ ${step.account}: ${money.format(account.balance)}`;

  if (step.op === "transfer") {
    const target = accounts[step.target];
    if (!target) return `[ERROR] ${step.tid}: Account ${step.target} not found.`;
    if (account.balance < step.amount) return `[${step.tid}] ERROR ${step.account}: insufficient balance.`;
    account.balance -= step.amount;
    target.balance += step.amount;
    return `[${step.tid}] TRANSFER ${step.account}->${step.target}: ${money.format(step.amount)}`;
  }

  if (step.op === "deposit" || (step.op === "write" && step.amount > 0)) {
    account.balance += step.amount;
    return `[${step.tid}] DEPOSIT ${step.account}: +${money.format(step.amount)}`;
  }

  const withdrawal = step.op === "withdraw" ? step.amount : Math.abs(step.amount);
  if (account.balance < withdrawal) return `[${step.tid}] ERROR ${step.account}: insufficient balance.`;
  account.balance -= withdrawal;
  return `[${step.tid}] WITHDRAW ${step.account}: -${money.format(withdrawal)}`;
}

function resetGraphPage() {
  cancelAnimation();
  accounts = cloneAccounts(DEFAULT_ACCOUNTS);
  saveAccounts();
  renderAccounts();
  loadPreset(els.presetSelect.value || "Core Banking Rush Hour");
  setStatus("Reset Complete", "safe");
}

function rollback() {
  cancelAnimation();
  if (!checkpoint) {
    updateLog(`${els.executionLog.textContent}\n[ROLLBACK]\nNo checkpoint available.`);
    return setStatus("No Checkpoint", "unsafe");
  }
  accounts = cloneAccounts(checkpoint);
  saveAccounts();
  renderAccounts();
  renderTransactions(currentSchedule);
  drawGraph(currentSchedule);
  updateLog(`${els.executionLog.textContent}\n[ROLLBACK]\nBalances restored to previous checkpoint.`);
  setStatus("Rolled Back", "safe");
}

function cancelAnimation() {
  if (animationTimer) window.clearTimeout(animationTimer);
  animationTimer = null;
  if (els.runBtn) els.runBtn.disabled = false;
}

function renderTransactions(schedule) {
  if (!els.transactionList) return;
  els.transactionList.replaceChildren();
  if (els.stepMetric) els.stepMetric.textContent = `0 / ${schedule.length}`;
  schedule.forEach((step, index) => {
    const row = document.createElement("article");
    row.className = "transaction-row";
    row.dataset.index = String(index);
    row.innerHTML = `
      <div class="row-status">WAIT</div>
      <div class="row-main">${String(index + 1).padStart(2, "0")} ${step.tid} ${step.op.toUpperCase()} | ${channelForStep(step, index)}</div>
      <div class="row-meta">${formatStepMeta(step)}</div>
    `;
    els.transactionList.appendChild(row);
  });
}

function setTransactionState(index, state) {
  if (!els.transactionList) return;
  const row = els.transactionList.querySelector(`[data-index="${index}"]`);
  if (!row) return;
  row.classList.remove("is-active", "is-done", "has-conflict");
  const status = row.querySelector(".row-status");
  if (state === "active") {
    row.classList.add("is-active");
    status.textContent = "RUN";
  }
  if (state === "done") {
    row.classList.add("is-done");
    status.textContent = "DONE";
  }
  if (state === "conflict") {
    row.classList.add("has-conflict");
    status.textContent = "EDGE";
  }
  row.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function formatStepMeta(step) {
  if (step.op === "transfer") return `${step.account}->${step.target} ${money.format(step.amount)}`;
  if (step.op === "withdraw") return `${step.account} -${money.format(step.amount)}`;
  if (step.op === "deposit") return `${step.account} +${money.format(step.amount)}`;
  return `${step.account} ${step.amount || 0}`;
}

function channelForStep(step, index) {
  if (step.op === "transfer") return index % 2 === 0 ? "IMPS" : "Mobile";
  if (step.op === "withdraw") return "ATM";
  if (step.op === "deposit") return "Branch";
  return "Balance API";
}

function updateLog(text) {
  if (!els.executionLog) return;
  els.executionLog.textContent = text;
  els.executionLog.scrollTop = els.executionLog.scrollHeight;
}

function setStatus(text, type) {
  if (!els.systemStatus) return;
  els.systemStatus.textContent = text;
  els.systemStatus.classList.toggle("is-safe", type === "safe");
  els.systemStatus.classList.toggle("is-unsafe", type === "unsafe");
}

function loadQuiz() {
  const scenario = QUIZ_SCENARIOS[quizIndex % QUIZ_SCENARIOS.length];
  currentSchedule = scenario.schedule.map(stepFromTuple);
  els.quizQuestion.textContent = currentSchedule.map((step, index) =>
    `${String(index + 1).padStart(2, "0")}  ${step.tid}  ${step.op.toUpperCase()}  ${formatStepMeta(step)}`
  ).join("\n");
  els.quizResult.textContent = "Pick an answer to reveal the graph result.";
  els.quizResult.style.borderColor = "var(--gold)";
  els.quizScore.textContent = `${quizCorrect} / ${quizTotal}`;
  drawGraph([]);
}

function answerQuiz(answer) {
  const result = evaluateSchedule(currentSchedule);
  const correct = result.safe ? "safe" : "unsafe";
  quizTotal += 1;
  if (answer === correct) {
    quizCorrect += 1;
    els.quizResult.textContent = `Correct. ${QUIZ_SCENARIOS[quizIndex % QUIZ_SCENARIOS.length].hint}`;
    els.quizResult.style.borderColor = "var(--emerald)";
  } else {
    els.quizResult.textContent = `Wrong. Correct answer: ${correct.toUpperCase()}. ${QUIZ_SCENARIOS[quizIndex % QUIZ_SCENARIOS.length].hint}`;
    els.quizResult.style.borderColor = "var(--burgundy)";
  }
  els.quizScore.textContent = `${quizCorrect} / ${quizTotal}`;
  drawGraph(currentSchedule);
  setStatus(result.safe ? "Safe" : "Unsafe", result.safe ? "safe" : "unsafe");
}

function nextQuiz() {
  quizIndex += 1;
  loadQuiz();
  setStatus("Quiz Ready", "safe");
}

function touchedAccounts(step) {
  return step.op === "transfer" ? [step.account, step.target] : [step.account];
}

function writesData(step) {
  return step.op !== "read";
}

function detectConflicts(schedule) {
  const conflicts = [];
  for (let i = 0; i < schedule.length; i += 1) {
    for (let j = i + 1; j < schedule.length; j += 1) {
      const first = schedule[i];
      const second = schedule[j];
      if (first.tid === second.tid) continue;
      const shared = touchedAccounts(first).filter((account) => touchedAccounts(second).includes(account));
      if (!shared.length || (!writesData(first) && !writesData(second))) continue;
      shared.forEach((account) => {
        conflicts.push({
          from: first.tid,
          to: second.tid,
          account,
          reason: `${first.op.toUpperCase()}(${account}) vs ${second.op.toUpperCase()}(${account})`,
          sourceIndex: i,
          targetIndex: j,
        });
      });
    }
  }
  return conflicts;
}

function getConflictIndexes(schedule) {
  const indexes = new Set();
  detectConflicts(schedule).forEach((item) => {
    indexes.add(item.sourceIndex);
    indexes.add(item.targetIndex);
  });
  return indexes;
}

function buildGraph(schedule, conflicts) {
  const nodes = [...new Set(schedule.map((step) => step.tid))];
  const adjacency = Object.fromEntries(nodes.map((node) => [node, []]));
  const seen = new Set();
  conflicts.forEach((edge) => {
    const key = `${edge.from}->${edge.to}`;
    if (!seen.has(key)) {
      adjacency[edge.from].push(edge.to);
      seen.add(key);
    }
  });
  return { nodes, edges: conflicts, adjacency };
}

function findCycle(graph) {
  const visited = new Set();
  const active = new Set();
  const stack = [];
  function visit(node) {
    visited.add(node);
    active.add(node);
    stack.push(node);
    for (const next of graph.adjacency[node] || []) {
      if (!visited.has(next)) {
        const found = visit(next);
        if (found.length) return found;
      } else if (active.has(next)) {
        return stack.slice(stack.indexOf(next)).concat(next);
      }
    }
    active.delete(node);
    stack.pop();
    return [];
  }
  for (const node of graph.nodes) {
    if (!visited.has(node)) {
      const found = visit(node);
      if (found.length) return found;
    }
  }
  return [];
}

function evaluateSchedule(schedule) {
  const conflicts = detectConflicts(schedule);
  const graph = buildGraph(schedule, conflicts);
  const cycle = findCycle(graph);
  return { conflicts, graph, cycle, safe: cycle.length === 0 };
}

function updateOperationsSummary(schedule) {
  if (!els.ledgerVolume) return;
  const result = evaluateSchedule(schedule);
  const volume = schedule.reduce((sum, step) => step.op === "read" ? sum : sum + Math.abs(step.amount || 0), 0);
  els.ledgerVolume.textContent = money.format(volume);
  els.activeTxnCount.textContent = String(new Set(schedule.map((step) => step.tid)).size);
  els.conflictCount.textContent = String(result.conflicts.length);
  els.riskState.textContent = result.safe ? (result.conflicts.length ? "Review" : "Cleared") : "Unsafe";
}

function drawGraph(schedule) {
  if (!els.graphCanvas) return updateOperationsSummary(schedule);
  const canvas = els.graphCanvas;
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);

  const width = rect.width;
  const height = rect.height;
  ctx.clearRect(0, 0, width, height);
  paintGraphBackground(ctx, width, height);

  const result = evaluateSchedule(schedule);
  updateOperationsSummary(schedule);
  if (els.graphMetric) {
    els.graphMetric.textContent = result.safe ? "Safe" : "Unsafe";
    els.graphMetric.classList.toggle("is-safe", result.safe);
    els.graphMetric.classList.toggle("is-unsafe", !result.safe);
  }

  if (!result.graph.nodes.length) {
    drawCenteredText(ctx, width, height, "Graph waiting for transactions", "Load or run a schedule");
    return;
  }

  const positions = getNodePositions(result.graph.nodes, width, height);
  const edgeColor = result.safe ? "#0f6f61" : "#8f263e";
  result.graph.edges.forEach((edge, index) => {
    const from = positions[edge.from];
    const to = positions[edge.to];
    if (from && to) drawArrow(ctx, from, to, edgeColor, edge.account, index);
  });
  result.graph.nodes.forEach((node) => drawNode(ctx, positions[node].x, positions[node].y, node, result.safe));
  drawCaption(ctx, width, height, result.safe ? "No cycle found" : `Cycle: ${result.cycle.join(" -> ")}`, `${result.conflicts.length} conflict edge(s)`, result.safe);
}

function paintGraphBackground(ctx, width, height) {
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "#fffdf8");
  gradient.addColorStop(1, "#f4e6ce");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(185, 139, 50, 0.14)";
  ctx.lineWidth = 1;
  for (let x = 40; x < width; x += 80) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 40; y < height; y += 80) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
}

function getNodePositions(nodes, width, height) {
  const centerX = width / 2;
  const centerY = height / 2 - 8;
  const radius = Math.max(100, Math.min(width, height) * 0.34);
  const positions = {};
  nodes.forEach((node, index) => {
    const angle = -Math.PI / 2 + (index / nodes.length) * Math.PI * 2;
    positions[node] = {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
    };
  });
  return positions;
}

function drawArrow(ctx, from, to, color, label, index) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const angle = Math.atan2(dy, dx);
  const nodeRadius = 40;
  const startX = from.x + Math.cos(angle) * nodeRadius;
  const startY = from.y + Math.sin(angle) * nodeRadius;
  const endX = to.x - Math.cos(angle) * nodeRadius;
  const endY = to.y - Math.sin(angle) * nodeRadius;
  const curve = index % 2 === 0 ? 22 : -22;
  const midX = (startX + endX) / 2 - Math.sin(angle) * curve;
  const midY = (startY + endY) / 2 + Math.cos(angle) * curve;
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(startX, startY);
  ctx.quadraticCurveTo(midX, midY, endX, endY);
  ctx.stroke();
  ctx.save();
  ctx.translate(endX, endY);
  ctx.rotate(angle);
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(-14, -8);
  ctx.lineTo(-14, 8);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
  ctx.font = "800 15px Inter, Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.fillStyle = "#3a2d23";
  ctx.fillText(label, midX, midY - 14);
}

function drawNode(ctx, x, y, label, safe) {
  ctx.beginPath();
  ctx.arc(x, y, 48, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(185, 139, 50, 0.22)";
  ctx.fill();
  ctx.beginPath();
  ctx.arc(x, y, 40, 0, Math.PI * 2);
  ctx.fillStyle = safe ? "#0f6f61" : "#8f263e";
  ctx.fill();
  ctx.strokeStyle = "#b98b32";
  ctx.lineWidth = 3;
  ctx.stroke();
  ctx.fillStyle = "#fffaf1";
  ctx.font = "900 22px Inter, Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(label, x, y);
}

function drawCaption(ctx, width, height, lineOne, lineTwo, safe) {
  ctx.fillStyle = safe ? "#0f6f61" : "#8f263e";
  ctx.font = "900 20px Inter, Segoe UI, sans-serif";
  ctx.textAlign = "left";
  ctx.fillText(lineOne, 24, height - 44);
  ctx.fillStyle = "#72685a";
  ctx.font = "800 16px Inter, Segoe UI, sans-serif";
  ctx.fillText(lineTwo, 24, height - 20);
}

function drawCenteredText(ctx, width, height, lineOne, lineTwo) {
  ctx.fillStyle = "#3a2d23";
  ctx.font = "900 24px Inter, Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(lineOne, width / 2, height / 2 - 16);
  ctx.fillStyle = "#72685a";
  ctx.font = "800 17px Inter, Segoe UI, sans-serif";
  ctx.fillText(lineTwo, width / 2, height / 2 + 20);
}

init();

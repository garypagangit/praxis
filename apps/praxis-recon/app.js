const STORAGE_KEY = "praxisReconState.v2";

const stageGroups = [
  {
    title: "Discovery",
    states: ["DISCOVERED", "REVIEWING", "REVIEWED"],
  },
  {
    title: "Ideation",
    states: ["IDEATING", "IDEAS_READY", "IDEA_SELECTED"],
  },
  {
    title: "Design",
    states: ["DESIGNING", "PLAN_READY", "EXPORTED"],
  },
  {
    title: "Execution",
    states: ["QUEUED_FOR_RUN", "EXECUTING", "EVALUATING"],
  },
  {
    title: "Publishing",
    states: ["RESULT_POSITIVE", "RESULT_NEGATIVE", "DEFENSIBILITY_CHECK", "PACKAGE_READY", "PUBLISHED_GIT", "ARCHIVED"],
  },
];

const nextStage = {
  DISCOVERED: "REVIEWING",
  REVIEWING: "REVIEWED",
  REVIEWED: "IDEATING",
  IDEATING: "IDEAS_READY",
  IDEAS_READY: "IDEA_SELECTED",
  IDEA_SELECTED: "DESIGNING",
  DESIGNING: "PLAN_READY",
  PLAN_READY: "QUEUED_FOR_RUN",
  QUEUED_FOR_RUN: "EXECUTING",
  EXECUTING: "EVALUATING",
  EVALUATING: "DEFENSIBILITY_CHECK",
  DEFENSIBILITY_CHECK: "PACKAGE_READY",
  PACKAGE_READY: "PUBLISHED_GIT",
};

const stateLabels = {
  DISCOVERED: "Discovered",
  REVIEWING: "Reviewing",
  REVIEWED: "Reviewed",
  IDEATING: "Ideating",
  IDEAS_READY: "Ideas ready",
  IDEA_SELECTED: "Idea selected",
  DESIGNING: "Designing",
  PLAN_READY: "Plan ready",
  EXPORTED: "Exported",
  QUEUED_FOR_RUN: "Queued",
  EXECUTING: "Executing",
  EVALUATING: "Evaluating",
  RESULT_POSITIVE: "Positive",
  RESULT_NEGATIVE: "Negative",
  DEFENSIBILITY_CHECK: "Defense gate",
  PACKAGE_READY: "Package ready",
  PUBLISHED_GIT: "Published",
  ARCHIVED: "Archived",
};

const seedState = {
  settings: {
    budgetCap: 500,
    budgetUsed: 146.8,
    gates: [
      { name: "Idea selection", mode: "Auto top scored", waiting: 0 },
      { name: "Defensibility", mode: "Human confirm", waiting: 3 },
      { name: "Publish approval", mode: "Human confirm", waiting: 2 },
    ],
  },
  topics: [
    {
      id: "topic_agent_defense",
      name: "Agentic deployment defenses",
      dailyCap: 35,
      peerReviewedOnly: true,
      includePreprints: true,
      active: true,
      sources: ["USENIX", "arXiv", "OpenAlex"],
      discovered: 24,
    },
    {
      id: "topic_cyber_ml",
      name: "Cyber ML and CTI",
      dailyCap: 50,
      peerReviewedOnly: true,
      includePreprints: false,
      active: true,
      sources: ["OpenAlex", "Crossref", "Semantic Scholar"],
      discovered: 42,
    },
    {
      id: "topic_mech_interp",
      name: "Mechanistic safety",
      dailyCap: 25,
      peerReviewedOnly: false,
      includePreprints: true,
      active: true,
      sources: ["arXiv", "OpenReview"],
      discovered: 18,
    },
  ],
  workItems: [
    {
      id: "wi_px050",
      title: "Package hallucination survives tool-using agents",
      topic: "Agentic deployment defenses",
      state: "PACKAGE_READY",
      kind: "experiment",
      venue: "USENIX Security line",
      source: "Package hallucination analysis",
      priority: "Lead",
      abstractOnly: false,
      defensibility: 5,
      cost: 61.4,
      updatedAt: "2026-07-06 09:10",
      overview: "Deterministic PyPI/NPM install validation blocked invalid dry-run tool-call arguments before execution.",
    },
    {
      id: "wi_px054",
      title: "Refusal geometry across recurrent depth",
      topic: "Mechanistic safety",
      state: "DEFENSIBILITY_CHECK",
      kind: "experiment",
      venue: "arXiv",
      source: "Huginn recurrent-depth transformer",
      priority: "High",
      abstractOnly: false,
      defensibility: 4,
      cost: 38.2,
      updatedAt: "2026-07-06 08:52",
      overview: "Safe prompt activations show stable depth-indexed refusal-style direction in Huginn-0125.",
    },
    {
      id: "wi_px055",
      title: "Refusal-direction geometry under quantization",
      topic: "Mechanistic safety",
      state: "QUEUED_FOR_RUN",
      kind: "experiment",
      venue: "Source-gate candidate",
      source: "Post-training quantization refusal-direction protocol",
      priority: "Deconflict first",
      abstractOnly: false,
      defensibility: 3,
      cost: 0,
      updatedAt: "2026-07-11 23:23",
      overview: "Gate 0A rescope/proceed; local preflight blocked by missing GPU ML stack; cloud FP16/int8/NF4 hook smoke is ready.",
    },
    {
      id: "wi_px056",
      title: "Model registry identifier hallucination",
      topic: "Agentic deployment defenses",
      state: "GATE_READY",
      kind: "experiment",
      venue: "HF Hub / NGC catalog",
      source: "HF Hub / NGC model registry verification",
      priority: "High",
      abstractOnly: false,
      defensibility: 4,
      cost: 0,
      updatedAt: "2026-07-21 18:56",
      overview: "PX-056 is the model/dataset registry extension of PX-050. Gate 0 now passes HF+NGC readiness, and Gate 1 passed the controlled extractor/verifier pilot.",
    },
    {
      id: "wi_px003",
      title: "ATT&CK relationship evidence for CTI compliance",
      topic: "Cyber ML and CTI",
      state: "PACKAGE_READY",
      kind: "experiment",
      venue: "CTIBench / MITRE ATT&CK",
      source: "CTI-MCQ relationship evidence",
      priority: "High",
      abstractOnly: false,
      defensibility: 5,
      cost: 94.7,
      updatedAt: "2026-07-05 21:35",
      overview: "Per-question ATT&CK relationship evidence improves strict CTI answer compliance across model families.",
    },
    {
      id: "wi_pkg_fresh",
      title: "Adaptive evaluation of deterministic agent gates",
      topic: "Agentic deployment defenses",
      state: "PLAN_READY",
      kind: "idea",
      venue: "Future-work candidate",
      source: "Agent defense deconfliction",
      priority: "High ceiling",
      abstractOnly: false,
      defensibility: 4,
      cost: 0,
      updatedAt: "2026-07-06 07:40",
      overview: "Adversarially optimize prompts against deterministic gates and compare escape/utility curves.",
    },
    {
      id: "wi_falsecite",
      title: "Software artifact citation poisoning",
      topic: "Agentic deployment defenses",
      state: "PUBLISHED_GIT",
      kind: "package",
      venue: "Citation hallucination",
      source: "FalseCite-Code",
      priority: "Support",
      abstractOnly: false,
      defensibility: 4,
      cost: 22.5,
      updatedAt: "2026-07-04 18:30",
      overview: "External metadata verifier reduces fabricated software-artifact citation trust to zero on locked benchmark.",
    },
    {
      id: "wi_new_paper",
      title: "Open sparse MoE routing audit transfer",
      topic: "Mechanistic safety",
      state: "REVIEWED",
      kind: "paper",
      venue: "ACL / arXiv",
      source: "Standing Committee literature",
      priority: "Medium",
      abstractOnly: false,
      defensibility: 3,
      cost: 2.8,
      updatedAt: "2026-07-06 06:12",
      overview: "Review complete; novelty boundary suggests confirmatory extension rather than first-discovery claim.",
    },
  ],
  papers: [
    {
      id: "paper_001",
      title: "We Have a Package for You: A Comprehensive Analysis of Package Hallucinations by Code Generating LLMs",
      topic: "Agentic deployment defenses",
      source: "USENIX Security",
      published: "2025",
      state: "REVIEWED",
      evidenceStrength: "strong",
      novelty: "Reusable baseline for package-install hallucination defenses.",
      abstractOnly: false,
    },
    {
      id: "paper_002",
      title: "CTIBench: A Benchmark for Evaluating LLMs in Cyber Threat Intelligence",
      topic: "Cyber ML and CTI",
      source: "arXiv",
      published: "2024",
      state: "IDEAS_READY",
      evidenceStrength: "moderate",
      novelty: "Evaluation substrate for strict CTI answer compliance.",
      abstractOnly: false,
    },
    {
      id: "paper_003",
      title: "Scaling Up Test-Time Compute with Latent Reasoning",
      topic: "Mechanistic safety",
      source: "arXiv",
      published: "2025",
      state: "PLAN_READY",
      evidenceStrength: "moderate",
      novelty: "Recurrent depth creates a white-box activation capture opportunity.",
      abstractOnly: false,
    },
    {
      id: "paper_005",
      title: "Towards Understanding and Improving Refusal in Compressed Models via Mechanistic Interpretability",
      topic: "Mechanistic safety",
      source: "arXiv",
      published: "2025",
      state: "REVIEWED",
      evidenceStrength: "strong",
      novelty: "Direct overlap for PX-055; forces the quantization experiment to be an extension rather than a first-of-kind direction claim.",
      abstractOnly: false,
    },
    {
      id: "paper_006",
      title: "Model and Package Identifier Hallucination in Code-Generating LLMs",
      topic: "Agentic deployment defenses",
      source: "USENIX / arXiv / registry APIs",
      published: "2025-2026",
      state: "PLAN_READY",
      evidenceStrength: "moderate",
      novelty: "Extends package-hallucination defenses from package managers to model and dataset registries used in physical-AI code.",
      abstractOnly: false,
    },
    {
      id: "paper_004",
      title: "The Illusion of Specialization in Mixture-of-Experts Models",
      topic: "Mechanistic safety",
      source: "ACL / arXiv",
      published: "2026",
      state: "REVIEWED",
      evidenceStrength: "strong",
      novelty: "Standing Committee framing requires local novelty boundary.",
      abstractOnly: false,
    },
  ],
  ideas: [
    {
      id: "idea_001",
      paperId: "paper_001",
      title: "Package hallucination under agentic deployment plus verifier",
      oneLiner: "Measure whether package hallucination survives tool-using agents, then quantify deterministic gate recovery.",
      feasibility: 5,
      impact: 5,
      defensibility: 5,
      type: "computational",
      status: "selected",
      risks: ["Reads incremental unless held-out prompt families are added."],
    },
    {
      id: "idea_002",
      paperId: "paper_001",
      title: "Security-utility Pareto for agent gates",
      oneLiner: "Set gate strictness by consequence of pending action and publish operating-point curves.",
      feasibility: 4,
      impact: 4,
      defensibility: 4,
      type: "data_analysis",
      status: "ready",
      risks: ["Needs clear utility proxy and deployment consequence taxonomy."],
    },
    {
      id: "idea_003",
      paperId: "paper_003",
      title: "Refusal geometry across recurrent depth",
      oneLiner: "Capture safe prompt activations across recurrent steps and test stability of refusal-style directions.",
      feasibility: 4,
      impact: 4,
      defensibility: 4,
      type: "computational",
      status: "selected",
      risks: ["Must avoid causal safety claims without intervention tests."],
    },
    {
      id: "idea_005",
      paperId: "paper_005",
      title: "Refusal-direction geometry under post-training quantization",
      oneLiner: "Test whether quantization preserves, rotates, attenuates, or spreads refusal-style directions across model families.",
      feasibility: 3,
      impact: 4,
      defensibility: 3,
      type: "computational",
      status: "ready",
      risks: ["Existing compressed-model refusal-direction work overlaps; Gate 0 must prove a narrower extension before GPU spend."],
    },
    {
      id: "idea_006",
      paperId: "paper_006",
      title: "Model registry identifier hallucination",
      oneLiner: "Measure whether code LLMs hallucinate Hugging Face model/dataset identifiers in physical-AI code and whether deterministic registry gates close the surface.",
      feasibility: 4,
      impact: 4,
      defensibility: 4,
      type: "computational",
      status: "selected",
      risks: ["HF tokened scoring is required for 401/403 disambiguation; NGC remains conditional until a stable API path is pinned."],
    },
    {
      id: "idea_004",
      paperId: "paper_004",
      title: "Standing-committee transfer audit",
      oneLiner: "Repeat frozen router audit across model families and publish only as confirmation or extension.",
      feasibility: 4,
      impact: 3,
      defensibility: 4,
      type: "computational",
      status: "ready",
      risks: ["Novelty boundary must cite existing Standing Committee work."],
    },
  ],
  experiments: [
    {
      id: "exp_px050",
      ideaId: "idea_001",
      title: "Deterministic Tool-Boundary Gates for Package-Install Hallucination",
      status: "completed",
      positiveResult: true,
      primaryMetric: "hardened invalid allows",
      value: "0 / 288",
      successCriteria: "Zero hardened invalid allows and valid allow 1.0000 on dry-run live-agent corpus.",
      proof: "The tool-boundary verifier blocked invalid PyPI/NPM tool-call arguments before execution while preserving valid installs.",
      artifacts: ["PX050_FINAL_DEFENSE_PACKAGE_EXPORT_20260705.md", "combined_live_agent_tool_calls.csv"],
    },
    {
      id: "exp_px054",
      ideaId: "idea_003",
      title: "Depth-Indexed Refusal-Style Geometry",
      status: "defensibility_check",
      positiveResult: true,
      primaryMetric: "cross-depth stability",
      value: "0.9257",
      successCriteria: "Stable direction, benign-control FPR 0.0000, full activation capture.",
      proof: "Huginn-0125 exposes stable, measurable refusal-style latent direction across safe recurrent-depth prompts.",
      artifacts: ["PX054_FINAL_DEFENSE_PACKAGE_EXPORT_20260706.md", "activation_rows.csv"],
    },
    {
      id: "exp_px055",
      ideaId: "idea_005",
      title: "Refusal-Direction Geometry Under Post-Training Quantization",
      status: "queued_for_cloud_hook_gate",
      positiveResult: null,
      primaryMetric: "FP16/quantized direction stability",
      value: "cloud hook gate pending",
      successCriteria: "One-model FP16/int8/NF4 hidden-state capture works without custom CUDA and prompt validity stays >=0.95.",
      proof: "Gate 0A rescope/proceed completed; local preflight blocked by missing Torch/Transformers/bitsandbytes/CUDA. No measured model result yet.",
      artifacts: ["PX055_GATE0_SOURCE_CLEARANCE_20260711.md", "run_px055_quantization_hook_gate.py", "px055_quantization_hook_gate_20260711"],
    },
    {
      id: "exp_px056",
      ideaId: "idea_006",
      title: "Identifier Hallucination in Physical-AI Model Registries",
      status: "gate2a_pilot_positive",
      positiveResult: null,
      primaryMetric: "model-registry hallucination rate",
      value: "6.06% physical registry; 20.28% package baseline",
      successCriteria: "H1-H4 clear after full prompt run: hallucination rate, package comparator, PRE/POST churn effect, and gate FPR <= 2%.",
      proof: "Gate 2A completed on AWS SageMaker with 3 open code models, 378 real outputs, 1,282 extracted identifiers, generation errors 0, physical-registry nonexistent identifiers 2/33 (6.06%), package nonexistent identifiers 206/1,016 (20.28%), deterministic gate blocks 232, known-missing escapes 0, ambiguous verifications 116, and null-control extraction events 5. Positive live-output pilot, but full H1-H4 study is still pending.",
      artifacts: ["PX056_GATE2A_LIVE_MODEL_OUTPUT_PILOT.md", "PX056_GATE2A_DETERMINATION_20260721.md", "summary.json", "scored_identifiers_sanitized.csv", "run_px056_gate2_model_output.py"],
    },
    {
      id: "exp_agent_adaptive",
      ideaId: "idea_002",
      title: "Adaptive Evaluation of Deterministic Agent Gates",
      status: "plan_ready",
      positiveResult: null,
      primaryMetric: "adaptive invalid escape",
      value: "pending",
      successCriteria: "Hardened adaptive escape below registry-only baseline without utility collapse.",
      proof: "Pending execution.",
      artifacts: ["PLAN_READY.json"],
    },
  ],
  packages: [
    {
      id: "pkg_px050",
      experimentId: "exp_px050",
      title: "PX-050 Agentic Package Gate",
      status: "PACKAGE_READY",
      targets: ["GitHub", "Text", "PowerPoint"],
      repo: "reports/agentic_deployment_defense/px050_final_defense_package_export_20260705",
      summary: "Lead deployment-systems package with policy and provenance refresh.",
    },
    {
      id: "pkg_px003",
      experimentId: "exp_px003",
      title: "PX-003/PX-034 CTI Evidence Routing",
      status: "PACKAGE_READY",
      targets: ["GitHub", "Text"],
      repo: "reports/praxis_final_positive_reports_20260701",
      summary: "Relationship-evidence CTI compliance and source-support risk stratification.",
    },
  ],
  events: [
    {
      id: "evt_px056_added",
      type: "source_gate",
      title: "PX-056 model registry arm added",
      body: "Pre-registered HF Hub model/dataset identifier hallucination experiment; NGC remains conditional.",
      time: "13:08",
    },
    {
      id: "evt_px056_gate0",
      type: "source_gate",
      title: "PX-056 Gate 0 completed",
      body: "HF+NGC source readiness now passes after authenticated HF scoring and the corrected NGC catalog search path.",
      time: "18:49",
    },
    {
      id: "evt_px056_gate1",
      type: "source_gate",
      title: "PX-056 Gate 1 passed",
      body: "Extractor/verifier pilot passed on 24 fixtures: precision 1.0000, recall 1.0000, null-control false positives 0, known-missing escapes 0.",
      time: "18:56",
    },
    {
      id: "evt_px056_gate2a",
      type: "result",
      title: "PX-056 Gate 2A completed",
      body: "Live SageMaker pilot completed: 378 outputs, 1,282 extracted identifiers, physical-registry nonexistent rate 6.06%, package nonexistent rate 20.28%, deterministic gate blocks 232, known-missing escapes 0.",
      time: "21:57",
    },
    {
      id: "evt_px055_added",
      type: "source_gate",
      title: "PX-055 quantization geometry added",
      body: "Added as a deconflicted source-gate candidate; overlap must clear before GPU work.",
      time: "09:00",
    },
    {
      id: "evt_px055_gate0",
      type: "source_gate",
      title: "PX-055 Gate 0 ready",
      body: "Literature rescope completed; local hook preflight blocked; cloud FP16/int8/NF4 hook smoke packaged.",
      time: "23:23",
    },
    {
      id: "evt_001",
      type: "package_ready",
      title: "PX-050 package is defense ready",
      body: "Two-model dry-run live-agent corpus cleared hardened invalid allows with valid utility preserved.",
      time: "09:10",
    },
    {
      id: "evt_002",
      type: "defense_gate",
      title: "PX-054 waiting at defensibility gate",
      body: "Scale gate passed; claim remains observational and safe-prompt bounded.",
      time: "08:52",
    },
    {
      id: "evt_003",
      type: "review_complete",
      title: "Standing Committee paper reviewed",
      body: "Novelty boundary set to confirmation/extension only.",
      time: "06:12",
    },
  ],
};

let appState = loadState();
ensureSeedState(appState);
let currentView = "dashboard";
let selectedIdeaIds = new Set();
let query = "";

const $ = (selector) => document.querySelector(selector);

function loadState() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) return structuredClone(seedState);
  try {
    return JSON.parse(saved);
  } catch {
    return structuredClone(seedState);
  }
}

function mergeById(target, seeded) {
  seeded.forEach((entry) => {
    if (!target.some((item) => item.id === entry.id)) {
      target.push(structuredClone(entry));
    }
  });
}

function ensureSeedState(state) {
  mergeById(state.topics, seedState.topics);
  mergeById(state.workItems, seedState.workItems);
  mergeById(state.papers, seedState.papers);
  mergeById(state.ideas, seedState.ideas);
  mergeById(state.experiments, seedState.experiments);
  mergeById(state.packages, seedState.packages);
  mergeById(state.events, seedState.events);
  saveState();
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(appState));
}

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function logEvent(type, title, body) {
  appState.events.unshift({
    id: `evt_${Date.now()}`,
    type,
    title,
    body,
    time: nowTime(),
  });
  appState.events = appState.events.slice(0, 20);
  saveState();
}

function matchesQuery(text) {
  if (!query) return true;
  return text.toLowerCase().includes(query.toLowerCase());
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function badgeClass(value) {
  const normalized = String(value).toLowerCase();
  if (normalized.includes("positive") || normalized.includes("ready") || normalized.includes("completed")) return "green";
  if (normalized.includes("review") || normalized.includes("gate") || normalized.includes("plan")) return "amber";
  if (normalized.includes("negative") || normalized.includes("failed") || normalized.includes("blocked")) return "red";
  if (normalized.includes("selected") || normalized.includes("lead")) return "teal";
  return "violet";
}

function render() {
  renderViewChrome();
  renderBudget();
  renderMetrics();
  renderPipeline();
  renderEvents();
  renderTopics();
  renderPapers();
  renderIdeas();
  renderExperiments();
  renderPackages();
}

function renderViewChrome() {
  const titles = {
    dashboard: "Dashboard",
    topics: "Topics",
    papers: "Papers",
    ideas: "Ideas",
    experiments: "Experiments",
    packages: "Packages",
  };
  $("#viewTitle").textContent = titles[currentView];
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("is-visible"));
  $(`#${currentView}View`).classList.add("is-visible");
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === currentView);
  });
}

function renderBudget() {
  const { budgetCap, budgetUsed, gates } = appState.settings;
  const pct = Math.min(100, Math.round((budgetUsed / budgetCap) * 100));
  $("#budgetFill").style.width = `${pct}%`;
  $("#budgetUsed").textContent = `$${budgetUsed.toFixed(0)} used`;
  $("#budgetTotal").textContent = `$${budgetCap.toFixed(0)} cap`;
  $("#gateList").innerHTML = gates
    .map(
      (gate) => `
        <div class="gate-pill">
          <span>${escapeHtml(gate.name)}</span>
          <span class="badge ${gate.waiting ? "amber" : "green"}">${escapeHtml(gate.mode)} - ${gate.waiting}</span>
        </div>
      `,
    )
    .join("");
}

function renderMetrics() {
  const positives = appState.experiments.filter((exp) => exp.positiveResult === true).length;
  const running = appState.workItems.filter((item) => ["QUEUED_FOR_RUN", "EXECUTING", "EVALUATING"].includes(item.state)).length;
  const needsMe = appState.workItems.filter((item) => ["DEFENSIBILITY_CHECK", "PACKAGE_READY"].includes(item.state)).length;
  const packages = appState.packages.length;
  const tiles = [
    ["Papers", appState.papers.length, `${appState.topics.length} active topics`],
    ["Ideas", appState.ideas.length, `${selectedIdeaIds.size} selected now`],
    ["Runs", appState.experiments.length, `${running} in flight`],
    ["Positive", positives, "defensible results"],
    ["Needs Me", needsMe, `${packages} packages staged`],
  ];
  $("#metricsGrid").innerHTML = tiles
    .map(
      ([label, value, detail]) => `
        <article class="metric-card">
          <span>${label}</span>
          <strong>${value}</strong>
          <em>${detail}</em>
        </article>
      `,
    )
    .join("");
}

function getFilteredWorkItems() {
  const filter = $("#stageFilter")?.value || "all";
  return appState.workItems.filter((item) => {
    const text = `${item.title} ${item.topic} ${item.state} ${item.overview}`;
    if (!matchesQuery(text)) return false;
    if (filter === "needs_me") return ["DEFENSIBILITY_CHECK", "PACKAGE_READY"].includes(item.state);
    if (filter === "positive") return ["RESULT_POSITIVE", "DEFENSIBILITY_CHECK", "PACKAGE_READY", "PUBLISHED_GIT"].includes(item.state);
    if (filter === "blocked") return ["RESULT_NEGATIVE", "ARCHIVED"].includes(item.state);
    return true;
  });
}

function renderPipeline() {
  const board = $("#pipelineBoard");
  if (!board) return;
  const items = getFilteredWorkItems();
  board.innerHTML = stageGroups
    .map((group) => {
      const groupItems = items.filter((item) => group.states.includes(item.state));
      const cards = groupItems
        .map(
          (item) => `
            <article class="pipeline-card">
              <strong>${escapeHtml(item.title)}</strong>
              <p>${escapeHtml(item.overview)}</p>
              <div class="meta-line">
                <span class="badge ${badgeClass(item.state)}">${stateLabels[item.state] || item.state}</span>
                <span>${escapeHtml(item.priority)}</span>
              </div>
              <div class="card-actions">
                ${nextStage[item.state] ? `<button class="small-button" type="button" data-action="advance" data-id="${item.id}">Advance</button>` : ""}
                <button class="small-button" type="button" data-action="export-workitem" data-id="${item.id}">JSON</button>
              </div>
            </article>
          `,
        )
        .join("");
      return `
        <section class="pipeline-column">
          <h4><span>${group.title}</span><span>${groupItems.length}</span></h4>
          ${cards || emptyMarkup("No items")}
        </section>
      `;
    })
    .join("");
}

function renderEvents() {
  const events = appState.events.filter((event) => matchesQuery(`${event.title} ${event.body} ${event.type}`));
  $("#eventFeed").innerHTML =
    events
      .slice(0, 12)
      .map(
        (event) => `
          <article class="event">
            <span class="event-dot" aria-hidden="true"></span>
            <div>
              <strong>${escapeHtml(event.title)}</strong>
              <p>${escapeHtml(event.body)}</p>
              <div class="meta-line"><span>${escapeHtml(event.time)}</span><span>${escapeHtml(event.type)}</span></div>
            </div>
          </article>
        `,
      )
      .join("") || emptyMarkup("No events");
}

function renderTopics() {
  const rows = appState.topics.filter((topic) => matchesQuery(`${topic.name} ${topic.sources.join(" ")}`));
  $("#topicsTable").innerHTML =
    rows
      .map(
        (topic) => `
          <article class="topic-row">
            <div>
              <strong>${escapeHtml(topic.name)}</strong>
              <div class="meta-line">${topic.sources.map((source) => `<span>${escapeHtml(source)}</span>`).join("")}</div>
            </div>
            <span class="badge ${topic.active ? "green" : "red"}">${topic.active ? "active" : "paused"}</span>
            <span>${topic.dailyCap}/day</span>
            <span>${topic.peerReviewedOnly ? "peer reviewed" : "mixed"}</span>
            <button class="small-button" type="button" data-action="toggle-topic" data-id="${topic.id}">${topic.active ? "Pause" : "Resume"}</button>
          </article>
        `,
      )
      .join("") || emptyMarkup("No topics");
}

function renderPapers() {
  const rows = appState.papers.filter((paper) => matchesQuery(`${paper.title} ${paper.topic} ${paper.source} ${paper.novelty}`));
  $("#paperList").innerHTML =
    rows
      .map(
        (paper) => `
          <article class="record-card">
            <div>
              <h4>${escapeHtml(paper.title)}</h4>
              <p>${escapeHtml(paper.novelty)}</p>
              <div class="meta-line">
                <span>${escapeHtml(paper.topic)}</span>
                <span>${escapeHtml(paper.source)}</span>
                <span>${escapeHtml(paper.published)}</span>
                <span>${paper.abstractOnly ? "abstract only" : "full text"}</span>
              </div>
            </div>
            <div class="record-side">
              <span class="badge ${badgeClass(paper.state)}">${stateLabels[paper.state] || paper.state}</span>
              <span class="badge ${paper.evidenceStrength === "strong" ? "green" : "amber"}">${paper.evidenceStrength}</span>
              <button class="small-button" type="button" data-action="force-review" data-id="${paper.id}">Review</button>
            </div>
          </article>
        `,
      )
      .join("") || emptyMarkup("No papers");
}

function renderIdeas() {
  const ideas = appState.ideas.filter((idea) => matchesQuery(`${idea.title} ${idea.oneLiner} ${idea.type} ${idea.status}`));
  $("#ideaBoard").innerHTML =
    ideas
      .map(
        (idea) => `
          <article class="idea-card">
            <div>
              <div class="meta-line">
                <span class="badge ${badgeClass(idea.status)}">${escapeHtml(idea.status)}</span>
                <span>${escapeHtml(idea.type)}</span>
              </div>
              <h4>${escapeHtml(idea.title)}</h4>
              <p>${escapeHtml(idea.oneLiner)}</p>
              <div class="idea-score">
                <div class="score-box"><span>Feasible</span><strong>${idea.feasibility}</strong></div>
                <div class="score-box"><span>Impact</span><strong>${idea.impact}</strong></div>
                <div class="score-box"><span>Defense</span><strong>${idea.defensibility}</strong></div>
              </div>
              <p class="card-small">${escapeHtml(idea.risks.join(" "))}</p>
            </div>
            <div class="card-actions">
              <button class="small-button" type="button" data-action="select-idea" data-id="${idea.id}">${selectedIdeaIds.has(idea.id) ? "Selected" : "Select"}</button>
              <button class="small-button" type="button" data-action="export-idea" data-id="${idea.id}">Plan</button>
            </div>
          </article>
        `,
      )
      .join("") || emptyMarkup("No ideas");
}

function renderExperiments() {
  const rows = appState.experiments.filter((exp) => matchesQuery(`${exp.title} ${exp.status} ${exp.proof} ${exp.primaryMetric}`));
  $("#experimentList").innerHTML =
    rows
      .map(
        (exp) => `
          <article class="record-card">
            <div>
              <h4>${escapeHtml(exp.title)}</h4>
              <p>${escapeHtml(exp.successCriteria)}</p>
              <div class="meta-line">
                <span class="badge ${badgeClass(exp.status)}">${escapeHtml(exp.status)}</span>
                <span>${escapeHtml(exp.primaryMetric)}: ${escapeHtml(exp.value)}</span>
                <span>${exp.positiveResult === true ? "positive" : exp.positiveResult === false ? "negative" : "pending"}</span>
              </div>
              <p>${escapeHtml(exp.proof)}</p>
            </div>
            <div class="record-side">
              <button class="small-button" type="button" data-action="run-exp" data-id="${exp.id}">Run</button>
              <button class="small-button" type="button" data-action="complete-exp" data-id="${exp.id}">Evaluate</button>
              <button class="small-button" type="button" data-action="export-exp" data-id="${exp.id}">JSON</button>
            </div>
          </article>
        `,
      )
      .join("") || emptyMarkup("No experiments");
}

function renderPackages() {
  const rows = appState.packages.filter((pkg) => matchesQuery(`${pkg.title} ${pkg.status} ${pkg.summary} ${pkg.targets.join(" ")}`));
  $("#packageList").innerHTML =
    rows
      .map(
        (pkg) => `
          <article class="package-card">
            <div>
              <span class="badge green">${escapeHtml(pkg.status)}</span>
              <h4>${escapeHtml(pkg.title)}</h4>
              <p>${escapeHtml(pkg.summary)}</p>
              <div class="meta-line">${pkg.targets.map((target) => `<span>${escapeHtml(target)}</span>`).join("")}</div>
              <p class="card-small">${escapeHtml(pkg.repo)}</p>
            </div>
            <div class="card-actions">
              <button class="small-button" type="button" data-action="publish-pkg" data-id="${pkg.id}">Publish</button>
              <button class="small-button" type="button" data-action="export-pkg" data-id="${pkg.id}">Text</button>
            </div>
          </article>
        `,
      )
      .join("") || emptyMarkup("No packages");
}

function emptyMarkup(text) {
  return `<div class="empty-state"><strong>${escapeHtml(text)}</strong><span>Praxis Recon</span></div>`;
}

function advanceWorkItem(id) {
  const item = appState.workItems.find((entry) => entry.id === id);
  if (!item || !nextStage[item.state]) return;
  const from = item.state;
  item.state = nextStage[item.state];
  item.updatedAt = new Date().toLocaleString();
  logEvent("state_advanced", `${item.title} advanced`, `${stateLabels[from]} -> ${stateLabels[item.state]}`);
}

function toggleTopic(id) {
  const topic = appState.topics.find((entry) => entry.id === id);
  if (!topic) return;
  topic.active = !topic.active;
  logEvent("topic_update", `${topic.name} ${topic.active ? "resumed" : "paused"}`, `Daily cap ${topic.dailyCap}`);
}

function forceReview(id) {
  const paper = appState.papers.find((entry) => entry.id === id);
  if (!paper) return;
  paper.state = "REVIEWED";
  paper.evidenceStrength = paper.evidenceStrength === "strong" ? "strong" : "moderate";
  appState.settings.budgetUsed += 3.6;
  logEvent("review_complete", `${paper.title} reviewed`, `${paper.evidenceStrength} evidence strength`);
}

function selectIdea(id) {
  if (selectedIdeaIds.has(id)) {
    selectedIdeaIds.delete(id);
  } else {
    selectedIdeaIds.add(id);
  }
  const idea = appState.ideas.find((entry) => entry.id === id);
  if (idea) idea.status = selectedIdeaIds.has(id) ? "selected" : "ready";
  logEvent("idea_selection", "Idea selection updated", `${selectedIdeaIds.size} idea(s) selected`);
  saveState();
  render();
}

function runExperiment(id) {
  const exp = appState.experiments.find((entry) => entry.id === id);
  if (!exp) return;
  exp.status = "executing";
  appState.settings.budgetUsed += 12.5;
  logEvent("run_started", `${exp.title} executing`, `Guardrails active for ${exp.primaryMetric}`);
}

function completeExperiment(id) {
  const exp = appState.experiments.find((entry) => entry.id === id);
  if (!exp) return;
  if (exp.positiveResult === null) {
    exp.positiveResult = true;
    exp.value = "0.041 escape";
    exp.proof = "The simulated gate cleared the registered positive screen and now waits for defense audit.";
  }
  exp.status = "defensibility_check";
  logEvent("evaluation_complete", `${exp.title} evaluated`, exp.proof);
}

function discoverPapers() {
  const active = appState.topics.filter((topic) => topic.active);
  const id = `paper_${Date.now()}`;
  const topic = active[0] || appState.topics[0];
  appState.papers.unshift({
    id,
    title: `New ${topic.name} paper candidate`,
    topic: topic.name,
    source: topic.includePreprints ? "OpenAlex + arXiv" : "OpenAlex",
    published: "2026",
    state: "DISCOVERED",
    evidenceStrength: "pending",
    novelty: "Queued for review agent and praxis ideation.",
    abstractOnly: false,
  });
  appState.workItems.unshift({
    id: `wi_${id}`,
    title: `New ${topic.name} paper candidate`,
    topic: topic.name,
    state: "DISCOVERED",
    kind: "paper",
    venue: "Discovery",
    source: "Open metadata APIs",
    priority: "New",
    abstractOnly: false,
    defensibility: 0,
    cost: 0.4,
    updatedAt: new Date().toLocaleString(),
    overview: "Newly discovered candidate awaiting review.",
  });
  appState.settings.budgetUsed += 0.4;
  logEvent("paper_discovered", "New paper discovered", topic.name);
}

function redTeamScores() {
  appState.ideas.forEach((idea) => {
    if (idea.defensibility > 3 && idea.risks.length) {
      idea.defensibility -= 1;
    }
  });
  logEvent("red_team", "Idea scores red-teamed", "Defensibility adjusted for known risks");
}

function queueSelected() {
  const selected = appState.ideas.filter((idea) => selectedIdeaIds.has(idea.id));
  selected.forEach((idea) => {
    const existing = appState.experiments.some((exp) => exp.ideaId === idea.id);
    if (existing) return;
    appState.experiments.unshift({
      id: `exp_${Date.now()}_${idea.id}`,
      ideaId: idea.id,
      title: idea.title,
      status: "plan_ready",
      positiveResult: null,
      primaryMetric: "registered primary metric",
      value: "pending",
      successCriteria: "Pass registered threshold without violating guardrails.",
      proof: "Pending execution.",
      artifacts: ["PLAN.md", "outputs_contract.json"],
    });
  });
  logEvent("experiments_queued", "Selected ideas queued", `${selected.length} selected idea(s) processed`);
}

function generatePackages() {
  const positives = appState.experiments.filter((exp) => exp.positiveResult === true);
  positives.forEach((exp) => {
    const exists = appState.packages.some((pkg) => pkg.experimentId === exp.id);
    if (exists) return;
    appState.packages.unshift({
      id: `pkg_${Date.now()}_${exp.id}`,
      experimentId: exp.id,
      title: exp.title,
      status: "PACKAGE_READY",
      targets: ["GitHub", "Text", "PowerPoint"],
      repo: "generated/praxis-package",
      summary: exp.proof,
    });
  });
  logEvent("package_generated", "Positive results packaged", `${positives.length} positive result(s) checked`);
}

function publishPackage(id) {
  const pkg = appState.packages.find((entry) => entry.id === id);
  if (!pkg) return;
  pkg.status = "PUBLISHED_GIT";
  logEvent("published", `${pkg.title} published`, "GitHub target recorded");
}

function exportObject(name, object, type = "json") {
  const content = type === "json" ? JSON.stringify(object, null, 2) : object;
  const mime = type === "json" ? "application/json" : "text/plain";
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function exportMarkdownPlan(idea) {
  const paper = appState.papers.find((entry) => entry.id === idea.paperId);
  return `# ${idea.title}

## Source
${paper ? paper.title : "Unknown paper"}

## Praxis Idea
${idea.oneLiner}

## Scores
- Feasibility: ${idea.feasibility}
- Impact: ${idea.impact}
- Defensibility: ${idea.defensibility}

## Risks
${idea.risks.map((risk) => `- ${risk}`).join("\n")}

## Outputs Contract
results.json must include status, positive_result, primary_metric_value, overview, what_it_proves, artifacts, and caveats.
`;
}

function handleAction(action, id) {
  if (action === "advance") advanceWorkItem(id);
  if (action === "export-workitem") exportObject(`${id}.json`, appState.workItems.find((item) => item.id === id));
  if (action === "toggle-topic") toggleTopic(id);
  if (action === "force-review") forceReview(id);
  if (action === "select-idea") return selectIdea(id);
  if (action === "export-idea") {
    const idea = appState.ideas.find((entry) => entry.id === id);
    if (idea) exportObject(`${id}_PLAN.md`, exportMarkdownPlan(idea), "text");
  }
  if (action === "run-exp") runExperiment(id);
  if (action === "complete-exp") completeExperiment(id);
  if (action === "export-exp") exportObject(`${id}.json`, appState.experiments.find((exp) => exp.id === id));
  if (action === "publish-pkg") publishPackage(id);
  if (action === "export-pkg") {
    const pkg = appState.packages.find((entry) => entry.id === id);
    if (pkg) exportObject(`${id}.txt`, `${pkg.title}\n\n${pkg.summary}\n\nTargets: ${pkg.targets.join(", ")}\n`, "text");
  }
  saveState();
  render();
}

function wireEvents() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      currentView = button.dataset.view;
      render();
    });
  });

  document.body.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    handleAction(button.dataset.action, button.dataset.id);
  });

  $("#searchInput").addEventListener("input", (event) => {
    query = event.target.value.trim();
    render();
  });

  $("#stageFilter").addEventListener("change", render);
  $("#discoverButton").addEventListener("click", () => {
    discoverPapers();
    saveState();
    render();
  });
  $("#redTeamButton").addEventListener("click", () => {
    redTeamScores();
    saveState();
    render();
  });
  $("#queueButton").addEventListener("click", () => {
    queueSelected();
    saveState();
    render();
  });
  $("#generatePackageButton").addEventListener("click", () => {
    generatePackages();
    saveState();
    render();
  });
  $("#exportStateButton").addEventListener("click", () => exportObject("praxis-recon-state.json", appState));
  $("#resetButton").addEventListener("click", () => {
    appState = structuredClone(seedState);
    selectedIdeaIds = new Set();
    saveState();
    render();
  });
  $("#topicForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const name = $("#topicName").value.trim();
    if (!name) return;
    appState.topics.unshift({
      id: `topic_${Date.now()}`,
      name,
      dailyCap: Number($("#topicCap").value || 25),
      peerReviewedOnly: $("#topicPeer").checked,
      includePreprints: $("#topicPreprints").checked,
      active: true,
      sources: $("#topicPreprints").checked ? ["OpenAlex", "arXiv"] : ["OpenAlex", "Crossref"],
      discovered: 0,
    });
    event.target.reset();
    $("#topicCap").value = 40;
    $("#topicPeer").checked = true;
    logEvent("topic_created", `${name} added`, "Query spec initialized");
    saveState();
    render();
  });
}

wireEvents();
render();

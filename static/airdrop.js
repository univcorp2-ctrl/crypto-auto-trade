let report = null;

const el = (id) => document.getElementById(id);

function statusClass(status) {
  if (status === "READY_DRY_RUN") return "good";
  if (status === "UNVERIFIED") return "bad";
  return "warn";
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ja-JP");
}

function renderSummary(data) {
  el("targetCount").textContent = data.target_count ?? 0;
  el("readyCount").textContent = data.ready_dry_run ?? 0;
  el("readOnlyCount").textContent = data.read_only ?? 0;
  el("unverifiedCount").textContent = data.unverified ?? 0;
  el("lastRun").textContent = formatDate(data.generated_at);
}

function cardHtml(target) {
  const programOk = target.program_probe?.ok;
  const apiOk = target.api_probe?.ok;
  const programClass = programOk === true ? "good" : programOk === false ? "bad" : "warn";
  const apiClass = apiOk === true ? "good" : apiOk === false ? "bad" : "warn";
  const eligibilityClass = target.api_reward_eligibility === "CONFIRMED" ? "good" : target.api_reward_eligibility === "UNVERIFIED" ? "bad" : "warn";
  return `
    <article class="agent-card">
      <div class="agent-top">
        <div>
          <h2 class="agent-title">${target.name}</h2>
          <div class="badges">
            <span class="badge">Wave ${target.wave}</span>
            <span class="badge">${target.mode}</span>
            <span class="badge">Priority ${target.priority}</span>
            <span class="badge ${programClass}">Program ${programOk === true ? "OK" : programOk === false ? "NG" : "-"}</span>
            <span class="badge ${apiClass}">API ${target.api_url ? (apiOk === true ? "OK" : apiOk === false ? "NG" : "-") : "N/A"}</span>
            <span class="badge ${eligibilityClass}">Reward ${target.api_reward_eligibility || "REVERIFY"}</span>
          </div>
        </div>
        <span class="status-pill ${statusClass(target.status)}">${target.status}</span>
      </div>
      <div class="details">
        <div><span>Reward unit</span><strong>${target.reward_unit}</strong></div>
        <div><span>Japan / Legal</span><strong>${target.japan_legal_status}</strong></div>
        <div><span>API reward eligibility</span><strong>${target.api_reward_eligibility}</strong></div>
        <div><span>Rule verified</span><strong>${formatDate(target.reward_rule_verified_at)}</strong></div>
        <div><span>LIVE</span><strong>${target.live_approved ? "APPROVED" : "OFF"}</strong></div>
        <div><span>Checked</span><strong>${formatDate(target.checked_at)}</strong></div>
        <div><span>Open risk</span><strong>$${Number(target.open_risk_usd ?? 0).toFixed(2)}</strong></div>
      </div>
      <p class="reason">${target.blocked_reason || target.seed_note || ""}</p>
      ${target.reward_evidence_note ? `<p class="reason">Reward evidence: ${target.reward_evidence_note}</p>` : ""}
      <div class="links">
        <a href="${target.program_url}" target="_blank" rel="noreferrer">Program ↗</a>
        ${target.api_url ? `<a href="${target.api_url}" target="_blank" rel="noreferrer">API / Docs ↗</a>` : ""}
        ${target.reward_evidence_source ? `<a href="${target.reward_evidence_source}" target="_blank" rel="noreferrer">Reward evidence ↗</a>` : ""}
      </div>
    </article>`;
}

function renderGrid() {
  const grid = el("agentGrid");
  if (!report) return;
  const wave = el("waveFilter").value;
  const status = el("statusFilter").value;
  const query = el("search").value.trim().toLowerCase();
  const targets = (report.targets || []).filter((target) => {
    const waveOk = wave === "all" || String(target.wave) === wave;
    const statusOk = status === "all" || target.status === status;
    const haystack = `${target.name} ${target.slug} ${target.reward_unit} ${target.mode} ${target.seed_note} ${target.api_reward_eligibility}`.toLowerCase();
    const queryOk = !query || haystack.includes(query);
    return waveOk && statusOk && queryOk;
  });
  grid.innerHTML = targets.length ? targets.map(cardHtml).join("") : '<div class="empty">該当するAgentがありません。</div>';
}

async function loadStatus() {
  el("loading").hidden = false;
  try {
    const response = await fetch("/api/airdrop/status");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    report = await response.json();
    renderSummary(report);
    renderGrid();
  } catch (error) {
    el("agentGrid").innerHTML = `<div class="empty">Status取得失敗: ${String(error)}</div>`;
  } finally {
    el("loading").hidden = true;
  }
}

async function runDry() {
  const button = el("runDry");
  button.disabled = true;
  button.textContent = "DRY RUN中…";
  try {
    const response = await fetch("/api/airdrop/dry-run?probe_network=true", { method: "POST" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    report = await response.json();
    renderSummary(report);
    renderGrid();
  } catch (error) {
    window.alert(`DRY RUN失敗: ${String(error)}`);
  } finally {
    button.disabled = false;
    button.textContent = "今すぐDRY RUN";
  }
}

el("runDry").addEventListener("click", runDry);
el("refresh").addEventListener("click", loadStatus);
el("waveFilter").addEventListener("change", renderGrid);
el("statusFilter").addEventListener("change", renderGrid);
el("search").addEventListener("input", renderGrid);

loadStatus();

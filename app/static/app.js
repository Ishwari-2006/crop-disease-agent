const SESSION_ID = "session_" + Math.random().toString(36).substr(2, 9);
let selectedFile = null;
let currentFarming = "both";

// ---------- Treatment toggle ----------
const treatmentToggle = document.getElementById("treatmentToggle");
treatmentToggle.addEventListener("click", e => {
    const btn = e.target.closest(".tt-chip");
    if (!btn) return;
    treatmentToggle.querySelectorAll(".tt-chip").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentFarming = btn.dataset.value;
});

// ---------- File input handler ----------
document.getElementById("fileInput").addEventListener("change", function(e) {
    if (e.target.files[0]) handleFile(e.target.files[0]);
});

// ---------- Drag and drop ----------
const dropZone = document.getElementById("dropZone");
dropZone.addEventListener("click", () => {
    if (!selectedFile) document.getElementById("fileInput").click();
});
dropZone.addEventListener("dragover",  e => { e.preventDefault(); if (!selectedFile) dropZone.classList.add("dragover"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", e => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = e => {
        const preview = document.getElementById("previewImg");
        preview.src = e.target.result;
        preview.classList.remove("hidden");
        document.getElementById("previewFilename").textContent = file.name;
        document.getElementById("previewFilename").classList.remove("hidden");
        document.getElementById("cancelBtn").classList.remove("hidden");
        document.getElementById("dropContent").classList.add("hidden");
        dropZone.classList.add("has-image");
    };
    reader.readAsDataURL(file);
    document.getElementById("analyzeBtn").disabled = false;
}

function cancelUpload(e) {
    if (e) e.stopPropagation();
    selectedFile = null;
    document.getElementById("fileInput").value = "";
    document.getElementById("previewImg").classList.add("hidden");
    document.getElementById("previewFilename").classList.add("hidden");
    document.getElementById("cancelBtn").classList.add("hidden");
    document.getElementById("dropContent").classList.remove("hidden");
    dropZone.classList.remove("has-image");
    document.getElementById("analyzeBtn").disabled = true;

    document.getElementById("resultZone").innerHTML = `
        <section class="card">
            <div class="result-waiting">
                <div class="result-icon">🌿</div>
                <div class="result-title">Awaiting Analysis</div>
                <div class="result-sub">Upload a leaf photo to get started</div>
            </div>
        </section>`;

    resetChat();

    // Reset session
    fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: SESSION_ID })
    });
}

async function analyzeLeaf() {
    if (!selectedFile) return;

    const farming = currentFarming;

    document.getElementById("resultZone").innerHTML = `
        <section class="card">
            <div class="loading">
                <div class="spinner"></div>
                <div>Analyzing leaf...</div>
                <div style="font-size:12px; color:#8b9179; margin-top:4px">AI is preparing your report</div>
            </div>
        </section>`;

    const formData = new FormData();
    formData.append("image", selectedFile);
    formData.append("farming_type", farming);
    formData.append("session_id", SESSION_ID);

    try {
        const res  = await fetch("/api/analyze", { method: "POST", body: formData });
        const data = await res.json();

        if (data.error) {
            document.getElementById("resultZone").innerHTML = `
                <section class="card">
                    <div class="result-waiting">
                        <div class="result-icon">⚠️</div>
                        <div class="result-title">Error</div>
                        <div class="result-sub">${data.error}</div>
                    </div>
                </section>`;
            return;
        }

        showResult(data, farming);
        activateChat(data);

    } catch (err) {
        document.getElementById("resultZone").innerHTML = `
            <section class="card">
                <div class="result-waiting">
                    <div class="result-icon">⚠️</div>
                    <div class="result-title">Connection error</div>
                    <div class="result-sub">Make sure the server is running</div>
                </div>
            </section>`;
    }
}

function showResult(data, farming) {
    const severity   = (data.severity || "unknown").toLowerCase();
    const severityLabel = data.severity || "Unknown";

    const showOrganic  = (farming === "both" || farming === "organic") && (data.organic || []).length;
    const showChemical = (farming === "both" || farming === "chemical") && (data.chemical || []).length;

    const organicHTML  = (data.organic  || []).map(t => `<li>${t}</li>`).join("");
    const chemicalHTML = (data.chemical || []).map(t => `<li>${t}</li>`).join("");

    const preventionHTML = Array.isArray(data.prevention)
        ? data.prevention.map(t => `<li>${t}</li>`).join("")
        : data.prevention ? `<li>${data.prevention}</li>` : "";

    let html = `
        <section class="card">
            <div class="diagnosis-head">
                <div>
                    <div class="diagnosis-eyebrow">DIAGNOSIS · ${(data.plant || "").toUpperCase()}</div>
                    <div class="disease-name">${data.disease}</div>
                    <div class="badge-row">
                        <span class="badge badge-detected">⚠ Disease Detected</span>
                        <span class="badge badge-severity">Severity · ${severityLabel}</span>
                    </div>
                </div>
                <div class="confidence-block">
                    <div class="confidence-label">Confidence</div>
                    <div class="confidence-num">${data.confidence}<sup>%</sup></div>
                    <div class="confidence-bar-bg">
                        <div class="confidence-bar-fill" style="width:${data.confidence}%"></div>
                    </div>
                </div>
            </div>
        </section>

        <section class="card">
            <div class="about-title-row">
                <div class="about-icon">ℹ️</div>
                <div>
                    <div class="about-title">About the diagnosis</div>
                    <div class="about-sub">DISEASE OVERVIEW</div>
                </div>
            </div>
            <div class="about-body">${marked.parse(data.report || "")}</div>
        </section>`;

    if (showOrganic || showChemical) {
        html += `<section class="card"><div class="treatment-row">`;
        if (showOrganic) {
            html += `
                <div class="treatment-card organic">
                    <div class="treatment-title-row">
                        <div class="treatment-icon">🌿</div>
                        <div>
                            <div class="treatment-title">Organic treatment</div>
                            <div class="treatment-sub">Natural remedies</div>
                        </div>
                    </div>
                    <ul class="treatment-list">${organicHTML}</ul>
                </div>`;
        }
        if (showChemical) {
            html += `
                <div class="treatment-card chemical">
                    <div class="treatment-title-row">
                        <div class="treatment-icon">⚗️</div>
                        <div>
                            <div class="treatment-title">Chemical treatment</div>
                            <div class="treatment-sub">Synthetic protocol</div>
                        </div>
                    </div>
                    <ul class="treatment-list">${chemicalHTML}</ul>
                </div>`;
        }
        html += `</div></section>`;
    }

    if (preventionHTML) {
        html += `
            <section class="card">
                <div class="about-title-row">
                    <div class="about-icon">🛡️</div>
                    <div>
                        <div class="about-title">Prevention</div>
                        <div class="about-sub">STAY AHEAD NEXT SEASON</div>
                    </div>
                </div>
                <ul class="prevention-list">${preventionHTML}</ul>
            </section>`;
    }

    document.getElementById("resultZone").innerHTML = html;
}

// ---------- Chat ----------
function activateChat(data) {
    document.getElementById("chatSub").textContent = `Chat · ${data.disease}`;
    document.getElementById("chatIntro").innerHTML =
        `Hi — I'm CropDoctor.<br>I have your <strong>${data.disease}</strong> diagnosis in mind. Ask me anything about it.`;
    document.getElementById("chatSuggestions").style.display = "flex";
    document.getElementById("chatMessages").innerHTML = "";
    document.getElementById("chatInput").disabled = false;
    document.getElementById("chatSendBtn").disabled = false;
}

function resetChat() {
    document.getElementById("chatSub").textContent = "Chat · Awaiting Diagnosis";
    document.getElementById("chatIntro").innerHTML =
        `Hi — I'm CropDoctor.<br>Upload and analyze a leaf photo, and I'll be ready to answer anything about the diagnosis.`;
    document.getElementById("chatSuggestions").style.display = "none";
    document.getElementById("chatMessages").innerHTML = "";
    document.getElementById("chatInput").disabled = true;
    document.getElementById("chatSendBtn").disabled = true;
}

document.getElementById("chatSuggestions").addEventListener("click", e => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    document.getElementById("chatInput").value = chip.dataset.q;
    sendChat();
});

async function sendChat() {
    const input    = document.getElementById("chatInput");
    const question = input.value.trim();
    if (!question || input.disabled) return;

    input.value = "";
    const messages = document.getElementById("chatMessages");
    const body = document.getElementById("chatBody");

    messages.innerHTML += `<div class="chat-msg-user">${question}</div>`;

    const loadingId = "loading_" + Date.now();
    messages.innerHTML += `<div id="${loadingId}" class="chat-typing">AI Expert is typing...</div>`;
    body.scrollTop = body.scrollHeight;

    try {
        const res  = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, session_id: SESSION_ID })
        });
        const data = await res.json();

        document.getElementById(loadingId).remove();
        messages.innerHTML += `<div class="chat-msg-agent">${marked.parse(data.reply || data.error || "")}</div>`;
        body.scrollTop = body.scrollHeight;

    } catch (err) {
        document.getElementById(loadingId).remove();
        messages.innerHTML += `<div class="chat-msg-agent">Connection error. Please try again.</div>`;
        body.scrollTop = body.scrollHeight;
    }
}
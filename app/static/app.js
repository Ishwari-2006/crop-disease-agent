const SESSION_ID = "session_" + Math.random().toString(36).substr(2, 9);
let selectedFile = null;

// File input handler
document.getElementById("fileInput").addEventListener("change", function(e) {
    if (e.target.files[0]) handleFile(e.target.files[0]);
});

// Drag and drop
const dropZone = document.getElementById("dropZone");
dropZone.addEventListener("dragover",  e => { e.preventDefault(); dropZone.classList.add("dragover"); });
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
        const content = document.getElementById("dropContent");
        preview.src = e.target.result;
        preview.classList.remove("hidden");
        content.classList.add("hidden");

        // Show cancel button
        document.getElementById("cancelBtn").style.display = "block";
    };
    reader.readAsDataURL(file);
    document.getElementById("analyzeBtn").disabled = false;
}

function cancelUpload() {
    selectedFile = null;
    document.getElementById("fileInput").value = "";
    document.getElementById("previewImg").classList.add("hidden");
    document.getElementById("dropContent").classList.remove("hidden");
    document.getElementById("analyzeBtn").disabled = true;
    document.getElementById("cancelBtn").style.display = "none";
    document.getElementById("resultZone").innerHTML = `
        <div class="result-waiting">
            <div class="result-icon">🌿</div>
            <div class="result-title">Awaiting Analysis</div>
            <div class="result-sub">Upload a leaf photo to get started</div>
        </div>`;
    document.getElementById("chatSection").style.display = "none";
    document.getElementById("chatMessages").innerHTML = "";

    // Reset session
    fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: SESSION_ID })
    });
}

async function analyzeLeaf() {
    if (!selectedFile) return;

    const farming = document.querySelector('input[name="farm"]:checked').value;

    // Show loading
    document.getElementById("resultZone").innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <div>Analyzing leaf...</div>
            <div style="font-size:12px; color:#7aaa7a; margin-top:4px">AI is preparing your report</div>
        </div>`;

    const formData = new FormData();
    formData.append("image", selectedFile);
    formData.append("farming_type", farming);
    formData.append("session_id", SESSION_ID);

    try {
        const res  = await fetch("/api/analyze", { method: "POST", body: formData });
        const data = await res.json();

        if (data.error) {
            document.getElementById("resultZone").innerHTML =
                `<div class="result-waiting">
                    <div class="result-icon">⚠️</div>
                    <div class="result-title">Error</div>
                    <div class="result-sub">${data.error}</div>
                </div>`;
            return;
        }

        showResult(data,farming);
        document.getElementById("chatSection").style.display = "block";

    } catch (err) {
        document.getElementById("resultZone").innerHTML =
            `<div class="result-waiting">
                <div class="result-icon">⚠️</div>
                <div class="result-title">Connection error</div>
                <div class="result-sub">Make sure the server is running</div>
            </div>`;
    }
}

function showResult(data, farming) {
    const severity   = (data.severity || "unknown").toLowerCase();
    const badgeClass = severity === "high"   ? "badge-high"
                     : severity === "medium" ? "badge-medium"
                     : severity === "low"    ? "badge-low"
                     : "badge-none";

    const organicHTML  = (data.organic  || []).map(t =>
        `<div class="treatment-item">${t}</div>`).join("");
    const chemicalHTML = (data.chemical || []).map(t =>
        `<div class="treatment-item">${t}</div>`).join("");

    // Only show relevant treatment sections
    const showOrganic  = farming === "both" || farming === "organic";
    const showChemical = farming === "both" || farming === "chemical";

    document.getElementById("resultZone").innerHTML = `
        <div class="diagnosis-result">
            <div class="disease-header">
                <div class="plant-label">${data.plant}</div>
                <div class="disease-name">${data.disease}</div>
                <span class="badge ${badgeClass}">${data.severity} severity</span>
                <div class="confidence-row">
                    <span class="confidence-label">Confidence</span>
                    <div class="confidence-bar-bg">
                        <div class="confidence-bar-fill" style="width:${data.confidence}%"></div>
                    </div>
                    <span class="confidence-pct">${data.confidence}%</span>
                </div>
            </div>

            <div class="report-box">${data.report.replace(/\n/g, "<br>")}</div>

            ${showOrganic && organicHTML ? `
            <div class="treatment-section">
                <div class="treatment-label">🌿 Organic treatments</div>
                ${organicHTML}
            </div>` : ""}

            ${showChemical && chemicalHTML ? `
            <div class="treatment-section">
                <div class="treatment-label">⚗️ Chemical treatments</div>
                ${chemicalHTML}
            </div>` : ""}

            ${data.prevention ? `
            <div class="treatment-section">
                <div class="treatment-label">🛡️ Prevention</div>
                <div class="treatment-item">${data.prevention}</div>
            </div>` : ""}
        </div>`;
}

async function sendChat() {
    const input    = document.getElementById("chatInput");
    const question = input.value.trim();
    if (!question) return;

    input.value = "";
    const messages = document.getElementById("chatMessages");

    // Add user message
    messages.innerHTML += `
        <div>
            <div class="chat-label chat-label-user">You</div>
            <div class="chat-msg-user">${question}</div>
        </div>`;

    // Add loading
    const loadingId = "loading_" + Date.now();
    messages.innerHTML += `<div id="${loadingId}" style="color:#7aaa7a; font-size:12px; padding:4px 8px;">AI Expert is typing...</div>`;
    messages.scrollTop = messages.scrollHeight;

    try {
        const res  = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, session_id: SESSION_ID })
        });
        const data = await res.json();

        document.getElementById(loadingId).remove();
        messages.innerHTML += `
            <div>
                <div class="chat-label chat-label-agent">AI Expert</div>
                <div class="chat-msg-agent">${(data.reply || data.error).replace(/\n/g, "<br>")}</div>
            </div>`;
        messages.scrollTop = messages.scrollHeight;

    } catch (err) {
        document.getElementById(loadingId).remove();
        messages.innerHTML += `<div class="chat-msg-agent">Connection error. Please try again.</div>`;
    }
}
/** Chat & Progressive Synthesis Module */
import { ToastSystem } from './toast.js';
import { EvidenceDrawer } from './evidence.js';
import { SourcesModule } from './sources.js';

export const ChatModule = {
    history: [],
    isGenerating: false,
    autoScroll: true,
    userScrolledUp: false,
    activeScope: "ALL",
    activeAbortController: null,

    init() {
        this.renderEmptyState();
        this.setupScrollListener();
    },

    setupScrollListener() {
        const chatContainer = document.getElementById("chatMessages");
        const viewport = document.getElementById("chatViewport") || chatContainer;
        if (viewport) {
            viewport.addEventListener("scroll", () => {
                const distanceFromBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
                this.userScrolledUp = distanceFromBottom > 75;
            }, { passive: true });
        }
    },

    scrollToBottom() {
        if (this.userScrolledUp) return;
        const viewport = document.getElementById("chatViewport") || document.getElementById("chatMessages");
        if (viewport) {
            viewport.scrollTop = viewport.scrollHeight;
        }
    },

    stopGeneration() {
        if (this.activeAbortController) {
            this.activeAbortController.abort();
            this.activeAbortController = null;
        }
        this.isGenerating = false;
        const sendBtnIcon = document.getElementById("sendBtnIcon");
        if (sendBtnIcon) sendBtnIcon.textContent = "north_east";
        ToastSystem.show("Generation stopped.");
    },

    renderEmptyState() {
        const container = document.getElementById("chatMessages");
        if (!container || this.history.length > 0) return;

        const docs = SourcesModule.documents || [];
        if (docs.length === 0) {
            container.innerHTML = `
                <div class="chat-empty-state">
                    <span class="material-symbols-outlined chat-empty-icon">menu_book</span>
                    <h2 class="chat-empty-title">Academic Research Workspace</h2>
                    <p class="chat-empty-desc">
                        Please upload an academic PDF to begin your research. All embeddings, property graphs, and citations are extracted locally.
                    </p>
                    <button type="button" class="pill-primary-btn" onclick="window.UploadModal.open()" style="margin-top:16px;">
                        <span class="material-symbols-outlined icon-xs">upload_file</span>
                        <span>Upload Academic PDFs</span>
                    </button>
                </div>
            `;
            return;
        }

        // Generate dynamic questions derived from active document names
        const dynamicPrompts = docs.slice(0, 3).map(d => {
            const cleanTitle = d.filename.replace(/\.pdf$/i, "").replace(/[_-]/g, " ");
            return `Summarize the primary institutional objectives, research findings, and funding in ${d.filename}`;
        });

        container.innerHTML = `
            <div class="chat-empty-state">
                <span class="material-symbols-outlined chat-empty-icon">auto_awesome</span>
                <h2 class="chat-empty-title">Explore Your Academic Literature</h2>
                <p class="chat-empty-desc">
                    Ask grounded research questions across your ${docs.length} indexed document(s). 
                    All claims are verified with exact page-level citations.
                </p>
                <div class="suggested-prompts-grid">
                    ${dynamicPrompts.map(prompt => `
                        <button type="button" class="prompt-pill-btn" onclick="window.ChatModule.usePrompt('${this.escapeHtml(prompt)}')">
                            📄 ${this.escapeHtml(prompt.length > 60 ? prompt.substring(0, 57) + "..." : prompt)}
                        </button>
                    `).join("")}
                </div>
            </div>
        `;
    },

    usePrompt(text) {
        const input = document.getElementById("queryInput");
        if (input) {
            input.value = text;
            window.handleQuerySubmit(new Event("submit"));
        }
    },

    clear() {
        this.history = [];
        this.renderEmptyState();
    },

    handleScopeChange(val) {
        this.activeScope = val;
        ToastSystem.show(`Scope changed: ${val === 'ALL' ? 'All Documents' : val}`);
    },

    setAutoScroll(val) {
        this.autoScroll = val;
    },

    async askQuestion(query) {
        if (this.isGenerating) {
            this.stopGeneration();
            return;
        }

        this.isGenerating = true;
        this.userScrolledUp = false;
        this.activeAbortController = new AbortController();

        const msgId = "msg_" + Date.now();
        this.history.push({ id: msgId, query: query, answer: "" });

        const container = document.getElementById("chatMessages");
        if (container.querySelector(".chat-empty-state")) {
            container.innerHTML = "";
        }

        // Render User Message Bubble
        const userRow = document.createElement("div");
        userRow.className = "message-row user-message-row";
        userRow.innerHTML = `
            <div class="user-message-bubble">
                <span>${this.escapeHtml(query)}</span>
                <span class="user-msg-actions" title="Edit question" onclick="window.ChatModule.openQuestionEditor('${msgId}')">
                    <span class="material-symbols-outlined icon-xs">edit</span>
                </span>
            </div>
        `;
        container.appendChild(userRow);

        // Render Assistant Placeholder Card
        const assistantRow = document.createElement("div");
        assistantRow.className = "message-row assistant-message-row";
        assistantRow.id = `assistantRow_${msgId}`;
        assistantRow.innerHTML = `
            <div class="assistant-message-card">
                <div class="assistant-card-header">
                    <div class="assistant-brand">
                        <span class="material-symbols-outlined icon-xs">auto_awesome</span>
                        <span>RAISE Synthesis</span>
                    </div>
                    <span class="offline-badge-mini"><span class="status-dot"></span> Offline GraphRAG</span>
                </div>

                <!-- Thinking Deliberation Stages -->
                <div class="thought-accordion" id="thought_${msgId}">
                    <div class="thought-header">
                        <div class="thought-header-left">
                            <span class="material-symbols-outlined icon-xs">psychology</span>
                            <span id="thoughtStatus_${msgId}">Deliberating across document substrates...</span>
                        </div>
                        <span class="grounded-pill" id="groundedScore_${msgId}">Analyzing...</span>
                    </div>
                </div>

                <!-- Progressive Answer Markdown Body -->
                <div class="assistant-markdown" id="answerBody_${msgId}">
                    <span class="typing-caret"></span>
                </div>

                <!-- Actions Toolbar -->
                <div class="assistant-card-actions" id="actions_${msgId}" style="display:none;">
                    <button type="button" class="card-action-btn" onclick="window.ChatModule.copyAnswer('${msgId}')">
                        <span class="material-symbols-outlined icon-xs">content_copy</span>
                        <span>Copy</span>
                    </button>
                    <button type="button" class="card-action-btn" onclick="window.VoiceModule.speakAnswer('${msgId}')">
                        <span class="material-symbols-outlined icon-xs">volume_up</span>
                        <span>Read aloud</span>
                    </button>
                </div>
            </div>
        `;
        container.appendChild(assistantRow);
        this.scrollToBottom();

        const sendBtnIcon = document.getElementById("sendBtnIcon");
        if (sendBtnIcon) sendBtnIcon.textContent = "stop";

        try {
            const thoughtStatus = document.getElementById(`thoughtStatus_${msgId}`);
            const groundedScore = document.getElementById(`groundedScore_${msgId}`);

            if (thoughtStatus) thoughtStatus.textContent = "Reasoning across vector indices and property graph...";

            const response = await fetch("/api/graphrag/subgraph-query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                signal: this.activeAbortController.signal,
                body: JSON.stringify({
                    query: query,
                    hops: 2,
                    top_k: 4,
                    document_filter: this.activeScope !== "ALL" ? this.activeScope : null
                })
            });

            const data = await response.json();
            const rawAnswer = data.grounded_answer || data.answer || "Please upload an academic PDF to begin your research.";
            const citations = data.citations || [];
            const score = data.traceability_score ? Math.round(data.traceability_score * 100) : 0;
            
            const uniqueSources = new Set(citations.map(c => c.pdf_filename || c.university)).size || (data.sources_count || 0);

            if (thoughtStatus) {
                thoughtStatus.textContent = data.query_type === "EMPTY_WORKSPACE" 
                    ? "Notice: No documents active in workspace"
                    : `Completed reasoning across ${uniqueSources} source(s)`;
            }
            if (groundedScore) {
                groundedScore.textContent = score > 0 
                    ? `✓ Grounded ${score}% · ${uniqueSources} sources`
                    : "Zero-document state";
            }

            // Stream Answer Text Token by Token
            await this.streamAnswerText(msgId, rawAnswer, citations);

            // Load Citations into Evidence Drawer
            if (citations.length > 0) {
                EvidenceDrawer.loadCitations(citations);
            }

            const actions = document.getElementById(`actions_${msgId}`);
            if (actions) actions.style.display = "flex";

        } catch (err) {
            if (err.name === "AbortError") {
                const answerBody = document.getElementById(`answerBody_${msgId}`);
                if (answerBody) answerBody.innerHTML += `<p style="color:var(--text-muted); font-size:13px; margin-top:8px;">[Generation stopped by user]</p>`;
            } else {
                console.error("Query failed:", err);
                const answerBody = document.getElementById(`answerBody_${msgId}`);
                if (answerBody) answerBody.innerHTML = `<p style="color:#f87171;">Query error: ${err.message}</p>`;
            }
        } finally {
            this.isGenerating = false;
            this.activeAbortController = null;
            if (sendBtnIcon) sendBtnIcon.textContent = "north_east";
        }
    },

    async streamAnswerText(msgId, fullText, citations) {
        const container = document.getElementById(`answerBody_${msgId}`);
        if (!container) return;

        const tokens = fullText.split(" ");
        let currentText = "";

        for (let i = 0; i < tokens.length; i++) {
            if (!this.isGenerating) break; // Terminate if user clicked Stop

            currentText += (i === 0 ? "" : " ") + tokens[i];
            let html = this.formatMarkdown(currentText);
            container.innerHTML = html + `<span class="typing-caret"></span>`;

            if (this.autoScroll && i % 4 === 0) {
                this.scrollToBottom();
            }
            await new Promise(r => setTimeout(r, 20));
        }

        container.innerHTML = this.formatMarkdown(fullText);
        this.attachCitationClickHandlers(container);
        if (this.autoScroll) this.scrollToBottom();
    },

    formatMarkdown(text) {
        let html = text
            .replace(/^### (.*$)/gim, '<h3 class="md-h3">$1</h3>')
            .replace(/^## (.*$)/gim, '<h2 class="md-h2">$1</h2>')
            .replace(/^# (.*$)/gim, '<h1 class="md-h1">$1</h1>')
            .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/gim, '<em>$1</em>')
            .replace(/^\s*[-*]\s+(.*$)/gim, '<li>$1</li>')
            .replace(/\[(\d+)\]/g, '<span class="inline-citation-pill" data-citation="$1">[$1]</span>');

        // Wrap loose lists
        html = html.replace(/(<li>.*<\/li>)/gims, '<ul class="md-list">$1</ul>');
        html = html.replace(/\n\n/g, '<br><br>');
        return html;
    },

    attachCitationClickHandlers(container) {
        container.querySelectorAll(".inline-citation-pill").forEach(pill => {
            pill.addEventListener("click", () => {
                const citId = pill.getAttribute("data-citation");
                EvidenceDrawer.open();
                EvidenceDrawer.highlightCitation(citId);
            });
        });
    },

    copyAnswer(msgId) {
        const target = this.history.find(h => h.id === msgId);
        const text = target ? target.answer : document.getElementById(`answerBody_${msgId}`)?.innerText;
        if (text) {
            navigator.clipboard.writeText(text);
            ToastSystem.show("Answer copied to clipboard!");
        }
    },

    openQuestionEditor(msgId) {
        const target = this.history.find(h => h.id === msgId);
        if (!target) return;
        const input = document.getElementById("queryInput");
        if (input) {
            input.value = target.query;
            input.focus();
            ToastSystem.show("Question loaded into composer");
        }
    },

    escapeHtml(str) {
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
};

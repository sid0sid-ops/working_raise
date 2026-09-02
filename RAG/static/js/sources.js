/** Sources & Document Management Module */
import { ToastSystem } from './toast.js';

export const SourcesModule = {
    documents: [],

    async loadDocuments() {
        try {
            const res = await fetch("/api/documents");
            const data = await res.json();
            this.documents = data.documents || [];
            this.renderDocuments(this.documents);
            this.updateScopeDropdown(this.documents);
        } catch (e) {
            console.error("Failed to load documents:", e);
        }
    },

    renderDocuments(docs) {
        const container = document.getElementById("documentListContainer");
        const badge = document.getElementById("sourceCountBadge");
        const omnibarCount = document.getElementById("selectedSourcesCount");
        
        if (badge) badge.textContent = `${docs.length} PDFs`;
        if (omnibarCount) omnibarCount.textContent = `${docs.length} documents active`;

        if (!docs || docs.length === 0) {
            container.innerHTML = `
                <div class="source-empty-state">
                    <span class="material-symbols-outlined source-empty-icon">picture_as_pdf</span>
                    <span class="source-empty-title">No sources loaded yet</span>
                    <span class="source-empty-desc">Click "Add academic PDF" or load the pre-indexed vault.</span>
                </div>
            `;
            return;
        }

        container.innerHTML = docs.map((doc, idx) => `
            <div class="source-item-card" id="docCard_${idx}">
                <div class="source-item-left">
                    <div class="source-pdf-badge">PDF</div>
                    <div class="source-item-info">
                        <div class="source-item-filename" title="${doc.filename}">${doc.filename}</div>
                        <div class="source-item-sub">${doc.pages || 1} pages · ${doc.size_mb || 0.5} MB · Ready</div>
                    </div>
                </div>
                <div class="source-item-actions">
                    <a href="/api/pdf/${encodeURIComponent(doc.filename)}" target="_blank" class="panel-icon-btn" title="Open PDF">
                        <span class="material-symbols-outlined icon-xs">open_in_new</span>
                    </a>
                    <button type="button" class="panel-icon-btn" title="Delete document" onclick="window.SourcesModule.deleteDocument('${doc.filename}')">
                        <span class="material-symbols-outlined icon-xs">close</span>
                    </button>
                </div>
            </div>
        `).join("");
    },

    updateScopeDropdown(docs) {
        const select = document.getElementById("sourceScopeSelect");
        if (!select) return;
        
        const currentVal = select.value;
        let html = `<option value="ALL">Sources: All Indexed Documents (${docs.length})</option>`;
        docs.forEach(d => {
            html += `<option value="${d.filename}">Doc: ${d.filename}</option>`;
        });
        select.innerHTML = html;
        if (currentVal && docs.some(d => d.filename === currentVal)) {
            select.value = currentVal;
        }
    },

    toggleSelectAll() {
        const chk = document.getElementById("selectAllCheckbox");
        if (chk) chk.checked = !chk.checked;
    },

    async deleteDocument(filename) {
        if (!confirm(`Remove "${filename}" from active sources?`)) return;
        try {
            const res = await fetch("/api/documents/delete", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename })
            });
            const data = await res.json();
            ToastSystem.show(`Removed ${filename}`);
            if (data.documents) {
                this.documents = data.documents;
                this.renderDocuments(this.documents);
                this.updateScopeDropdown(this.documents);
            } else {
                await this.loadDocuments();
            }
        } catch (e) {
            console.error("Delete failed:", e);
            ToastSystem.show(`Failed to remove document`);
        }
    },

    async handleUpload(files) {
        if (!files) return;
        const fileList = Array.isArray(files) ? files : (files.length !== undefined ? Array.from(files) : [files]);
        const validPdfs = fileList.filter(f => f && f.name && f.name.toLowerCase().endsWith(".pdf"));
        if (validPdfs.length === 0) {
            ToastSystem.show("Please select valid academic PDF file(s).");
            return;
        }

        const pbox = document.getElementById("uploadProgressBox");
        const pfill = document.getElementById("uploadProgressBarFill");
        const pstatus = document.getElementById("uploadProgressStatusText");
        
        if (pbox) pbox.classList.remove("hidden");
        if (pfill) { pfill.style.width = "20%"; pfill.style.background = "var(--accent-color)"; }
        if (pstatus) pstatus.textContent = `Uploading ${validPdfs.length} PDF(s)...`;

        const formData = new FormData();
        validPdfs.forEach(f => formData.append("files", f));

        try {
            if (pfill) pfill.style.width = "50%";
            if (pstatus) pstatus.textContent = "Extracting text structure & dense embeddings...";

            const res = await fetch("/api/upload-academic-pdfs", {
                method: "POST",
                body: formData
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Upload failed");
            }

            if (pfill) pfill.style.width = "90%";
            if (pstatus) pstatus.textContent = "Building knowledge graph & indexing...";

            const result = await res.json();
            if (pfill) pfill.style.width = "100%";
            if (pstatus) pstatus.textContent = "Indexing Complete!";

            setTimeout(() => {
                if (window.UploadModal) window.UploadModal.close();
                this.loadDocuments();
                if (window.HomeModule) window.HomeModule.loadNotebooks();
                ToastSystem.show(`Successfully indexed ${validPdfs.length} document(s)!`);
                // If on Home Hub, switch into research workspace
                if (document.getElementById("homeView").classList.contains("active")) {
                    window.AppRouter.showWorkspace();
                }
            }, 600);

        } catch (err) {
            console.error("Upload error:", err);
            if (pstatus) pstatus.textContent = `Upload error: ${err.message}`;
            if (pfill) pfill.style.background = "#ef4444";
        }
    }
};

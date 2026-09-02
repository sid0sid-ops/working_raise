/** Home Dashboard & Research Hub Dynamic Module */
export const HomeModule = {
    async loadNotebooks() {
        const grid = document.getElementById("notebookGrid");
        const emptyState = document.getElementById("emptyHubState");
        if (!grid) return;

        try {
            const res = await fetch("/api/documents");
            const data = await res.json();
            const docs = data.documents || [];

            if (docs.length === 0) {
                grid.innerHTML = `
                    <div class="create-notebook-card" onclick="window.UploadModal.open()">
                        <div class="create-icon-wrapper">
                            <span class="material-symbols-outlined create-plus-icon">upload_file</span>
                        </div>
                        <span class="create-card-title">Upload Academic PDFs</span>
                        <span class="create-card-desc">Add institutional reports, extract knowledge graphs, and ground Q&A</span>
                    </div>
                `;
                if (emptyState) emptyState.style.display = "flex";
                return;
            }

            if (emptyState) emptyState.style.display = "none";

            let cardsHtml = `
                <div class="create-notebook-card" onclick="window.UploadModal.open()">
                    <div class="create-icon-wrapper">
                        <span class="material-symbols-outlined create-plus-icon">upload_file</span>
                    </div>
                    <span class="create-card-title">Upload Academic PDFs</span>
                    <span class="create-card-desc">Add more institutional reports or research papers</span>
                </div>
            `;

            docs.forEach((doc, idx) => {
                cardsHtml += `
                    <div class="notebook-card" onclick="window.HomeModule.openDocumentWorkspace('${encodeURIComponent(doc.filename)}')">
                        <div class="notebook-card-icon-row">
                            <span class="material-symbols-outlined notebook-icon">menu_book</span>
                            <span class="notebook-card-menu" onclick="event.stopPropagation(); window.SourcesModule.deleteDocument('${doc.filename}')" title="Delete document">
                                <span class="material-symbols-outlined icon-xs">delete</span>
                            </span>
                        </div>
                        <div class="notebook-card-info">
                            <h3 class="notebook-name">${doc.filename}</h3>
                            <p class="notebook-meta">${doc.pages || 1} pages · ${doc.size_mb || 0.5} MB · Grounded</p>
                        </div>
                    </div>
                `;
            });

            grid.innerHTML = cardsHtml;
        } catch (e) {
            console.error("Failed to load home notebooks:", e);
        }
    },

    openDocumentWorkspace(filename) {
        const decoded = decodeURIComponent(filename);
        window.AppRouter.openNotebook(decoded);
        const scopeSelect = document.getElementById("sourceScopeSelect");
        if (scopeSelect) scopeSelect.value = decoded;
    }
};

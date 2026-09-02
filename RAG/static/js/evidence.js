/** Evidence Drawer Module */
export const EvidenceDrawer = {
    citations: [],

    open() {
        const drawer = document.getElementById("evidenceDrawer");
        if (drawer) drawer.classList.remove("hidden");
    },

    close() {
        const drawer = document.getElementById("evidenceDrawer");
        if (drawer) drawer.classList.add("hidden");
    },

    toggle() {
        const drawer = document.getElementById("evidenceDrawer");
        if (drawer) drawer.classList.toggle("hidden");
    },

    loadCitations(citations) {
        this.citations = citations || [];
        const container = document.getElementById("evidenceDrawerBody");
        const sCount = document.getElementById("evidenceSourceCount");
        const pCount = document.getElementById("evidencePassageCount");

        const uniqueDocs = new Set(this.citations.map(c => c.pdf_filename)).size;
        if (sCount) sCount.textContent = `${uniqueDocs} sources`;
        if (pCount) pCount.textContent = `${this.citations.length} passages`;

        if (!this.citations || this.citations.length === 0) {
            container.innerHTML = `
                <div class="evidence-empty-state">
                    <span class="material-symbols-outlined">travel_explore</span>
                    <p>Click any inline citation badge (e.g. [1], [2]) to inspect grounded evidence.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.citations.map((c, idx) => {
            const pageNum = c.primary_page || 1;
            const pdfName = c.pdf_filename || "Annual Report.pdf";
            return `
                <div class="evidence-card" id="evidenceCard_${idx + 1}">
                    <div class="evidence-card-header">
                        <span class="evidence-card-doc">[${idx + 1}] ${pdfName}</span>
                        <span class="evidence-card-page">Page ${pageNum}</span>
                    </div>
                    <div class="evidence-card-text">${c.plain_text || c.text || "Passage excerpt"}</div>
                    <a href="/api/pdf/${encodeURIComponent(pdfName)}#page=${pageNum}" target="_blank" class="evidence-link-btn">
                        <span class="material-symbols-outlined icon-xs">open_in_new</span>
                        <span>Open in PDF (Page ${pageNum})</span>
                    </a>
                </div>
            `;
        }).join("");
    },

    highlightCitation(index) {
        this.open();
        const card = document.getElementById(`evidenceCard_${index}`);
        if (card) {
            card.scrollIntoView({ behavior: "smooth", block: "center" });
            card.style.borderColor = "var(--accent-blue)";
            card.style.background = "var(--card-surface-high)";
            setTimeout(() => {
                card.style.borderColor = "";
                card.style.background = "";
            }, 1800);
        }
    }
};

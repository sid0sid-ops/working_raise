/** Router & Navigation Module */
import { ToastSystem } from './toast.js';
import { SourcesModule } from './sources.js';
import { ChatModule } from './chat.js';

export const AppRouter = {
    currentNotebook: "Academic Research Workspace",

    init() {
        this.showHome();
        SourcesModule.loadDocuments();
    },

    showHome() {
        document.getElementById("homeView").classList.add("active");
        document.getElementById("workspaceView").classList.remove("active");
        if (window.HomeModule) window.HomeModule.loadNotebooks();
    },

    showWorkspace() {
        document.getElementById("homeView").classList.remove("active");
        document.getElementById("workspaceView").classList.add("active");
    },

    openNotebook(name) {
        this.currentNotebook = name;
        const titleInput = document.getElementById("projectTitleInput");
        if (titleInput) titleInput.value = name;
        this.showWorkspace();
        SourcesModule.loadDocuments();
        ChatModule.renderEmptyState();
        ToastSystem.show(`Opened research notebook: ${name}`);
    },

    openCreateNotebookModal() {
        document.getElementById("newNotebookModal").classList.remove("hidden");
        document.getElementById("newNotebookName").focus();
    },

    closeCreateNotebookModal() {
        document.getElementById("newNotebookModal").classList.add("hidden");
    },

    submitCreateNotebook() {
        const nameInput = document.getElementById("newNotebookName");
        const name = nameInput.value.trim() || "Untitled research notebook";
        this.closeCreateNotebookModal();
        this.openNotebook(name);
        ChatModule.clear();
        this.openUploadModal();
    },

    openUploadModal() {
        document.getElementById("uploadModal").classList.remove("hidden");
    },

    closeUploadModal() {
        document.getElementById("uploadModal").classList.add("hidden");
        const pbox = document.getElementById("uploadProgressBox");
        if (pbox) pbox.classList.add("hidden");
    },

    async ingestVaultAndOpen() {
        const pbox = document.getElementById("uploadProgressBox");
        const pfill = document.getElementById("uploadProgressBarFill");
        const pstatus = document.getElementById("uploadProgressStatusText");
        
        pbox.classList.remove("hidden");
        pfill.style.width = "30%";
        pstatus.textContent = "Scanning and indexing pre-indexed reports in vault...";

        try {
            const resp = await fetch("/api/vault/load-defaults", { method: "POST" });
            const data = await resp.json();
            pfill.style.width = "100%";
            pstatus.textContent = "Vault loaded successfully!";
            
            setTimeout(() => {
                this.closeUploadModal();
                SourcesModule.loadDocuments();
                ToastSystem.show("Academic Reports Vault synchronized!");
            }, 600);
        } catch (e) {
            pstatus.textContent = "Notice: Loading local manifest cache...";
            setTimeout(() => {
                this.closeUploadModal();
                SourcesModule.loadDocuments();
            }, 600);
        }
    }
};

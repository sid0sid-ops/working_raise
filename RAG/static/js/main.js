/** Main Root Orchestrator */
import { ToastSystem } from './toast.js';
import { AppRouter } from './router.js';
import { SourcesModule } from './sources.js';
import { ChatModule } from './chat.js';
import { EvidenceDrawer } from './evidence.js';
import { VoiceModule } from './voice.js';
import { SettingsModal } from './settings.js';
import { StudioModule } from './studio.js';
import { HomeModule } from './home.js';

// Expose modules to window for inline onclick handlers
window.ToastSystem = ToastSystem;
window.AppRouter = AppRouter;
window.SourcesModule = SourcesModule;
window.ChatModule = ChatModule;
window.EvidenceDrawer = EvidenceDrawer;
window.VoiceModule = VoiceModule;
window.SettingsModal = SettingsModal;
window.StudioModule = StudioModule;
window.HomeModule = HomeModule;

window.UploadModal = {
    open() {
        const modal = document.getElementById("uploadModal");
        if (modal) modal.classList.remove("hidden");
    },
    close() {
        const modal = document.getElementById("uploadModal");
        if (modal) modal.classList.add("hidden");
        const pbox = document.getElementById("uploadProgressBox");
        if (pbox) pbox.classList.add("hidden");
        const fileInput = document.getElementById("modalFileInput");
        if (fileInput) fileInput.value = "";
    },
    handleFileInput(event) {
        const files = event.target.files;
        if (files && files.length > 0) {
            SourcesModule.handleUpload(files);
        }
    }
};

window.HeaderModule = {
    handleTitleChange(val) {
        AppRouter.currentNotebook = val.trim() || "Untitled research notebook";
    }
};

window.TabModule = {
    switchTab(tabName) {
        document.querySelectorAll(".mobile-tab").forEach(t => t.classList.remove("active"));
        const activeTab = document.getElementById(`tab-${tabName}`);
        if (activeTab) activeTab.classList.add("active");

        const sPanel = document.getElementById("sourcePanel");
        const cPanel = document.getElementById("chatViewport");
        const gPanel = document.getElementById("studioViewport");

        if (tabName === "sources") {
            sPanel.style.display = "flex";
            cPanel.style.display = "none";
            gPanel.style.display = "none";
        } else if (tabName === "chat") {
            sPanel.style.display = "none";
            cPanel.style.display = "flex";
            gPanel.style.display = "none";
        } else if (tabName === "studio") {
            sPanel.style.display = "none";
            cPanel.style.display = "none";
            gPanel.style.display = "flex";
        }
    }
};

window.handleQuerySubmit = function(event) {
    if (event) event.preventDefault();
    if (ChatModule.isGenerating) {
        ChatModule.stopGeneration();
        return;
    }
    const input = document.getElementById("queryInput");
    if (!input) return;
    const query = input.value.trim();
    if (!query) return;

    input.value = "";
    input.style.height = "auto";
    ChatModule.askQuestion(query);
};

window.handleKeyDown = function(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        window.handleQuerySubmit(event);
    }
};

window.handleInputChange = function(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
};

window.handleModalFileUpload = function(event) {
    const files = event.target.files;
    if (files && files.length > 0) {
        SourcesModule.handleUpload(files);
    }
};

window.clearConversation = function() {
    if (confirm("Clear current research conversation?")) {
        ChatModule.clear();
        ToastSystem.show("Conversation cleared");
    }
};

// Bootstrap on DOM Ready
document.addEventListener("DOMContentLoaded", () => {
    AppRouter.init();
    ChatModule.init();
    HomeModule.loadNotebooks();
});

/** Settings Modal Module */
export const SettingsModal = {
    open() {
        const modal = document.getElementById("settingsModal");
        if (modal) modal.classList.remove("hidden");
    },
    close() {
        const modal = document.getElementById("settingsModal");
        if (modal) modal.classList.add("hidden");
    }
};

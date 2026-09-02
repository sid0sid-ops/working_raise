/** Knowledge Graph Studio Module */
export const StudioModule = {
    async runCypher() {
        const input = document.getElementById("cypherInput");
        const output = document.getElementById("cypherOutput");
        const q = input.value.trim() || "MATCH (n) RETURN n LIMIT 10";

        try {
            const res = await fetch("/api/neo4j/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: q })
            });
            const data = await res.json();
            output.textContent = JSON.stringify(data, null, 2);
        } catch (e) {
            output.textContent = "Error executing Cypher: " + e.message;
        }
    }
};

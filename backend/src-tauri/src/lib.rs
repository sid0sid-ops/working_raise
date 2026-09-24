use serde::{Deserialize, Serialize};
use std::fs::OpenOptions;
use std::io::Write;
use std::net::TcpStream;
use std::time::Duration;
use sysinfo::System;
use tauri::Emitter;

#[derive(Debug, Serialize, Deserialize)]
pub struct HardwareTelemetry {
    pub platform: String,
    pub os_name: String,
    pub total_ram_gb: f32,
    pub free_ram_gb: f32,
    pub cpu_cores: usize,
    pub ollama_running: bool,
    pub recommended_mode: String,
    pub recommendation_note: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ModelPullProgress {
    pub status: String,
    pub completed: u64,
    pub total: u64,
    pub percent: f32,
}

// 1. Hardware Detection Command
#[tauri::command]
pub fn get_system_hardware() -> HardwareTelemetry {
    let mut sys = System::new_all();
    sys.refresh_all();

    let total_ram = (sys.total_memory() as f32) / (1024.0 * 1024.0 * 1024.0);
    let free_ram = (sys.available_memory() as f32) / (1024.0 * 1024.0 * 1024.0);
    let cpu_cores = sys.cpus().len();

    // Check if Ollama is running locally on port 11434
    let ollama_running = TcpStream::connect_timeout(
        &"127.0.0.1:11434".parse().unwrap(),
        Duration::from_millis(400),
    )
    .is_ok();

    let (recommended_mode, recommendation_note) = if total_ram >= 16.0 {
        (
            "hybrid".to_string(),
            "Hardware supports both Local (Llama 3.2 / Qwen 2.5) and Cloud AI.".to_string(),
        )
    } else {
        (
            "cloud".to_string(),
            "Cloud Profile (Groq / Gemini) recommended for maximum speed.".to_string(),
        )
    };

    HardwareTelemetry {
        platform: std::env::consts::OS.to_string(),
        os_name: System::long_os_version().unwrap_or_else(|| "Unknown OS".to_string()),
        total_ram_gb: (total_ram * 10.0).round() / 10.0,
        free_ram_gb: (free_ram * 10.0).round() / 10.0,
        cpu_cores,
        ollama_running,
        recommended_mode,
        recommendation_note,
    }
}

// 2. Save Configuration to .env Command
#[tauri::command]
pub fn save_configuration(config_json: String) -> Result<String, String> {
    let mut file = OpenOptions::new()
        .write(true)
        .create(true)
        .append(true)
        .open(".env")
        .map_err(|e| e.to_string())?;

    writeln!(file, "\n# Updated via RAISE Control Center").map_err(|e| e.to_string())?;
    writeln!(file, "# Config: {}", config_json).map_err(|e| e.to_string())?;
    Ok("Configuration saved successfully".into())
}

// 3. Model Download Stream Event Dispatcher
#[tauri::command]
pub async fn pull_local_model(
    app: tauri::AppHandle,
    model_name: String,
) -> Result<String, String> {
    let client = reqwest::Client::new();
    let url = "http://127.0.0.1:11434/api/pull";

    let payload = serde_json::json!({
        "name": model_name,
        "stream": true
    });

    let resp = client
        .post(url)
        .json(&payload)
        .send()
        .await
        .map_err(|e| format!("Failed to connect to Ollama: {}", e))?;

    use futures_util::StreamExt;
    let mut stream = resp.bytes_stream();

    while let Some(chunk_res) = stream.next().await {
        if let Ok(chunk) = chunk_res {
            if let Ok(text) = std::str::from_utf8(&chunk) {
                for line in text.lines() {
                    if let Ok(val) = serde_json::from_str::<serde_json::Value>(line) {
                        let status = val["status"].as_str().unwrap_or("downloading").to_string();
                        let completed = val["completed"].as_u64().unwrap_or(0);
                        let total = val["total"].as_u64().unwrap_or(1);
                        let percent = if total > 0 {
                            (completed as f32 / total as f32) * 100.0
                        } else {
                            0.0
                        };

                        let _ = app.emit(
                            "model-pull-progress",
                            ModelPullProgress {
                                status,
                                completed,
                                total,
                                percent,
                            },
                        );
                    }
                }
            }
        }
    }

    Ok("Model pull completed".into())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_system_hardware,
            save_configuration,
            pull_local_model
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

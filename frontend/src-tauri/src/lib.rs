use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use tauri::{Manager, RunEvent};

struct SidecarState(Arc<Mutex<Option<Child>>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  let sidecar_child = Arc::new(Mutex::new(None));
  let sidecar_child_clone = sidecar_child.clone();

  tauri::Builder::default()
    .manage(SidecarState(sidecar_child.clone()))
    .setup(move |app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      // Spawning FastAPI backend process relative to current run path
      // In development mode, the path is ../backend/venv/Scripts/python.exe
      #[cfg(target_os = "windows")]
      let python_path = "../backend/venv/Scripts/python.exe";
      #[cfg(not(target_os = "windows"))]
      let python_path = "../backend/venv/bin/python";

      println!("Tauri Sidecar: Launching FastAPI backend server at {}", python_path);
      
      let child = Command::new(python_path)
        .args(&["-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"])
        .current_dir("../backend")
        .spawn();

      match child {
        Ok(proc) => {
          println!("Tauri Sidecar: FastAPI backend successfully spawned with PID {}", proc.id());
          let mut guard = sidecar_child_clone.lock().unwrap();
          *guard = Some(proc);
        }
        Err(e) => {
          eprintln!("Tauri Sidecar: Failed to launch backend sidecar: {:?}", e);
        }
      }

      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("error while building tauri application")
    .run(move |app_handle, event| {
      if let RunEvent::Exit = event {
        println!("Tauri Sidecar: Application exiting, cleaning up sidecar process.");
        let state = app_handle.state::<SidecarState>();
        let mut guard = state.0.lock().unwrap();
        if let Some(mut child) = guard.take() {
          match child.kill() {
            Ok(_) => println!("Tauri Sidecar: FastAPI backend successfully terminated."),
            Err(e) => eprintln!("Tauri Sidecar: Failed to kill backend sidecar process: {:?}", e),
          }
        }
      }
    });
}

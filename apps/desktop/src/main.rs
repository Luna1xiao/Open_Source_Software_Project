use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;

use tauri::{AppHandle, Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};

struct BackendState(Mutex<Option<Child>>);

fn main() {
    tauri::Builder::default()
        .manage(BackendState(Mutex::new(None)))
        .setup(|app| {
            let port = reserve_port()?;
            let child = spawn_backend(app.handle(), port)?;
            {
                let state = app.state::<BackendState>();
                let mut guard = state.0.lock().map_err(|_| "failed to lock backend state")?;
                *guard = Some(child);
            }

            wait_for_backend(port)?;

            WebviewWindowBuilder::new(app, "main", WebviewUrl::default())
                .title("Mercury Desktop")
                .inner_size(1440.0, 900.0)
                .initialization_script(&format!("window.__BACKEND_PORT__ = {};", port))
                .build()
                .map_err(|err| err.to_string())?;

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building mercury desktop")
        .run(|app_handle, event| {
            if matches!(event, RunEvent::Exit) {
                kill_backend(app_handle);
            }
        });
}

fn reserve_port() -> Result<u16, String> {
    let listener = TcpListener::bind("127.0.0.1:0").map_err(|err| err.to_string())?;
    let port = listener.local_addr().map_err(|err| err.to_string())?.port();
    drop(listener);
    Ok(port)
}

fn spawn_backend(app: &AppHandle, port: u16) -> Result<Child, String> {
    if cfg!(debug_assertions) {
        let backend_dir = repo_root().join("backend");
        return spawn_dev_backend(backend_dir, port);
    }

    let binary_path = sidecar_binary_path(app)?;
    Command::new(binary_path)
        .env("MERCURY_PORT", port.to_string())
        .spawn()
        .map_err(|err| err.to_string())
}

fn spawn_dev_backend(backend_dir: PathBuf, port: u16) -> Result<Child, String> {
    let port_value = port.to_string();

    if let Ok(child) = Command::new("uv")
        .args(["run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", &port_value])
        .env("MERCURY_PORT", &port_value)
        .current_dir(&backend_dir)
        .spawn()
    {
        return Ok(child);
    }

    if let Ok(child) = Command::new("py")
        .args(["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", &port_value])
        .env("MERCURY_PORT", &port_value)
        .current_dir(&backend_dir)
        .spawn()
    {
        return Ok(child);
    }

    Command::new("python")
        .args(["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", &port_value])
        .env("MERCURY_PORT", &port_value)
        .current_dir(backend_dir)
        .spawn()
        .map_err(|err| err.to_string())
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

fn sidecar_binary_path(app: &AppHandle) -> Result<PathBuf, String> {
    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|err| err.to_string())?;
    let executable = if cfg!(target_os = "windows") {
        "mercury-backend.exe"
    } else {
        "mercury-backend"
    };
    Ok(resource_dir.join("binaries").join(executable))
}

fn wait_for_backend(port: u16) -> Result<(), String> {
    for _ in 0..40 {
        if healthcheck(port) {
            return Ok(());
        }
        std::thread::sleep(Duration::from_millis(250));
    }
    Err(format!("backend did not become healthy on port {}", port))
}

fn healthcheck(port: u16) -> bool {
    let address = format!("127.0.0.1:{}", port);
    let mut stream = match TcpStream::connect(address) {
        Ok(stream) => stream,
        Err(_) => return false,
    };

    let request = b"GET /healthz HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
    if stream.write_all(request).is_err() {
        return false;
    }

    let mut response = String::new();
    if stream.read_to_string(&mut response).is_err() {
        return false;
    }

    response.contains("\"status\":\"ok\"")
}

fn kill_backend(app_handle: &AppHandle) {
    let state = app_handle.state::<BackendState>();
    let lock_result = state.0.lock();
    if let Ok(mut guard) = lock_result {
        if let Some(child) = guard.as_mut() {
            let _ = child.kill();
        }
        *guard = None;
    }
}

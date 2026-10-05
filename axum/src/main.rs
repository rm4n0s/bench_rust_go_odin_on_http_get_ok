use axum::{http::header, routing::get, Router};

async fn root() -> ([(header::HeaderName, &'static str); 1], &'static str) {
    ([(header::CONTENT_TYPE, "text/plain; charset=utf-8")], "")
}

async fn health() -> ([(header::HeaderName, &'static str); 1], &'static str) {
    ([(header::CONTENT_TYPE, "text/plain; charset=utf-8")], "ok")
}

fn main() {
    // Worker thread count comes from TOKIO_WORKER_THREADS (tokio default = all cores).
    tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .unwrap()
        .block_on(async {
            let app = Router::new().route("/", get(root)).route("/health", get(health));
            let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await.unwrap();
            axum::serve(listener, app).await.unwrap();
        });
}

use axum::{routing::get, Json, Router};
use rmcp::{
    ErrorData as McpError, ServerHandler,
    handler::server::router::tool::ToolRouter,
    handler::server::wrapper::Parameters,
    model::*,
    schemars, tool, tool_handler, tool_router,
    transport::streamable_http_server::{
        session::local::LocalSessionManager, StreamableHttpService,
    },
};
use serde_json::Value;
use std::time::Instant;

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
struct FibonacciParams {
    /// The position in the Fibonacci sequence (0-40)
    n: i64,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
struct FetchParams {
    /// URL to fetch data from
    endpoint: String,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
struct ProcessJsonParams {
    /// JSON data to process
    data: Value,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
struct DbQueryParams {
    /// SQL query string
    query: String,
    /// Simulated delay in milliseconds
    delay_ms: u64,
}

fn fibonacci(n: u32) -> u64 {
    if n <= 1 {
        return n as u64;
    }
    fibonacci(n - 1) + fibonacci(n - 2)
}

fn uppercase_values(value: &Value) -> Value {
    match value {
        Value::String(s) => Value::String(s.to_uppercase()),
        Value::Object(map) => {
            let new_map: serde_json::Map<String, Value> = map
                .iter()
                .map(|(k, v)| (k.clone(), uppercase_values(v)))
                .collect();
            Value::Object(new_map)
        }
        Value::Array(arr) => Value::Array(arr.iter().map(uppercase_values).collect()),
        other => other.clone(),
    }
}

#[derive(Clone)]
struct BenchmarkServer {
    tool_router: ToolRouter<Self>,
    http_client: reqwest::Client,
}

#[tool_router]
impl BenchmarkServer {
    fn new(http_client: reqwest::Client) -> Self {
        Self {
            tool_router: Self::tool_router(),
            http_client,
        }
    }

    #[tool(description = "Calculate a Fibonacci number recursively (CPU-bound)")]
    fn calculate_fibonacci(
        &self,
        Parameters(params): Parameters<FibonacciParams>,
    ) -> Result<CallToolResult, McpError> {
        if params.n < 0 {
            return Ok(CallToolResult::error(vec![Content::text(
                "n must be between 0 and 40",
            )]));
        }
        if params.n > 40 {
            return Ok(CallToolResult::error(vec![Content::text(
                "n must be between 0 and 40",
            )]));
        }
        let n = params.n as u32;
        let result = fibonacci(n);
        let response = serde_json::json!({
            "input": params.n,
            "result": result,
            "server_type": "rust"
        });
        Ok(CallToolResult::success(vec![Content::text(
            response.to_string(),
        )]))
    }

    #[tool(description = "Fetch data from an external HTTP endpoint")]
    async fn fetch_external_data(
        &self,
        Parameters(params): Parameters<FetchParams>,
    ) -> Result<CallToolResult, McpError> {
        let start = Instant::now();
        match self.http_client.get(&params.endpoint).send().await {
            Ok(resp) => {
                let status = resp.status().as_u16();
                let elapsed = start.elapsed().as_millis();
                let response = serde_json::json!({
                    "url": params.endpoint,
                    "status_code": status,
                    "response_time_ms": elapsed,
                    "server_type": "rust"
                });
                Ok(CallToolResult::success(vec![Content::text(
                    response.to_string(),
                )]))
            }
            Err(e) => Ok(CallToolResult::error(vec![Content::text(format!(
                "Request failed: {}",
                e
            ))])),
        }
    }

    #[tool(description = "Process JSON data by uppercasing all string values")]
    fn process_json_data(
        &self,
        Parameters(params): Parameters<ProcessJsonParams>,
    ) -> Result<CallToolResult, McpError> {
        let original_keys: Vec<String> = if let Value::Object(map) = &params.data {
            map.keys().cloned().collect()
        } else {
            vec![]
        };
        let transformed = uppercase_values(&params.data);
        let response = serde_json::json!({
            "original_keys": original_keys,
            "transformed_data": transformed,
            "server_type": "rust"
        });
        Ok(CallToolResult::success(vec![Content::text(
            response.to_string(),
        )]))
    }

    #[tool(description = "Simulate a database query with configurable delay")]
    async fn simulate_database_query(
        &self,
        Parameters(params): Parameters<DbQueryParams>,
    ) -> Result<CallToolResult, McpError> {
        if params.delay_ms > 5000 {
            return Ok(CallToolResult::error(vec![Content::text(
                "delay_ms must be between 0 and 5000",
            )]));
        }
        tokio::time::sleep(std::time::Duration::from_millis(params.delay_ms)).await;
        let timestamp = chrono::Utc::now().to_rfc3339();
        let response = serde_json::json!({
            "query": params.query,
            "delay_ms": params.delay_ms,
            "timestamp": timestamp,
            "server_type": "rust"
        });
        Ok(CallToolResult::success(vec![Content::text(
            response.to_string(),
        )]))
    }
}

#[tool_handler]
impl ServerHandler for BenchmarkServer {
    fn get_info(&self) -> ServerInfo {
        ServerInfo {
            protocol_version: ProtocolVersion::V_2024_11_05,
            capabilities: ServerCapabilities::builder().enable_tools().build(),
            server_info: Implementation {
                name: "mcp-rust-server".to_string(),
                version: "0.1.0".to_string(),
                ..Default::default()
            },
            instructions: Some("Rust MCP benchmark server".into()),
        }
    }
}

async fn health() -> Json<Value> {
    Json(serde_json::json!({
        "status": "ok",
        "server_type": "rust"
    }))
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .unwrap();
    let service = StreamableHttpService::new(
        move || Ok(BenchmarkServer::new(client.clone())),
        LocalSessionManager::default().into(),
        Default::default(),
    );

    let app = Router::new()
        .route("/health", get(health))
        .nest_service("/mcp", service);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:8084")
        .await
        .expect("Failed to bind to port 8084");

    tracing::info!("Rust MCP server listening on port 8084");
    axum::serve(listener, app).await.expect("Server failed");
}

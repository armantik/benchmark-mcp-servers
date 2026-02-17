# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-language MCP (Model Context Protocol) server performance benchmark. Five server implementations (Java, Go, Python, Node.js, Rust) expose identical tools over Streamable HTTP transport, load-tested with k6 to compare latency, throughput, and resource usage.

## Commands

### Build & Run All Servers
```bash
docker compose build
docker compose up -d          # starts all 5 servers + mock-api
docker compose ps             # verify health
docker compose down           # teardown
```

### Functional Tests (requires servers running)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-test.txt
python3 test_mcp_servers.py
```

### Run Full Benchmark Suite
```bash
cd benchmark
./run_benchmark.sh    # requires: docker, k6, python3
```

### Run k6 Against a Single Server
```bash
k6 run -e SERVER_URL=http://localhost:8080/mcp -e SERVER_NAME=java benchmark/benchmark.js
```

### Analyze Results
```bash
python3 analyze_results.py                          # cross-round comparison table
python3 benchmark/consolidate.py benchmark/results/<timestamp_dir>  # generate summary.json
```

### Collect Docker Stats (background during benchmark)
```bash
python3 benchmark/collect_stats.py <container_name> <output.json> [poll_interval_s]
```

## Architecture

### Server Implementations (all expose `/mcp` endpoint via MCP Streamable HTTP)

| Server | Port | Stack | Entry Point |
|--------|------|-------|-------------|
| Java | 8080 | Spring Boot 4 + Spring AI 2.0 (WebMVC) | `java-server/` (Gradle, Java 21) |
| Go | 8081 | Official MCP Go SDK v1.2.0 | `go-server/main.go` |
| Python | 8082 | FastMCP + FastAPI (stateless HTTP) | `python-server/main.py` |
| Node.js | 8083 | Official MCP SDK v1.26.0 (Express) | `nodejs-server/index.js` |
| Rust | 8084 | Official rmcp SDK v0.15.0 (Axum) | `rust-server/src/main.rs` |

All servers are Docker-containerized with identical resource constraints (1 CPU, 1GB RAM). A MockServer container on port 1080 provides the mock API for `fetch_external_data` tests.

### Tool Contract

Every server implements these 4 tools with identical input/output schemas:
- **`calculate_fibonacci(n)`** — recursive CPU-bound computation, returns `{input, result, server_type}`
- **`fetch_external_data(endpoint)`** — HTTP GET to external URL, returns `{url, status_code, response_time_ms, server_type}`
- **`process_json_data(data)`** — uppercases all string values in nested JSON, returns `{original_keys, transformed_data, server_type}`
- **`simulate_database_query(query, delay_ms)`** — async sleep simulation, returns `{query, delay_ms, timestamp, server_type}`

All tool responses are wrapped in MCP's `content[0].text` as JSON strings.

### MCP Protocol Flow (Streamable HTTP)

Each benchmark iteration executes a full MCP session: `POST initialize` → `POST notifications/initialized` → `POST tools/call` → `DELETE` (session cleanup). The `Mcp-Session-Id` header is carried through all requests after initialization. Responses may be plain JSON or SSE (`text/event-stream`); both parsers handle either format.

### Benchmark Pipeline

`run_benchmark.sh` orchestrates: stop all → start one server → health check → warmup (10 requests) → start `collect_stats.py` in background → run k6 → stop stats → repeat for next server → `consolidate.py` produces `summary.json` with rankings.

Results are stored in `benchmark/results/<YYYYMMDD_HHMMSS>/<server>/` with `k6.json` (latency/throughput metrics) and `stats.json` (CPU/memory from Docker API).

### Health Check Endpoints

- Java: `/actuator/health` (Spring Boot Actuator)
- Go, Node.js, Python, Rust: `/health`

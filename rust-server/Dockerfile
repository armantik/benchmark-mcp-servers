FROM rust:1.88-slim AS builder

WORKDIR /app

# Cache dependencies: copy manifests first, build with dummy main
COPY Cargo.toml ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release 2>/dev/null || true
RUN rm -rf src

# Copy real source and build
COPY src ./src
RUN touch src/main.rs && cargo build --release

# Runtime image (glibc — faster allocator + SIMD string ops vs musl)
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /root/

COPY --from=builder /app/target/release/mcp-rust-server .

EXPOSE 8084

CMD ["./mcp-rust-server"]

FROM rust:1.88-alpine AS builder

RUN apk add --no-cache musl-dev

WORKDIR /app

# Cache dependencies: copy manifests first, build with dummy main
COPY Cargo.toml ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release 2>/dev/null || true
RUN rm -rf src

# Copy real source and build
COPY src ./src
RUN touch src/main.rs && cargo build --release

# Runtime image
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

COPY --from=builder /app/target/release/mcp-rust-server .

EXPOSE 8084

CMD ["./mcp-rust-server"]

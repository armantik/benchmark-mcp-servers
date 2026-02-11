from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager
import httpx
import time
import json
from typing import Any, Dict

# Inicialização do FastMCP com stateless HTTP
mcp = FastMCP("BenchmarkPythonServer", stateless_http=True)

# Tool 1: calculate_fibonacci
@mcp.tool()
def calculate_fibonacci(n: int) -> dict:
    """Calcula o N-ésimo número de Fibonacci de forma recursiva.
    
    Args:
        n: Número inteiro entre 0 e 40
    
    Returns:
        Objeto JSON com input, result e server_type
    """
    def fib(x: int) -> int:
        if x <= 1:
            return x
        return fib(x - 1) + fib(x - 2)
    
    if n < 0 or n > 40:
        raise ValueError("n deve estar entre 0 e 40")
    
    result = fib(n)
    return {
        "input": n,
        "result": result,
        "server_type": "python"
    }

# Tool 2: fetch_external_data
@mcp.tool()
async def fetch_external_data(endpoint: str) -> dict:
    """Faz uma requisição HTTP GET para uma API externa.
    
    Args:
        endpoint: URL completa do endpoint
    
    Returns:
        Objeto JSON com url, status_code, response_time_ms e server_type
    """
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(endpoint)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                "url": endpoint,
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "server_type": "python"
            }
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return {
                "url": endpoint,
                "status_code": 0,
                "response_time_ms": response_time_ms,
                "error": str(e),
                "server_type": "python"
            }

# Tool 3: process_json_data
@mcp.tool()
def process_json_data(data: Dict[str, Any]) -> dict:
    """Recebe um JSON, valida e transforma (uppercase em campos string).
    
    Args:
        data: Objeto JSON para processar
    
    Returns:
        Objeto JSON transformado com metadados
    """
    def transform_strings(obj):
        if isinstance(obj, dict):
            return {k: transform_strings(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [transform_strings(item) for item in obj]
        elif isinstance(obj, str):
            return obj.upper()
        else:
            return obj
    
    transformed = transform_strings(data)
    
    return {
        "original_keys": list(data.keys()) if isinstance(data, dict) else None,
        "transformed_data": transformed,
        "server_type": "python"
    }

# Tool 4: simulate_database_query
@mcp.tool()
async def simulate_database_query(query: str, delay_ms: int = 0) -> dict:
    """Simula uma query de banco de dados com delay configurável.
    
    Args:
        query: String da query SQL
        delay_ms: Delay em milissegundos (0-5000)
    
    Returns:
        Objeto JSON com query, delay_ms, timestamp e server_type
    """
    import asyncio
    from datetime import datetime
    
    if delay_ms < 0 or delay_ms > 5000:
        raise ValueError("delay_ms deve estar entre 0 e 5000")
    
    # Simula o delay
    await asyncio.sleep(delay_ms / 1000.0)
    
    return {
        "query": query,
        "delay_ms": delay_ms,
        "timestamp": datetime.utcnow().isoformat(),
        "server_type": "python"
    }

# Gerenciador de ciclo de vida (Lifespan)
@asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield

# Criar aplicação FastAPI
app = FastAPI(lifespan=lifespan)

# Montar o endpoint MCP
# FastMCP cria rota interna em /mcp, então montamos na raiz
app.mount("/", mcp.streamable_http_app())

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok", "server_type": "python"}

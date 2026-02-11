import express from 'express';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { z } from 'zod';

const app = express();
app.use(express.json());

// Função para criar uma instância do servidor MCP
function createMcpServer() {
    const server = new McpServer({
        name: 'BenchmarkNodejsServer',
        version: '1.0.0',
    });

    // Tool 1: calculate_fibonacci
    server.tool(
        'calculate_fibonacci',
        'Calcula o N-ésimo número de Fibonacci de forma recursiva',
        { n: z.number().describe('Número inteiro entre 0 e 40') },
        async ({ n }) => {
            if (n < 0 || n > 40) {
                throw new Error('n deve estar entre 0 e 40');
            }

            let a = 0, b = 1;
            for (let i = 0; i < n; i++) {
                [a, b] = [b, a + b];
            }

            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        input: n,
                        result: a,
                        server_type: 'nodejs',
                    }),
                }],
            };
        }
    );

    // Tool 2: fetch_external_data
    server.tool(
        'fetch_external_data',
        'Faz uma requisição HTTP GET para uma API externa',
        { endpoint: z.string().describe('URL completa do endpoint') },
        async ({ endpoint }) => {
            const startTime = Date.now();
            try {
                const response = await fetch(endpoint);
                const responseTimeMs = Date.now() - startTime;
                return {
                    content: [{
                        type: 'text',
                        text: JSON.stringify({
                            url: endpoint,
                            status_code: response.status,
                            response_time_ms: responseTimeMs,
                            server_type: 'nodejs',
                        }),
                    }],
                };
            } catch (error) {
                const responseTimeMs = Date.now() - startTime;
                return {
                    content: [{
                        type: 'text',
                        text: JSON.stringify({
                            url: endpoint,
                            status_code: 0,
                            response_time_ms: responseTimeMs,
                            error: error.message,
                            server_type: 'nodejs',
                        }),
                    }],
                };
            }
        }
    );

    // Tool 3: process_json_data
    server.tool(
        'process_json_data',
        'Recebe um JSON, valida e transforma (uppercase em campos string)',
        { data: z.object({}).passthrough().describe('Objeto JSON para processar') },
        async ({ data }) => {
            function transformStrings(obj) {
                if (typeof obj === 'object' && obj !== null) {
                    if (Array.isArray(obj)) {
                        return obj.map(transformStrings);
                    }
                    const result = {};
                    for (const [key, value] of Object.entries(obj)) {
                        result[key] = transformStrings(value);
                    }
                    return result;
                }
                if (typeof obj === 'string') return obj.toUpperCase();
                return obj;
            }

            const transformed = transformStrings(data);
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        original_keys: typeof data === 'object' && data !== null ? Object.keys(data) : null,
                        transformed_data: transformed,
                        server_type: 'nodejs',
                    }),
                }],
            };
        }
    );

    // Tool 4: simulate_database_query
    server.tool(
        'simulate_database_query',
        'Simula uma query de banco de dados com delay configurável',
        {
            query: z.string().describe('String da query SQL'),
            delay_ms: z.number().default(0).describe('Delay em milissegundos (0-5000)'),
        },
        async ({ query, delay_ms = 0 }) => {
            if (delay_ms < 0 || delay_ms > 5000) {
                throw new Error('delay_ms deve estar entre 0 e 5000');
            }

            await new Promise((resolve) => setTimeout(resolve, delay_ms));

            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        query,
                        delay_ms,
                        timestamp: new Date().toISOString(),
                        server_type: 'nodejs',
                    }),
                }],
            };
        }
    );

    return server;
}

// Endpoint MCP — PER-REQUEST instantiation (CVE-2026-25536 mitigation)
app.post('/mcp', async (req, res) => {
    const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined,
    });
    const server = createMcpServer();

    try {
        await server.connect(transport);
        await transport.handleRequest(req, res, req.body);
        res.on('close', async () => {
            await transport.close();
            await server.close();
        });
    } catch (error) {
        console.error('Error handling MCP request:', error);
        if (!res.headersSent) {
            res.status(500).json({ error: error.message });
        }
    }
});

app.get('/mcp', (req, res) => res.status(405).end());
app.delete('/mcp', (req, res) => res.status(405).end());

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'ok', server_type: 'nodejs' });
});

const PORT = 8083;
app.listen(PORT, () => {
    console.log(`Node.js MCP server listening on port ${PORT}`);
    console.log(`MCP endpoint: http://localhost:${PORT}/mcp`);
});

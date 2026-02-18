package com.benchmark.mcp;

import org.springaicommunity.mcp.annotation.McpTool;
import org.springaicommunity.mcp.annotation.McpToolParam;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

@Service
public class McpToolsService {

    private final RestTemplate restTemplate;

    public McpToolsService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    // Tool 1: calculate_fibonacci
    @McpTool(name = "calculate_fibonacci", description = "Calcula o N-ésimo número de Fibonacci de forma recursiva")
    public Map<String, Object> calculateFibonacci(
            @McpToolParam(description = "Número inteiro entre 0 e 40") int n) {

        if (n < 0 || n > 40) {
            throw new IllegalArgumentException("n deve estar entre 0 e 40");
        }

        int result = fibonacci(n);

        Map<String, Object> response = new HashMap<>();
        response.put("input", n);
        response.put("result", result);
        response.put("server_type", "java");
        return response;
    }

    private int fibonacci(int n) {
        if (n <= 1)
            return n;
        return fibonacci(n - 1) + fibonacci(n - 2);
    }

    // Tool 2: fetch_external_data
    @McpTool(name = "fetch_external_data", description = "Faz uma requisição HTTP GET para uma API externa")
    public Map<String, Object> fetchExternalData(
            @McpToolParam(description = "URL completa do endpoint") String endpoint) {

        long startTime = System.currentTimeMillis();
        Map<String, Object> response = new HashMap<>();

        try {
            var httpResponse = restTemplate.getForEntity(endpoint, String.class);
            long responseTimeMs = System.currentTimeMillis() - startTime;

            response.put("url", endpoint);
            response.put("status_code", httpResponse.getStatusCode().value());
            response.put("response_time_ms", responseTimeMs);
            response.put("server_type", "java");
        } catch (RestClientException e) {
            long responseTimeMs = System.currentTimeMillis() - startTime;
            response.put("url", endpoint);
            response.put("status_code", 0);
            response.put("response_time_ms", responseTimeMs);
            response.put("error", e.getMessage());
            response.put("server_type", "java");
        }

        return response;
    }

    // Tool 3: process_json_data
    @McpTool(name = "process_json_data", description = "Recebe um JSON, valida e transforma (uppercase em campos string)")
    public Map<String, Object> processJsonData(
            @McpToolParam(description = "Objeto JSON para processar") Map<String, Object> data) {

        Map<String, Object> transformed = transformStrings(data);

        Map<String, Object> response = new HashMap<>();
        response.put("original_keys", data.keySet());
        response.put("transformed_data", transformed);
        response.put("server_type", "java");
        return response;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> transformStrings(Map<String, Object> obj) {
        Map<String, Object> result = new HashMap<>();
        for (Map.Entry<String, Object> entry : obj.entrySet()) {
            Object value = entry.getValue();
            if (value instanceof String) {
                result.put(entry.getKey(), ((String) value).toUpperCase());
            } else if (value instanceof Map) {
                result.put(entry.getKey(), transformStrings((Map<String, Object>) value));
            } else {
                result.put(entry.getKey(), value);
            }
        }
        return result;
    }

    // Tool 4: simulate_database_query
    @McpTool(name = "simulate_database_query", description = "Simula uma query de banco de dados com delay configurável")
    public Map<String, Object> simulateDatabaseQuery(
            @McpToolParam(description = "String da query SQL") String query,
            @McpToolParam(description = "Delay em milissegundos (0-5000)") int delay_ms) {

        if (delay_ms < 0 || delay_ms > 5000) {
            throw new IllegalArgumentException("delay_ms deve estar entre 0 e 5000");
        }

        try {
            Thread.sleep(delay_ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        Map<String, Object> response = new HashMap<>();
        response.put("query", query);
        response.put("delay_ms", delay_ms);
        response.put("timestamp", Instant.now().toString());
        response.put("server_type", "java");
        return response;
    }
}

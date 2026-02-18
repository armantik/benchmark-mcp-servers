package main

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Input structures
type FibonacciArgs struct {
	N int `json:"n"`
}

type FetchDataArgs struct {
	Endpoint string `json:"endpoint"`
}

type ProcessDataArgs struct {
	Data map[string]interface{} `json:"data"`
}

type DatabaseQueryArgs struct {
	Query   string `json:"query"`
	DelayMs int    `json:"delay_ms,omitempty"`
}

// Output structures
type FibonacciOutput struct {
	Input      int    `json:"input"`
	Result     int    `json:"result"`
	ServerType string `json:"server_type"`
}

type FetchDataOutput struct {
	URL            string `json:"url"`
	StatusCode     int    `json:"status_code"`
	ResponseTimeMs int64  `json:"response_time_ms"`
	Error          string `json:"error,omitempty"`
	ServerType     string `json:"server_type"`
}

type ProcessDataOutput struct {
	OriginalKeys    []string               `json:"original_keys"`
	TransformedData map[string]interface{} `json:"transformed_data"`
	ServerType      string                 `json:"server_type"`
}

type DatabaseOutput struct {
	Query      string `json:"query"`
	DelayMs    int    `json:"delay_ms"`
	Timestamp  string `json:"timestamp"`
	ServerType string `json:"server_type"`
}

// HTTP client with timeout for external requests
var httpClient = &http.Client{Timeout: 10 * time.Second}

// Tool handlers
func handleFibonacci(ctx context.Context, req *mcp.CallToolRequest, args FibonacciArgs) (*mcp.CallToolResult, FibonacciOutput, error) {
	if args.N < 0 || args.N > 40 {
		return nil, FibonacciOutput{}, fmt.Errorf("n deve estar entre 0 e 40")
	}

	var fib func(int) int
	fib = func(x int) int {
		if x <= 1 {
			return x
		}
		return fib(x-1) + fib(x-2)
	}

	return nil, FibonacciOutput{
		Input:      args.N,
		Result:     fib(args.N),
		ServerType: "go",
	}, nil
}

func handleFetchData(ctx context.Context, req *mcp.CallToolRequest, args FetchDataArgs) (*mcp.CallToolResult, FetchDataOutput, error) {
	startTime := time.Now()

	resp, err := httpClient.Get(args.Endpoint)
	responseTimeMs := time.Since(startTime).Milliseconds()

	if err != nil {
		return nil, FetchDataOutput{
			URL:            args.Endpoint,
			StatusCode:     0,
			ResponseTimeMs: responseTimeMs,
			Error:          err.Error(),
			ServerType:     "go",
		}, nil
	}
	defer resp.Body.Close()

	return nil, FetchDataOutput{
		URL:            args.Endpoint,
		StatusCode:     resp.StatusCode,
		ResponseTimeMs: responseTimeMs,
		ServerType:     "go",
	}, nil
}

func handleProcessData(ctx context.Context, req *mcp.CallToolRequest, args ProcessDataArgs) (*mcp.CallToolResult, ProcessDataOutput, error) {
	var transformStrings func(interface{}) interface{}
	transformStrings = func(obj interface{}) interface{} {
		switch v := obj.(type) {
		case map[string]interface{}:
			result := make(map[string]interface{})
			for key, val := range v {
				result[key] = transformStrings(val)
			}
			return result
		case []interface{}:
			result := make([]interface{}, len(v))
			for i, val := range v {
				result[i] = transformStrings(val)
			}
			return result
		case string:
			return strings.ToUpper(v)
		default:
			return v
		}
	}

	transformed := transformStrings(args.Data).(map[string]interface{})
	originalKeys := make([]string, 0, len(args.Data))
	for k := range args.Data {
		originalKeys = append(originalKeys, k)
	}

	return nil, ProcessDataOutput{
		OriginalKeys:    originalKeys,
		TransformedData: transformed,
		ServerType:      "go",
	}, nil
}

func handleDatabaseQuery(ctx context.Context, req *mcp.CallToolRequest, args DatabaseQueryArgs) (*mcp.CallToolResult, DatabaseOutput, error) {
	if args.DelayMs < 0 || args.DelayMs > 5000 {
		return nil, DatabaseOutput{}, fmt.Errorf("delay_ms deve estar entre 0 e 5000")
	}

	time.Sleep(time.Duration(args.DelayMs) * time.Millisecond)

	return nil, DatabaseOutput{
		Query:      args.Query,
		DelayMs:    args.DelayMs,
		Timestamp:  time.Now().UTC().Format(time.RFC3339),
		ServerType: "go",
	}, nil
}

func main() {
	// Create server
	server := mcp.NewServer(&mcp.Implementation{
		Name:    "BenchmarkGoServer",
		Version: "1.0.0",
	}, nil)

	// Register tools
	mcp.AddTool(server, &mcp.Tool{
		Name:        "calculate_fibonacci",
		Description: "Calcula o N-ésimo número de Fibonacci de forma recursiva",
	}, handleFibonacci)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "fetch_external_data",
		Description: "Faz uma requisição HTTP GET para uma API externa",
	}, handleFetchData)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "process_json_data",
		Description: "Recebe um JSON, valida e transforma (uppercase em campos string)",
	}, handleProcessData)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "simulate_database_query",
		Description: "Simula uma query de banco de dados com delay configurável",
	}, handleDatabaseQuery)

	// Health check endpoint (before HTTP handler)
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"ok","server_type":"go"}`))
	})

	// Setup HTTP transport
	httpHandler := mcp.NewStreamableHTTPHandler(func(r *http.Request) *mcp.Server {
		return server
	}, nil)

	http.Handle("/mcp", httpHandler)

	fmt.Println("Go MCP server listening on port 8081")
	fmt.Println("MCP endpoint: http://localhost:8081/mcp")
	if err := http.ListenAndServe(":8081", nil); err != nil {
		panic(err)
	}
}


import json
import os
import sys

files = [
    'benchmark/results/20260210_182244/summary.json',
    'benchmark/results/20260210_212323/summary.json',
    'benchmark/results/20260210_214524/summary.json'
]

print(f"{'Server':<10} | {'Metric':<12} | {'Round 1':<10} | {'Round 2':<10} | {'Round 3':<10} | {'Var %':<6}")
print('-' * 80)

metrics = [
    ('RPS', ['http', 'rps']),
    ('Lat Avg', ['http', 'latency', 'avg']),
    ('Mem MB', ['resources', 'memory_mb', 'avg'])
]

# Order matters: python, go, nodejs, java based on typical file structure
servers = ['python', 'go', 'nodejs', 'java']

data = []
for f in files:
    try:
        with open(f) as fp:
            content = json.load(fp)
            if 'servers' in content:
                data.append(content['servers'])
            elif 'results' in content:
                data.append(content['results'])
            else:
                # If flat structure (might differ in older runs?)
                data.append(content)
    except Exception as e:
        print(f"Error reading {f}: {e}")
        sys.exit(1)

# Debug: check keys
for i, d in enumerate(data):
    missing = [s for s in servers if s not in d]
    if missing:
        print(f"Warning: File {i} missing keys: {missing}. Available: {list(d.keys())}")

for s in servers:
    for m_name, m_path in metrics:
        vals = []
        skip_metric = False
        for i in range(3):
            if s not in data[i]:
                vals.append(0.0)
                continue
                
            val = data[i][s]
            try:
                for key in m_path:
                    val = val[key]
                vals.append(val)
            except KeyError:
                vals.append(0.0)
        
        avg = sum(vals) / 3
        if avg == 0:
            var_pct = 0.0
        else:
            max_diff = max(abs(v - avg) for v in vals)
            var_pct = (max_diff / avg) * 100
        
        print(f"{s:<10} | {m_name:<12} | {vals[0]:<10.1f} | {vals[1]:<10.1f} | {vals[2]:<10.1f} | {var_pct:<6.1f}%")
    print('-' * 80)

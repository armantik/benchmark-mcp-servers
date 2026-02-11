
import json
import os
import sys

# Rounds to analyze
rounds = [
    'benchmark/results/20260210_182244',
    'benchmark/results/20260210_212323',
    'benchmark/results/20260210_214524'
]

servers = ['python', 'go', 'nodejs', 'java']

print(f"{'Server':<10} | {'Init (ms)':<10} | {'Net (MB/s)':<10} | {'Max Lat':<10} | {'Comp (ms)':<10} | {'I/O (ms)':<10}")
print('-' * 80)

def get_network_usage(stats_file):
    try:
        with open(stats_file) as f:
            data = json.load(f)
            samples = data['samples']
            if not samples: return 0.0
            
            # Helper to handle counter resets if any (restart), but assumption is single run
            start_rx = samples[0]['net_rx_bytes']
            end_rx = samples[-1]['net_rx_bytes']
            start_tx = samples[0]['net_tx_bytes']
            end_tx = samples[-1]['net_tx_bytes']
            
            total_bytes = (end_rx - start_rx) + (end_tx - start_tx)
            duration = samples[-1]['elapsed_s'] if 'elapsed_s' in samples[-1] else 300 # Approx
            if duration == 0: duration = 1 
            
            return (total_bytes / 1024 / 1024) / duration
    except:
        return 0.0

aggregated = {s: {'init': [], 'net': [], 'max_lat': [], 'comp': [], 'io': []} for s in servers}

for r in rounds:
    for s in servers:
        k6_path = os.path.join(r, s, 'k6.json')
        stats_path = os.path.join(r, s, 'stats.json')
        
        # 1. K6 Metrics
        try:
            with open(k6_path) as f:
                k6 = json.load(f)
                
                # Init Time
                init_ms = k6['tools']['_initialize']['avg']
                
                # Max Latency
                max_lat_ms = k6['http']['latency']['max']
                
                # Compute vs I/O
                # Compute: fibonacci + json_process
                t = k6['tools']
                comp_avg = (t['calculate_fibonacci']['avg'] + t['process_json_data']['avg']) / 2
                
                # I/O: fetch + db
                io_avg = (t['fetch_external_data']['avg'] + t['simulate_database_query']['avg']) / 2
                
                aggregated[s]['init'].append(init_ms)
                aggregated[s]['max_lat'].append(max_lat_ms)
                aggregated[s]['comp'].append(comp_avg)
                aggregated[s]['io'].append(io_avg)
                
        except Exception as e:
            # print(f"Error k6 {s}: {e}")
            pass

        # 2. Network Metrics
        net_mbs = get_network_usage(stats_path)
        aggregated[s]['net'].append(net_mbs)

# Print Averages
for s in servers:
    d = aggregated[s]
    avg_init = sum(d['init'])/3 if d['init'] else 0
    avg_net = sum(d['net'])/3 if d['net'] else 0
    avg_max = sum(d['max_lat'])/3 if d['max_lat'] else 0
    avg_comp = sum(d['comp'])/3 if d['comp'] else 0
    avg_io = sum(d['io'])/3 if d['io'] else 0
    
    print(f"{s:<10} | {avg_init:<10.2f} | {avg_net:<10.2f} | {avg_max:<10.0f} | {avg_comp:<10.2f} | {avg_io:<10.2f}")

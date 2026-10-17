import csv

def generate_markdown_tables():
    with open('results/summary_csv/postgres_matrix_results.csv', 'r', encoding='utf-8') as f:
        pg_rows = list(csv.DictReader(f))
    with open('results/summary_csv/rocksdb_matrix_results.csv', 'r', encoding='utf-8') as f:
        rdb_rows = list(csv.DictReader(f))

    print('### POSTGRES TABLE')
    print('| Workload | Variant | Threads | Throughput (ops/s) | Read Ops | Write Ops | p50 (ms) | p95 (ms) | p99 (ms) | p99.9 (ms) | Max (ms) | Variance (ms²) |')
    print('| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |')
    for r in pg_rows:
        print(f"| {r['workload']} | {r['variant']} | {r['threads']} | {float(r['total_throughput_ops']):,.1f} | {int(r['read_ops']):,} | {int(r['write_ops']):,} | {float(r['p50_ms']):.3f} | {float(r['p95_ms']):.3f} | {float(r['p99_ms']):.3f} | {float(r['p999_ms']):.3f} | {float(r['max_ms']):.2f} | {float(r['variance_ms2']):.3f} |")

    print('\n### ROCKSDB TABLE')
    print('| Workload | Variant | Threads | Throughput (ops/s) | Read Ops | Write Ops | p50 (ms) | p95 (ms) | p99 (ms) | p99.9 (ms) | Max (ms) | Variance (ms²) |')
    print('| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |')
    for r in rdb_rows:
        print(f"| {r['workload']} | {r['variant']} | {r['threads']} | {float(r['total_throughput_ops']):,.1f} | {int(r['read_ops']):,} | {int(r['write_ops']):,} | {float(r['p50_ms']):.3f} | {float(r['p95_ms']):.3f} | {float(r['p99_ms']):.3f} | {float(r['p999_ms']):.3f} | {float(r['max_ms']):.2f} | {float(r['variance_ms2']):.3f} |")

if __name__ == '__main__':
    generate_markdown_tables()

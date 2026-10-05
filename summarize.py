import json, glob, statistics as st, re, collections
rows = collections.defaultdict(list)
for f in sorted(glob.glob('results/*_r*.json')):
    m = re.match(r'results/([a-z_]+)_n(\d+)_c(\d+)_r(\d+)\.json', f)
    name, n, c, r = m.groups()
    d = json.load(open(f))
    ok = d['statusCodeDistribution'].get('200', 0); tot = sum(d['statusCodeDistribution'].values())
    rows[(int(n), name)].append((d['summary']['requestsPerSec'], d['latencyPercentiles']['p50']*1e3,
        d['latencyPercentiles']['p99']*1e3, d['latencyPercentiles']['p99.9']*1e3, d['summary']['successRate'], len(d['errorDistribution'])))
print(f"{'cores':>5} {'server':<5} {'rps (median)':>13} {'rps runs':>30} {'p50 ms':>7} {'p99 ms':>7} {'p99.9 ms':>8} {'RSS MB':>7} {'err':>4}")
for (n, name), v in sorted(rows.items()):
    rps = [x[0] for x in v]
    rss = int(open(f'results/{name}_n{n}_c200_rss_kb').read())/1024
    print(f"{n:>5} {name:<5} {st.median(rps):>13,.0f} {' / '.join(f'{x/1e3:.0f}k' for x in rps):>30} {st.median(x[1] for x in v):>7.3f} {st.median(x[2] for x in v):>7.3f} {st.median(x[3] for x in v):>8.3f} {rss:>7.1f} {sum(x[5] for x in v):>4}")

"""Render results/*.json into results/benchmark.png (throughput, p99 latency, full table)."""
import glob, json, re, statistics as st, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

# ---- palette (dataviz reference palette, light mode; slots 1-5 in fixed order) ----
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASE = "#e1e0d9", "#c3c2b7"
SERIES = [  # key, label, color  (color follows the entity)
    ("tina_rp", "Tina - Reuse_Port", "#2a78d6"),
    ("tina",    "Tina - Coordinator (upstream bench cfg)", "#eb6834"),
    ("axum",    "Rust Axum", "#1baf7a"),
    ("gofast",  "Go fasthttp", "#eda100"),
    ("go",      "Go net/http", "#e87ba4"),
]
CORES = [1, 4, 8]
DPI = 160
PX = DPI / 96  # one CSS px in device px

# ---- load data ----
runs = collections.defaultdict(list)
for f in glob.glob("results/*_r*.json"):
    name, n, r = re.match(r"results/([a-z_]+)_n(\d+)_c200_r(\d+)\.json", f).groups()
    d = json.load(open(f))
    runs[(name, int(n))].append((d["summary"]["requestsPerSec"], d["latencyPercentiles"]["p50"] * 1e3,
                                 d["latencyPercentiles"]["p99"] * 1e3, d["latencyPercentiles"]["p99.9"] * 1e3))
data = {}
for (name, n), v in runs.items():
    rss = int(open(f"results/{name}_n{n}_c200_rss_kb").read()) / 1024
    data[(name, n)] = dict(rps=st.median(x[0] for x in v), p50=st.median(x[1] for x in v),
                           p99=st.median(x[2] for x in v), p999=st.median(x[3] for x in v), rss=rss)

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.edgecolor": BASE})
fig = plt.figure(figsize=(10, 15.2), dpi=DPI, facecolor=SURFACE)


def rounded_bar(ax, x0, w, h, color, ymax, axes_h_px, r_css=4):
    """Bar from baseline with a 4px rounded top; bottom is square (rounded part is clipped below y=0)."""
    r = r_css * PX
    ext = 3 * r  # extend below the baseline so only the top corners show rounding
    p = FancyBboxPatch((x0, -ext), w, h + ext, boxstyle=f"round,pad=0,rounding_size={r}",
                       mutation_aspect=ymax / axes_h_px, fc=color, ec="none", lw=0)
    ax.add_patch(p)


def grouped(ax, key, ymax, ticks, fmt, title, subtitle, label_best):
    fig.canvas.draw()
    bb = ax.get_window_extent()
    W, H = bb.width, bb.height
    ax.set_xlim(0, W); ax.set_ylim(0, ymax)
    bar_w, gap = 24 * PX, 2 * PX
    cluster = len(SERIES) * bar_w + (len(SERIES) - 1) * gap
    for gi, n in enumerate(CORES):
        gx = W * (gi + 0.5) / len(CORES)
        vals = {k: data[(k, n)][key] for k, _, _ in SERIES if (k, n) in data}
        best = (max if label_best == "max" else min)(vals.values())
        for si, (k, lab, col) in enumerate(SERIES):
            if (k, n) not in data:
                continue
            x0 = gx - cluster / 2 + si * (bar_w + gap)
            v = data[(k, n)][key]
            rounded_bar(ax, x0, bar_w, v, col, ymax, H)
            if v == best:
                ax.text(x0 + bar_w / 2, v + ymax * 0.012, fmt(v), ha="center", va="bottom",
                        fontsize=8, color=INK, fontweight="bold")
    ax.set_xticks([W * (i + 0.5) / len(CORES) for i in range(len(CORES))])
    ax.set_xticklabels([f"{n} core{'s' if n > 1 else ''}" for n in CORES], fontsize=10, color=INK2)
    ax.set_yticks(ticks); ax.set_yticklabels([f"{t:,.0f}" if t >= 10 else f"{t:g}" for t in ticks], fontsize=9, color=MUTED)
    ax.yaxis.grid(True, color=GRID, lw=1, zorder=0); ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    ax.set_facecolor(SURFACE)
    ax.text(-0.0465, 1.12, title, transform=ax.transAxes, fontsize=12.5, fontweight="bold", color=INK, va="bottom")
    ax.text(-0.0465, 1.05, subtitle, transform=ax.transAxes, fontsize=9, color=INK2, va="bottom")


# ---- header ----
fig.text(0.06, 0.972, "GET / benchmark: Tina (Odin) vs Go vs Rust", fontsize=18, fontweight="bold", color=INK, va="top")
fig.text(0.06, 0.953, "Empty-body 200 over loopback, 200 keep-alive connections, oha 3 x 10 s (median), server pinned to N physical cores.\n"
         "AMD Ryzen AI MAX+ 395, Odin dev-2026-09, Go 1.26.8, Rust 1.98.1 (Axum 0.8), fasthttp 1.75.",
         fontsize=9, color=INK2, va="top", linespacing=1.5)

# ---- legend (always present for >=2 series) ----
lx, ly = 0.06, 0.905
for i, (k, lab, col) in enumerate(SERIES):
    col_i, row_i = i % 3, i // 3
    xx = lx + [0, 0.30, 0.60][col_i] if row_i == 0 else lx + [0, 0.30, 0.60][col_i]
    yy = ly - row_i * 0.014
    fig.patches.append(Rectangle((xx, yy - 0.0035), 0.011, 0.0072, transform=fig.transFigure, fc=col, ec="none"))
    fig.text(xx + 0.017, yy, lab, fontsize=9, color=INK2, va="center")

# ---- chart 1: throughput ----
ax1 = fig.add_axes([0.10, 0.585, 0.86, 0.245])
grouped(ax1, "rps", 1.4e6, [0, 250e3, 500e3, 750e3, 1000e3, 1250e3],
        lambda v: f"{v/1e3:,.0f}k", "Throughput (requests / second)", "Higher is better. Best bar in each group labelled.", "max")
ax1.set_yticklabels(["0", "250k", "500k", "750k", "1,000k", "1,250k"], fontsize=9, color=MUTED)

# ---- chart 2: p99 latency ----
ax2 = fig.add_axes([0.10, 0.335, 0.86, 0.19])
grouped(ax2, "p99", 3.6, [0, 1, 2, 3], lambda v: f"{v:.2f}", "p99 latency (ms)",
        "Lower is better. Best bar in each group labelled.", "min")
ax2.set_yticklabels(["0", "1 ms", "2 ms", "3 ms"], fontsize=9, color=MUTED)

# ---- table view ----
axt = fig.add_axes([0.06, 0.03, 0.90, 0.265], facecolor=SURFACE)
axt.set_xlim(0, 1); axt.set_ylim(0, 1); axt.axis("off")
axt.text(0, 1.0, "All results", fontsize=12.5, fontweight="bold", color=INK, va="top")
cols = [("Cores", 0.00, "left"), ("Server", 0.09, "left"), ("Req/s", 0.60, "right"), ("p50 ms", 0.70, "right"),
        ("p99 ms", 0.79, "right"), ("p99.9 ms", 0.89, "right"), ("RSS MB", 1.0, "right")]
top = 0.92
rh = 0.0555
for t, x, ha in cols:
    axt.text(x, top, t, fontsize=8.5, color=MUTED, ha=ha, va="center", fontweight="bold")
axt.plot([0, 1], [top - rh / 2, top - rh / 2], color=BASE, lw=1)
row = 0
for n in CORES:
    best_rps = max(data[(k, n)]["rps"] for k, _, _ in SERIES if (k, n) in data)
    group = sorted([(k, lab, col) for k, lab, col in SERIES if (k, n) in data], key=lambda s: -data[(s[0], n)]["rps"])
    for k, lab, col in group:
        d = data[(k, n)]
        y = top - rh * (row + 1)
        bold = "bold" if d["rps"] == best_rps else "normal"
        if row and group[0][0] == k:
            axt.plot([0, 1], [y + rh / 2, y + rh / 2], color=GRID, lw=1)
        if group[0][0] == k:
            axt.text(0.0, y, str(n), fontsize=9, ha="left", va="center", color=INK, fontweight="bold")
        axt.add_patch(Rectangle((0.09, y - 0.012), 0.012, 0.024, fc=col, ec="none"))
        axt.text(0.11, y, lab, fontsize=8.8, ha="left", va="center", color=INK2, fontweight=bold)
        for (t, x, ha), v in zip(cols[2:], [f"{d['rps']:,.0f}", f"{d['p50']:.3f}", f"{d['p99']:.3f}", f"{d['p999']:.3f}", f"{d['rss']:.0f}"]):
            axt.text(x, y, v, fontsize=8.8, ha=ha, va="center", color=INK2 if bold == "normal" else INK, fontweight=bold)
        row += 1
axt.text(0, 0.0, "Tina - Reuse_Port needs >1 shard (single shard always binds exclusively), so it has no 1-core row. "
         "Tina RSS is preallocated (~48 MB per shard).", fontsize=7.5, color=MUTED, va="bottom")

fig.savefig("results/benchmark.png", dpi=DPI, facecolor=SURFACE)
print("wrote results/benchmark.png")

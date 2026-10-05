#!/usr/bin/env bash
# Benchmarks GET / on Tina (Odin), Go net/http, Rust Axum.
# Server pinned to physical cores 0..N-1; oha pinned to cores 8-15 + SMT siblings 24-31.
set -u
cd "$(dirname "$0")"
OUT=results; mkdir -p $OUT
CONNS=${CONNS:-200}; DUR=${DUR:-10s}; RUNS=${RUNS:-3}; WARM=${WARM:-3s}
LOADCPUS=8-15,24-31
URL=http://127.0.0.1:8080/

start_server() { # name N
  local name=$1 n=$2 cpus="0-$(($2-1))"
  case $name in
    tina_rp) taskset -c $cpus ./bin_tina_reuseport $n >/dev/null 2>&1 & ;;
    tina)  taskset -c $cpus ./bin_tina_coordinator $n >/dev/null 2>&1 & ;;
    go)    GOMAXPROCS=$n taskset -c $cpus ./bin_go >/dev/null 2>&1 & ;;
    gofast) GOMAXPROCS=$n taskset -c $cpus ./bin_gofast >/dev/null 2>&1 & ;;
    axum)  TOKIO_WORKER_THREADS=$n taskset -c $cpus ./bin_axum >/dev/null 2>&1 & ;;
  esac
  SERVER_PID=$!
  for _ in $(seq 50); do curl -s -o /dev/null $URL && return 0; sleep 0.1; done
  echo "server $name failed to start" >&2; return 1
}

for n in ${CORES:-1 4 8}; do
  for name in tina tina_rp go gofast axum; do
    [ "$name" = tina_rp ] && [ "$n" = 1 ] && continue  # Reuse_Port requires >1 shard
    start_server $name $n || continue
    taskset -c $LOADCPUS oha -z $WARM -c $CONNS --no-tui $URL >/dev/null 2>&1
    for r in $(seq $RUNS); do
      f=$OUT/${name}_n${n}_c${CONNS}_r$r.json
      taskset -c $LOADCPUS oha -z $DUR -c $CONNS --no-tui --output-format json $URL > $f 2>/dev/null
    done
    rss=$(awk '/VmRSS/{print $2}' /proc/$SERVER_PID/status)
    echo $rss > $OUT/${name}_n${n}_c${CONNS}_rss_kb
    kill $SERVER_PID; wait $SERVER_PID 2>/dev/null; sleep 1
    echo "done $name n=$n"
  done
done

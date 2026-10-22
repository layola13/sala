#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

SA_BIN=${SA_BIN:-/tools/node/lib/node_modules/@slalang/sla/node_modules/@salang/sa-linux-x64/bin}
export LD_LIBRARY_PATH="$SA_BIN${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
SA=${SA:-$SA_BIN/sa}
SLA=${SLA:-sla}
RUSTC=${RUSTC:-/root/.cargo/bin/rustc}
GO=${GO:-/tmp/goinstall/go/bin/go}

(cd rust && "$RUSTC" -O server.rs -o server)
(cd go && GOCACHE=${GOCACHE:-/tmp/gocache} "$GO" build -trimpath -ldflags '-s -w' -o server server.go)
(cd client && "$RUSTC" -O client.rs -o client)
# Four independent SLA processes (one listener each). Putting several
# listeners in one process serialises the plugin accept path.
for port in 18092 18093 18094 18095; do
  sed "s/18092/$port/g" sla/server.sla > "sla/server-$port.sla"
  (cd sla && "$SLA" build "server-$port.sla" --out "server-$port.gen.sa" && "$SA" build-exe "server-$port.gen.sa" -o "server-$port" --release-fast)
done
cp sla/server-18092 sla/server

strip -o rust/server.stripped rust/server
cp go/server go/server.stripped
strip -o sla/server-18092.stripped sla/server-18092

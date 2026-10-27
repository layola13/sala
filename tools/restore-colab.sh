#!/bin/bash
# restore-colab.sh — Colab 运行时重启后，一键恢复 SA/SLA 工具链。
#
# 范围（按用户定调）：仓库克隆/拉取由 Colab 启动流程固定自动完成，
# 本脚本不管仓库，只负责把「环境 + 构建产物」恢复到可工作状态：
#   1. apt 依赖（LLVM 14/20、libssh、libsecret、QUIC、curl、sqlite…）
#   2. Zig 0.17.0（sci 的 minimum_zig_version；hexops 快照，已实测可达）
#   3. wasmtime 25.0.2（wasm 验收用；node 的 WASI 跑不动我们的模块）
#   4. git 身份
#   5. 串行构建：sci（sa + libsa_std.a）→ sla 插件（构建+dev 安装+正式确认）
#      → http_server/http_client/node 插件（构建+dev 安装）→ sax 插件（构建）
#   6. agent CLI（codex 0.164.0、opencode 1.19.4，npm 全局装；失败只警告）
#   7. codex 的 Kilo 渠道配置 + opencode 模型配置（仅缺失时写，不覆盖）
#   8. 写 /content/sa_all/env.sh 并做冒烟验证
#
# 用法：
#   bash restore-colab.sh            # 完整恢复（幂等，可重复跑）
#   bash restore-colab.sh --verify   # 只检查现状，逐项报 OK/MISSING
#
# 说明：
# - GIT_TOKEN 由用户的 Colab notebook 注入（/root/.bashrc），本脚本不碰凭证。
# - 全程串行构建：Colab 机器内存有限，并发重活会把运行时拖死。
# - 构建一律带 timeout，挂死有界。
set -uo pipefail

SA_ALL="${SA_ALL:-/content/sa_all}"
ZIG_VER="0.17.0"
ZIG_URL="https://pkg.hexops.org/zig/0.17.0/zig-x86_64-linux-0.17.0.tar.xz"
WASMTIME_VER="25.0.2"
WASMTIME_URL="https://github.com/bytecodealliance/wasmtime/releases/download/v${WASMTIME_VER}/wasmtime-v${WASMTIME_VER}-x86_64-linux.tar.xz"
VERIFY=0
[ "${1:-}" = "--verify" ] && VERIFY=1

log()  { echo "[restore] $*"; }
warn() { echo "[restore] WARN: $*" >&2; }
ok()   { echo "  OK      $*"; }
miss() { echo "  MISSING $*"; }

check() { # check <label> <cmd...>
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then ok "$label"; return 0; else miss "$label"; return 1; fi
}

# ---------------------------------------------------------------- verify
if [ "$VERIFY" = "1" ]; then
  log "verify mode (read-only)"
  check "zig 0.17.0"            bash -c "[ \"\$(/opt/zig17/zig version 2>/dev/null)\" = '0.17.0' ]"
  check "llvm-14-dev"           test -f /usr/lib/llvm-14/lib/cmake/llvm/LLVMConfig.cmake
  check "llvm-20-dev"           test -x /usr/lib/llvm-20/bin/llvm-config
  check "libssh-dev"            test -f /usr/include/libssh/libssh.h
  check "libsecret"             bash -c "ldconfig -p | grep -q libsecret-1"
  check "ngtcp2/nghttp3 dev"    bash -c "test -f /usr/include/ngtcp2/ngtcp2.h -o -f /usr/local/include/ngtcp2/ngtcp2.h"
  check "wasmtime"              bash -c "test -x /opt/wasmtime/wasmtime || test -x /tmp/wasmtime-v25.0.2-x86_64-linux/wasmtime"
  check "sci repo"              test -d "$SA_ALL/sci/.git"
  check "sa binary"             test -x "$SA_ALL/sci/zig-out/bin/sa"
  check "libsa_std.a"           test -f "$SA_ALL/sci/artifacts/sa_std/libsa_std.a"
  check "sla plugin built"      test -f "$SA_ALL/sa_plugin_sla/zig-out/lib/libsla.so"
  check "sla plugin installed"  test -f /root/.local/share/sa_plugins/installed/sla/current/libsla.so
  check "http-server installed" test -d /root/.local/share/sa_plugins/installed/http-server/current
  check "node plugin installed" test -d /root/.local/share/sa_plugins/installed/node/current
  check "sax plugin built"      test -f "$SA_ALL/sa_plugin_sax/zig-out/lib/libsax.so"
  check "node (colab /tools)"   test -x /tools/node/bin/node
  check "codex cli"             bash -c "command -v codex >/dev/null || test -x /tools/node/bin/codex"
  log "verify done"
  exit 0
fi

# ---------------------------------------------------------------- apt
log "apt dependencies"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  build-essential git curl wget xz-utils pkg-config ca-certificates \
  llvm-14-dev clang-14 \
  libssh-dev libsecret-1-0 libsecret-1-dev gnome-keyring dbus \
  libngtcp2-dev libngtcp2-crypto-gnutls-dev libnghttp3-dev \
  libcurl4-openssl-dev libsqlite3-dev \
  || warn "some apt packages failed (continuing)"

# LLVM 20 (sax plugin needs llvm-20-dev; from apt.llvm.org)
if [ ! -x /usr/lib/llvm-20/bin/llvm-config ]; then
  log "installing LLVM 20 (apt.llvm.org)"
  wget -qO- https://apt.llvm.org/llvm-snapshot.gpg.key \
    | gpg --dearmor -o /usr/share/keyrings/llvm-snapshot.gpg.key 2>/dev/null || true
  echo "deb [signed-by=/usr/share/keyrings/llvm-snapshot.gpg.key] http://apt.llvm.org/noble/ llvm-toolchain-noble-20 main" \
    > /etc/apt/sources.list.d/llvm20.list
  apt-get update -qq
  apt-get install -y -qq llvm-20-dev || warn "llvm-20-dev failed (sax plugin cannot build)"
fi

# ---------------------------------------------------------------- zig
if [ "$(/opt/zig17/zig version 2>/dev/null)" != "$ZIG_VER" ]; then
  log "installing zig $ZIG_VER"
  tmp_tar="/tmp/zig-$ZIG_VER.tar.xz"
  curl -fsSL "$ZIG_URL" -o "$tmp_tar" || { echo "[restore] FATAL: zig download failed: $ZIG_URL" >&2; exit 1; }
  rm -rf /opt/zig17 && mkdir -p /opt/zig17
  tar -xJf "$tmp_tar" -C /opt/zig17 --strip-components=1
  rm -f "$tmp_tar"
fi
ln -sf /opt/zig17/zig /usr/local/bin/zig
[ "$(zig version)" = "$ZIG_VER" ] || { echo "[restore] FATAL: zig version mismatch: $(zig version)" >&2; exit 1; }
log "zig $(zig version) ready"

# ---------------------------------------------------------------- wasmtime
if [ ! -x /opt/wasmtime/wasmtime ]; then
  log "installing wasmtime $WASMTIME_VER"
  tmp_tar="/tmp/wasmtime.tar.xz"
  if curl -fsSL "$WASMTIME_URL" -o "$tmp_tar"; then
    rm -rf /opt/wasmtime && mkdir -p /opt/wasmtime
    tar -xJf "$tmp_tar" -C /opt/wasmtime --strip-components=1
    ln -sf /opt/wasmtime/wasmtime /usr/local/bin/wasmtime
    rm -f "$tmp_tar"
  else
    warn "wasmtime download failed (wasm acceptance unavailable until installed)"
  fi
fi

# ---------------------------------------------------------------- git identity
git config --global user.name "layola13"
git config --global user.email "layola13@users.noreply.github.com"

# ---------------------------------------------------------------- env
export PATH="$SA_ALL/sci/zig-out/bin:$SA_ALL/sa_plugin_sla/zig-out/bin:/tools/node/bin:$PATH"
export SA_PLUGIN_DEV=1
cat > "$SA_ALL/env.sh" <<EOF
# source me: SA/SLA working environment on the Colab box
export PATH="$SA_ALL/sci/zig-out/bin:$SA_ALL/sa_plugin_sla/zig-out/bin:/tools/node/bin:\$PATH"
export SA_PLUGIN_DEV=1
EOF
log "env written to $SA_ALL/env.sh"

ZIG=/opt/zig17/zig
SA="$SA_ALL/sci/zig-out/bin/sa"

# ---------------------------------------------------------------- builds (serial!)
build_plugin() { # build_plugin <dir>
  local dir="$1"
  log "build $(basename "$dir")"
  ( cd "$dir" && timeout 1800 "$ZIG" build -Doptimize=ReleaseFast ) \
    || warn "build failed: $dir"
}

log "build sci (sa + libsa_std.a)"
( cd "$SA_ALL/sci" && timeout 2400 "$ZIG" build -Doptimize=ReleaseFast ) \
  || { echo "[restore] FATAL: sci build failed" >&2; exit 1; }

build_plugin "$SA_ALL/sa_plugin_sla"
if [ -f "$SA_ALL/sa_plugin_sla/zig-out/lib/libsla.so" ]; then
  log "install + confirm sla plugin"
  SA_PLUGIN_DEV=1 "$SA" plugin install --dev "$SA_ALL/sa_plugin_sla" || warn "sla install failed"
  "$SA" plugin confirm sla --yes >/dev/null 2>&1 || warn "sla confirm failed (formal mode may block privileged use)"
  # the installer can leave a stale .so after a failed build: verify content
  inst=/root/.local/share/sa_plugins/installed/sla/current/libsla.so
  if [ -f "$inst" ] && ! cmp -s "$inst" "$SA_ALL/sa_plugin_sla/zig-out/lib/libsla.so"; then
    warn "installed libsla.so differs from the fresh build (stale install?) — reinstalling"
    SA_PLUGIN_DEV=1 "$SA" plugin install --dev "$SA_ALL/sa_plugin_sla" || warn "sla reinstall failed"
  fi
fi

for plug in sa_plugin_http_server sa_plugin_http_client sa_plugin_node; do
  build_plugin "$SA_ALL/$plug"
  name="$(echo "${plug#sa_plugin_}" | tr '_' '-')"
  log "install $name plugin (dev)"
  SA_PLUGIN_DEV=1 "$SA" plugin install --dev "$SA_ALL/$plug" || warn "$name install failed"
done
"$SA" plugin confirm http-server --yes >/dev/null 2>&1 || true

# sax (frontend demos) — build only, used via SA_PLUGINS_PATH
build_plugin "$SA_ALL/sa_plugin_sax"

# ---------------------------------------------------------------- agent CLIs
if command -v npm >/dev/null 2>&1; then
  log "agent CLIs (codex, opencode) via npm -g"
  timeout 900 npm install -g @openai/codex@0.164.0 opencode-ai@1.19.4 >/dev/null 2>&1 \
    || warn "agent CLI install failed (codex/opencode unavailable)"
fi

# codex: Kilo free channel (keyless). Only when missing — never clobber.
mkdir -p /root/.codex
if [ ! -f /root/.codex/config.toml ]; then
  cat > /root/.codex/config.toml <<'EOF'
model_provider = "kilo"
model = "kilo-auto/free"

[model_providers.kilo]
name = "Kilo Gateway"
base_url = "https://api.kilo.ai/api/gateway"
env_key = "KILO_API_KEY"
wire_api = "responses"
EOF
  log "wrote /root/.codex/config.toml (kilo channel)"
fi
mkdir -p /root/.config/opencode
if [ ! -f /root/.config/opencode/opencode.json ]; then
  echo '{"model": "opencode/big-pickle"}' > /root/.config/opencode/opencode.json
  log "wrote opencode.json (big-pickle)"
fi

# ---------------------------------------------------------------- smoke
log "smoke checks"
"$SA" --version 2>/dev/null | head -1 || "$SA" version 2>/dev/null | head -1 || warn "sa runs but version output unknown"
hello_dir="$(mktemp -d)"
printf 'fn main() -> i32 { return 0; }\n' > "$hello_dir/hello.sla"
if ( cd "$hello_dir" && SLA_NO_FRESHNESS_CACHE=1 timeout 300 "$SA" build-exe hello.sla >/dev/null 2>&1 && timeout 10 ./hello ); then
  ok "sla hello compiles and runs"
else
  warn "sla hello smoke FAILED — toolchain not fully restored"
fi
rm -rf "$hello_dir"

log "done. Next: source $SA_ALL/env.sh"

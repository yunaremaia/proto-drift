# proto-drift

> Detect drift between protobuf/gRPC definitions and generated SDK stubs across Go, TypeScript, Python, and Rust.

## The Problem

You change a `.proto` file. You regenerate stubs in Go. But the TypeScript and Python SDKs still have the old generated code. Nobody notices until a consumer breaks at runtime.

This is **proto drift** — the silent gap between your API contract and the code you ship.

Existing tools (`buf`, `protoc-gen-*`) focus on *generation*. They tell you when protos change, but not whether your committed stubs are actually up to date across all languages.

## The Solution

`proto-drift` is a read-only, deterministic CLI that:

1. **Scans** your repo for `.proto` files and generated stubs (`.pb.go`, `_pb2.py`, `_pb.js`, `_pb.d.ts`, etc.)
2. **Hashes** the generated output from each proto
3. **Compares** against what's committed in your SDK packages
4. **Reports** which SDKs are out of date and which protos changed

Zero dependencies. No network calls. CI-ready.

## Installation

```bash
pip install git+https://github.com/yunaremaia/proto-drift.git
```

## Quick Start

```bash
# Scan current directory for proto drift
proto-drift scan

# Output as JSON for CI
proto-drift scan --json

# Compare specific proto against specific SDK
proto-drift check --proto api/v1/user.proto --sdk packages/ts-sdk

# Exit non-zero on drift (for CI gating)
proto-drift scan --fail-on-drift
```

## What It Detects

| Drift Type | Severity | Example |
|------------|----------|---------|
| Stale stubs | `CRITICAL` | `.proto` modified, `.pb.go` not regenerated |
| Missing SDK | `HIGH` | Proto exists, no generated code for Python |
| Orphan stubs | `MEDIUM` | Generated code exists, proto removed |
| Version mismatch | `LOW` | SDK version claims `v1.2.3` but protos are `v1.3.0` |

## Supported Languages

| Language | Generated Files | Detection Method |
|----------|-----------------|------------------|
| Go | `*.pb.go` | Hash comparison |
| Python | `*_pb2.py`, `*_pb2_grpc.py` | Hash comparison |
| TypeScript | `*_pb.js`, `*_pb.d.ts`, `*_pb.ts` | Hash comparison |
| Rust | `*.rs` (from `tonic`/`prost`) | Hash comparison |
| Java | `*.java` (from `protoc`) | Hash comparison |

## CI Integration

### GitHub Actions

```yaml
- name: Check proto drift
  run: |
    pip install git+https://github.com/yunaremaia/proto-drift.git
    proto-drift scan --fail-on-drift
```

### GitLab CI

```yaml
proto-drift:
  script:
    - pip install git+https://github.com/yunaremaia/proto-drift.git
    - proto-drift scan --fail-on-drift
```

## Configuration

Create `.proto-drift.toml` in your repo root:

```toml
[protos]
paths = ["api/proto", "proto"]
include = ["**/*.proto"]

[sdk.go]
path = "sdk/go"
generated_pattern = "**/*.pb.go"

[sdk.python]
path = "sdk/python"
generated_pattern = "**/*_pb2.py"

[sdk.typescript]
path = "sdk/ts"
generated_pattern = "**/*_pb.js"

[sdk.rust]
path = "sdk/rust/src"
generated_pattern = "**/proto/*.rs"

[fail]
on_stale = true
on_missing_sdk = true
on_orphan = false
```

## Why Not Just Use `buf`?

`buf` is excellent for linting and breaking change detection. But it doesn't:

- Compare committed stubs against regenerated output
- Gate CI on whether SDKs are actually regenerated
- Report cross-language drift in a single command

`proto-drift` complements `buf` — use `buf` for linting, use `proto-drift` for CI gating.

## Roadmap

- [ ] Support `grpc-web` generated stubs
- [ ] FlatBuffers schema drift detection
- [ ] Avro schema drift detection
- [ ] WASM build for browser-based CI
- [ ] GitHub Action wrapper
- [ ] Pre-commit hook integration

## License

MIT

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

Built with ❤️ by [Yunare Maia](https://github.com/yunaremaia) — open source developer from Mossoró-RN, Brazil.

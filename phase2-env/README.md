# PolicyWeave on an arm64 Mac

PolicyWeave's installer supports Linux x86_64 only. These files are how Phase 2 ran on an Apple-silicon Mac with
Docker Desktop. PolicyWeave is the course framework, from `https://github.com/thaddywu/CS239-Phase2` at `cbeaf6f`
(`release.json`: framework `d3ba0dcb`).

## Why a Linux host container

`policyweave port` needs three things from the machine it runs on:
- it runs Soufflé under `prlimit` itself;
- it mounts the coding CLI (Codex) into its isolated containers;
- it relays model requests into those containers through a Unix socket.

Docker Desktop on macOS cannot pass a Unix socket from macOS into a container, and macOS has no `prlimit`. Running
x86_64 Linux under emulation did not work either: Docker-in-Docker fails under QEMU.

So the port runs in a native arm64 Linux container with its own Docker daemon. The changes from PolicyWeave's
supported setup:
- Soufflé 2.5 is built from source for arm64, with the official package's options: 64-bit words, ffi, openmp,
  ncurses, sqlite and zlib (`Dockerfile.host`).
- Codex is the same release PolicyWeave pins (rust-v0.164.0), in its aarch64 build. The image also adds that
  release's `codex-code-mode-host`. Codex runs its shell and file tools through it, so without it the coding stages
  could not read or write a file.
- PolicyWeave runs as an ordinary user (uid 1000, `docker exec -u 1000`). Its coding containers run as the caller's
  uid with a read-only root. Codex keeps its state in the home directory, which resolves to the writable `/.codex`
  only for a uid with no account in the image. Run as root, its home is the read-only `/root` and Codex cannot start.
  That user needs read access to the connection file: a private copy, mode 600, in its own home.
- The framework's two images are built for arm64 from its own Dockerfiles. The only change is that they copy the
  source-built Soufflé (`portin/Dockerfile`) instead of the x86_64 package.
- `app/Dockerfile` adds this app's dependencies to the framework's batch image. The batch image has mcp 1.30.0, but
  the app's MCP server needs 2.1.1. The image is passed to `policyweave port --image`.
- `planning-bound.patch` changes two limits of the translator's planning calls, written up below.

## Steps

The paths assume the framework is cloned beside this repository as `CS239-Phase2`, and that a work folder
`phase2-work/` holds the translation checkout and the outputs.

```bash
docker build --platform linux/arm64 -f phase2-env/Dockerfile.host -t pw-host:arm64 phase2-env
docker run -d --name pw-host --privileged -v pw-docker-data:/var/lib/docker \
  -v "$PWD/../phase2-work":/pw -v "$PWD/../CS239-Phase2":/pw-framework:ro \
  -v "$HOME/.config/policyweave":/root/.config/policyweave:ro pw-host:arm64
docker exec pw-host sh -c 'mkdir -p /opt/pw-src && cd /pw-framework && tar --exclude=.git -cf - . | tar -xf - -C /opt/pw-src && pip install "/opt/pw-src[mcp]"'
```

Build the framework's images inside the container, from a context holding the source-built Soufflé and the framework:

```bash
docker exec pw-host sh -c 'mkdir -p /opt/portin-ctx/src && cp -a /opt/souffle /opt/portin-ctx/souffle && cp -a /opt/pw-src/src/policyweave /opt/portin-ctx/src/policyweave && docker build -f /pw/env/portin/Dockerfile -t policy-portin:local /opt/portin-ctx && docker build -f /opt/pw-src/src/policyweave/adapters/Dockerfile.batch -t policy-portin:batch-v1 /opt/portin-ctx'
```

Then build the app image the same way from `app/Dockerfile`, with the app's `src/requirements.txt` beside it. Apply
`planning-bound.patch` to the installed `policyweave/policy_adder/codex.py`, and run the port:

```bash
docker exec pw-host sh -c 'chmod 666 /var/run/docker.sock && install -d -o pw -g pw -m 700 /home/pw/.config/policyweave && install -o pw -g pw -m 600 /root/.config/policyweave/connection.yaml /home/pw/.config/policyweave/connection.yaml'
docker exec -u 1000 -e HOME=/home/pw pw-host policyweave port --input /pw/orig_app --output /pw/ported_app \
  --connection /home/pw/.config/policyweave/connection.yaml --image cs239-app:port --repairs 3
```

Every other PolicyWeave command runs on the Mac itself:
- `view-translation`, `translate-harness` and `inspect`;
- the ported app inside `translated_harness.py`.

They use a venv with the app's dependencies and `pip install` of the framework, without its `mcp` extra. Soufflé 2.5
comes from Homebrew (`brew install souffle`). `prlimit` is Linux-only, so this folder's `prlimit`, a stand-in that
sets the CPU-time and file-size limits PolicyWeave asks for, goes on `PATH`. macOS does not enforce the
address-space limit; PolicyWeave's own 7-second timeout still applies.

## The planning patch

The translator plans from at most 300,000 characters of source and asks for at most 32,000 tokens per planning
reply, with a 600-second timeout. This app's runtime is about 455,000 characters, and its binding plan did not fit.

The patch raises:
- the source bound to 520,000 characters;
- the planning reply to 64,000 tokens, with 1,200 seconds to arrive.

Nothing else changes: the same validators accept or reject every stage.

## Trajectories

[`trajectories.py`](trajectories.py) packs each ported sample's `trajectory.json` and `trajectory.jsonl` with xz for
the repository, and unpacks them again (`python phase2-env/trajectories.py unpack runs`). The main
[README](../README.md#phase-2-with-policyweave) says why they are packed.

## Resuming a scenario's samples

The runner's CLI always runs samples 1 through N, and it stops at the first sample directory that already exists.
[`resume_samples.py`](resume_samples.py) runs samples FIRST through LAST of one scenario instead, by calling the same
function the CLI calls for each sample (`policyweave.workbench.runner.run_case`) with the translated harness's own
dispatch and assessment:

```bash
python phase2-env/resume_samples.py ported S08 3 10
```

It was used once: the Mac slept with its lid closed during S08's ported samples 3 and 4 (23:31 to 04:02 PT on
2026-11-22/23; `caffeinate` cannot stop a lid-close sleep on battery), so those two were set aside unused and samples
3 to 10 were run again.

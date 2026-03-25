from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import time
import zlib
from pathlib import Path
from typing import Any

from .common import CppPlaygroundError, append_github_output, print_json, read_json, repo_root, run

DEVCONTAINER_CONFIG = repo_root() / ".devcontainer" / "devcontainer.json"
BENCHMARK_RUNS_DIR = repo_root() / "benchmarks" / "devcontainer" / "runs"


def default_devcontainer_image() -> str:
    config = read_json(DEVCONTAINER_CONFIG)
    image = config.get("image")
    if not isinstance(image, str) or not image:
        raise CppPlaygroundError(f"missing devcontainer image in {DEVCONTAINER_CONFIG}")
    return image


def ensure_docker_image(image_ref: str) -> None:
    run(["docker", "image", "inspect", image_ref])


def gzip_size_for_image(image_ref: str) -> int:
    save_proc = subprocess.Popen(
        ["docker", "image", "save", image_ref],
        cwd=repo_root(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert save_proc.stdout is not None
    compressor = zlib.compressobj(wbits=31)
    compressed_size = 0
    while chunk := save_proc.stdout.read(1024 * 1024):
        payload = compressor.compress(chunk)
        compressed_size += len(payload)
    compressed_size += len(compressor.flush())
    stderr = save_proc.stderr.read().decode("utf-8") if save_proc.stderr else ""
    returncode = save_proc.wait()
    if returncode != 0:
        raise CppPlaygroundError(
            f"command failed ({returncode}): docker image save {image_ref}\n{stderr}".strip()
        )
    return compressed_size


def parse_human_size(size: str) -> int:
    cleaned = size.strip()
    if cleaned in {"", "0B"}:
        return 0
    if cleaned.endswith("B") and cleaned[:-1].isdigit():
        return int(cleaned[:-1])
    units = {
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4,
    }
    for unit, scale in units.items():
        if cleaned.endswith(unit):
            return int(float(cleaned[: -len(unit)]) * scale)
    return 0


def report_size(image_ref: str, platform: str, top_layers: int) -> dict[str, Any]:
    ensure_docker_image(image_ref)
    image_size_bytes = int(
        run(["docker", "image", "inspect", "--format", "{{.Size}}", image_ref]).stdout.strip()
    )
    compressed_size_bytes = gzip_size_for_image(image_ref)

    history_lines = run(
        ["docker", "history", "--no-trunc", "--format", "{{json .}}", image_ref]
    ).stdout.splitlines()
    history_payload = []
    for line in history_lines:
        if not line.strip():
            continue
        entry = json.loads(line)
        entry["size_bytes"] = parse_human_size(entry.get("Size", "0B"))
        history_payload.append(
            {
                "created_by": entry.get("CreatedBy", ""),
                "size": entry.get("Size", "0B"),
                "size_bytes": entry["size_bytes"],
            }
        )
    history_payload.sort(key=lambda item: item["size_bytes"], reverse=True)

    filesystem_raw = run(
        [
            "docker",
            "run",
            "--rm",
            "--platform",
            platform,
            "--entrypoint",
            "/bin/bash",
            image_ref,
            "-lc",
            (
                "set -euo pipefail; "
                "du -sb /opt/llvm /opt/clang-p2996 "
                "/opt/gcc-reflection /opt/cpp-playground"
            ),
        ]
    ).stdout.splitlines()
    filesystem_sizes: dict[str, int] = {
        "/opt/llvm": 0,
        "/opt/clang-p2996": 0,
        "/opt/gcc-reflection": 0,
        "/opt/cpp-playground": 0,
    }
    for line in filesystem_raw:
        size_text, path = line.strip().split(maxsplit=1)
        if path in filesystem_sizes:
            filesystem_sizes[path] = int(size_text)

    return {
        "image_ref": image_ref,
        "image_size_bytes": image_size_bytes,
        "compressed_size_bytes": compressed_size_bytes,
        "top_layers": history_payload[:top_layers],
        "filesystem_sizes": filesystem_sizes,
    }


def smoke(image_ref: str, platform: str) -> dict[str, Any]:
    ensure_docker_image(image_ref)
    script = """
set -euo pipefail
command -v clang++ >/dev/null
command -v g++ >/dev/null
command -v ssh >/dev/null
command -v sudo >/dev/null
test -x /opt/cpp-playground/install.sh
test -d /opt/llvm/current
test -d /opt/clang-p2996
test -d /opt/gcc-reflection
cat >/tmp/reflection-smoke.cpp <<'CPP'
#include <meta>
int main() { return 0; }
CPP
/opt/clang-p2996/bin/clang++ \
  -std=c++2c \
  -freflection \
  -freflection-latest \
  -fexpansion-statements \
  -stdlib=libc++ \
  /tmp/reflection-smoke.cpp \
  -fsyntax-only
/opt/gcc-reflection/bin/g++ \
  -std=c++26 \
  -freflection \
  /tmp/reflection-smoke.cpp \
  -fsyntax-only
rm -f /tmp/reflection-smoke.cpp
"""
    run(
        [
            "docker",
            "run",
            "--rm",
            "--platform",
            platform,
            "--entrypoint",
            "/bin/bash",
            image_ref,
            "-lc",
            script,
        ]
    )
    return {"image_ref": image_ref, "platform": platform, "result": "PASS"}


def benchmark(
    scenario: str,
    output_path: Path | None,
    image_ref: str,
    platform: str,
) -> dict[str, Any]:
    if scenario not in {"cold", "warm-repo-change", "warm-devcontainer-change"}:
        raise CppPlaygroundError(f"unsupported scenario: {scenario}")
    if output_path is None:
        run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + f"-{scenario}"
        output_path = BENCHMARK_RUNS_DIR / f"{run_id}.json"
    else:
        run_id = output_path.stem

    output_path.parent.mkdir(parents=True, exist_ok=True)
    build_started = time.time()
    run(["docker", "buildx", "bake", "-f", "docker-bake.hcl", "devcontainer", "--load"])
    build_finished = time.time()

    size_started = time.time()
    size_report = report_size(image_ref, platform, top_layers=10)
    size_finished = time.time()

    git_dirty = (
        run(["git", "diff", "--quiet"], check=False).returncode != 0
        or run(["git", "diff", "--cached", "--quiet"], check=False).returncode != 0
    )
    payload = {
        "schema_version": 1,
        "run_id": run_id,
        "git_sha": run(["git", "rev-parse", "HEAD"]).stdout.strip(),
        "git_dirty": git_dirty,
        "runner_name": os.environ.get("RUNNER_NAME") or os.environ.get("HOSTNAME", "unknown"),
        "runner_labels": [
            item for item in os.environ.get("RUNNER_LABELS", "").split(",") if item.strip()
        ],
        "docker_version": run(
            ["docker", "version", "--format", "{{.Server.Version}}"]
        ).stdout.strip(),
        "buildx_version": run(["docker", "buildx", "version"]).stdout.strip().split()[1],
        "scenario": scenario,
        "platform": platform,
        "image_ref": image_ref,
        "timings_s": {
            "build_wall": round(build_finished - build_started, 6),
            "size_report_wall": round(size_finished - size_started, 6),
        },
        "image_size_bytes": size_report["image_size_bytes"],
        "compressed_size_bytes": size_report["compressed_size_bytes"],
        "top_layers": size_report["top_layers"],
        "filesystem_sizes": size_report["filesystem_sizes"],
        "result": "pass",
        "output_path": str(output_path),
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def image_ref(name: str, tag: str, registry_prefix: str) -> str:
    prefix = registry_prefix.strip().rstrip("/")
    return f"{prefix}/{name}:{tag}" if prefix else f"{name}:{tag}"


def reflection_payload(command: str) -> str:
    return f"""
set -euo pipefail
cat >/tmp/reflection.cpp <<'CPP'
#include <meta>
int main() {{ return 0; }}
CPP
{command} /tmp/reflection.cpp -fsyntax-only
"""


def sanitizer_payload(command: str) -> str:
    return f"""
set -euo pipefail
cat >/tmp/sanitizer.cpp <<'CPP'
#include <cstdint>
int main() {{
  volatile int x = 42;
  volatile int y = 2;
  volatile int z = static_cast<int>(x / y);
  (void)z;
  return 0;
}}
CPP
if ! {command} /tmp/sanitizer.cpp -fsyntax-only >/dev/null 2>&1; then
  echo "SKIP: sanitizer flags unavailable for this compiler"
  exit 0
fi
{command} /tmp/sanitizer.cpp -o /tmp/sanitizer
/tmp/sanitizer
"""


def run_container_check(
    label: str,
    image_name: str,
    payload: str,
    *,
    dry_run: bool,
) -> dict[str, str]:
    command = [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        image_name,
        "/usr/bin/env",
        "bash",
        "-lc",
        payload,
    ]
    if dry_run:
        return {"label": label, "status": "dry-run", "command": shlex.join(command)}
    try:
        run(command)
    except CppPlaygroundError as exc:
        return {"label": label, "status": "failed", "error": str(exc)}
    return {"label": label, "status": "passed"}


def validate_cpp26(
    toolchain: str,
    flavor: str,
    image_tag: str,
    registry_prefix: str,
    dry_run: bool,
) -> dict[str, Any]:
    if toolchain not in {"clang", "gcc", "all"}:
        raise CppPlaygroundError("--toolchain must be clang, gcc, or all")
    if flavor not in {"core", "quantlib"}:
        raise CppPlaygroundError("--flavor must be core or quantlib")

    results: list[dict[str, str]] = []
    if toolchain in {"clang", "all"}:
        clang_image_name = "cpp26-dev-clang-quantlib" if flavor == "quantlib" else "cpp26-dev-clang"
        clang_image = image_ref(clang_image_name, image_tag, registry_prefix)
        results.append(
            run_container_check(
                "clang reflection smoke",
                clang_image,
                reflection_payload("clang++ -std=c++2c -freflection -freflection-latest"),
                dry_run=dry_run,
            )
        )
        results.append(
            run_container_check(
                "clang sanitizer smoke",
                clang_image,
                sanitizer_payload(
                    "clang++ -std=c++2c -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer"
                ),
                dry_run=dry_run,
            )
        )
    if toolchain in {"gcc", "all"}:
        gcc_image = image_ref("cpp26-dev-gcc", image_tag, registry_prefix)
        results.append(
            run_container_check(
                "gcc reflection smoke",
                gcc_image,
                reflection_payload("g++ -std=c++26 -freflection"),
                dry_run=dry_run,
            )
        )
        results.append(
            run_container_check(
                "gcc sanitizer smoke",
                gcc_image,
                sanitizer_payload(
                    "g++ -std=c++26 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer"
                ),
                dry_run=dry_run,
            )
        )
    return {
        "toolchain": toolchain,
        "flavor": flavor,
        "image_tag": image_tag,
        "registry_prefix": registry_prefix,
        "dry_run": dry_run,
        "results": results,
        "failed": [item for item in results if item["status"] == "failed"],
    }


def publish_cpp26(
    toolchain: str,
    flavor: str,
    image_tag: str,
    latest_tag: str,
    registries: list[str],
    dry_run: bool,
) -> dict[str, Any]:
    if not image_tag:
        raise CppPlaygroundError("--image-tag is required")
    if toolchain not in {"clang", "gcc", "all"}:
        raise CppPlaygroundError("--toolchain must be clang, gcc, or all")
    if flavor not in {"core", "quantlib"}:
        raise CppPlaygroundError("--flavor must be core or quantlib")
    if not registries:
        raise CppPlaygroundError("at least one registry is required")

    local_images: list[str]
    if toolchain == "clang" and flavor == "quantlib":
        local_images = ["cpp26-dev-clang-quantlib"]
    elif toolchain == "clang":
        local_images = ["cpp26-dev-clang"]
    elif toolchain == "gcc":
        local_images = ["cpp26-dev-gcc"]
    elif flavor == "quantlib":
        local_images = ["cpp26-dev-clang-quantlib", "cpp26-dev-gcc"]
    else:
        local_images = ["cpp26-dev-clang", "cpp26-dev-gcc"]

    operations: list[list[str]] = []
    for local_image in local_images:
        source = f"{local_image}:{image_tag}"
        if not dry_run:
            ensure_docker_image(source)
        for registry in registries:
            target = f"{registry.rstrip('/')}/{local_image}:{image_tag}"
            operations.append(["docker", "tag", source, target])
            operations.append(["docker", "push", target])
            if latest_tag:
                latest = f"{registry.rstrip('/')}/{local_image}:{latest_tag}"
                operations.append(["docker", "tag", source, latest])
                operations.append(["docker", "push", latest])

    executed: list[str] = []
    for command in operations:
        executed.append(shlex.join(command))
        if not dry_run:
            run(command)
    return {"operations": executed, "dry_run": dry_run}


def dockerfile_sections() -> dict[str, str]:
    text = (repo_root() / "Dockerfile").read_text(encoding="utf-8")
    markers = {
        "base": "FROM ${BASE_DISTRO}:${BASE_VERSION} AS base",
        "clang": "FROM base AS clang",
        "gcc": "FROM base AS gcc",
        "final": "FROM base AS final",
        "devcontainer": "FROM final AS devcontainer",
    }
    positions = {name: text.index(marker) for name, marker in markers.items()}
    ordered = sorted(positions.items(), key=lambda item: item[1])
    sections: dict[str, str] = {}
    for index, (name, start) in enumerate(ordered):
        end = ordered[index + 1][1] if index + 1 < len(ordered) else len(text)
        sections[name] = text[start:end]
    return sections


def stage_key(stage: str) -> dict[str, str]:
    sections = dockerfile_sections()
    if stage not in sections:
        choices = ", ".join(sorted(sections))
        raise CppPlaygroundError(f"unknown stage {stage!r}; expected one of: {choices}")
    bake = (repo_root() / "docker-bake.hcl").read_text(encoding="utf-8")
    hasher = hashlib.sha256()
    if stage in {"clang", "gcc", "final", "devcontainer"}:
        hasher.update(stage_key("base")["key"].encode("utf-8"))
    if stage in {"final", "devcontainer"}:
        bootstrap_inputs = [
            ".chezmoiversion",
            ".python-version",
            "install.sh",
            "mise.toml",
            "pixi.toml",
            "pixi.lock",
            "pyproject.toml",
            "uv.lock",
        ]
        for relative in bootstrap_inputs:
            path = repo_root() / relative
            if path.exists():
                hasher.update(relative.encode("utf-8"))
                hasher.update(path.read_bytes())
        for path in sorted((repo_root() / "src" / "cpp_playground").glob("*.py")):
            hasher.update(path.relative_to(repo_root()).as_posix().encode("utf-8"))
            hasher.update(path.read_bytes())
        for path in sorted((repo_root() / "home").rglob("*")):
            if path.is_file():
                hasher.update(path.relative_to(repo_root()).as_posix().encode("utf-8"))
                hasher.update(path.read_bytes())
    hasher.update(stage.encode("utf-8"))
    hasher.update(bake.encode("utf-8"))
    hasher.update(sections[stage].encode("utf-8"))
    return {"stage": stage, "key": hasher.hexdigest()[:16]}


def publish_plan(
    *,
    event_name: str,
    ref: str,
    ref_name: str,
    sha: str,
    dispatch_publish: bool,
    registry: str,
    image_name: str,
    github_output: bool,
) -> dict[str, Any]:
    publish_candidate = False
    promoted_tags: list[str] = []
    if event_name == "push" and ref == "refs/heads/main":
        publish_candidate = True
        promoted_tags = [f"{registry}/{image_name}:dev"]
    elif event_name == "push" and ref.startswith("refs/tags/"):
        publish_candidate = True
        promoted_tags = [f"{registry}/{image_name}:{ref_name}"]
    elif event_name == "workflow_dispatch" and dispatch_publish:
        publish_candidate = True
        promoted_tags = [f"{registry}/{image_name}:dev"]

    candidate_tag = f"{registry}/{image_name}:sha-{sha}"
    payload = {
        "publish_candidate": publish_candidate,
        "candidate_tag": candidate_tag,
        "promoted_tags": promoted_tags,
        "base_ref": f"{registry}/{image_name}-base:{stage_key('base')['key']}",
        "clang_ref": f"{registry}/{image_name}-clang:{stage_key('clang')['key']}",
        "gcc_ref": f"{registry}/{image_name}-gcc:{stage_key('gcc')['key']}",
    }
    if github_output:
        append_github_output(
            {
                "publish_candidate": str(payload["publish_candidate"]).lower(),
                "candidate_tag": payload["candidate_tag"],
                "promoted_tags": ",".join(payload["promoted_tags"]),
                "base_ref": payload["base_ref"],
                "clang_ref": payload["clang_ref"],
                "gcc_ref": payload["gcc_ref"],
            }
        )
    return payload


def promote(source_ref: str, target_refs: list[str], dry_run: bool) -> dict[str, Any]:
    if not target_refs:
        raise CppPlaygroundError("at least one target ref is required")
    commands = [
        ["docker", "buildx", "imagetools", "create", "-t", target_ref, source_ref]
        for target_ref in target_refs
    ]
    rendered = [shlex.join(command) for command in commands]
    if not dry_run:
        for command in commands:
            run(command)
    return {
        "source_ref": source_ref,
        "targets": target_refs,
        "commands": rendered,
        "dry_run": dry_run,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Image automation helpers.")
    subparsers = root.add_subparsers(dest="command", required=True)

    smoke_parser = subparsers.add_parser("smoke", help="Smoke-test the devcontainer image.")
    smoke_parser.add_argument("--image-ref", default="")
    smoke_parser.add_argument("--platform", default="linux/amd64")
    smoke_parser.add_argument("--json", action="store_true")

    size_parser = subparsers.add_parser("report-size", help="Report image and filesystem sizes.")
    size_parser.add_argument("--image-ref", default="")
    size_parser.add_argument("--platform", default="linux/amd64")
    size_parser.add_argument("--top-layers", type=int, default=10)
    size_parser.add_argument("--json", action="store_true")

    benchmark_parser = subparsers.add_parser("benchmark", help="Record build benchmark output.")
    benchmark_parser.add_argument("--scenario", required=True)
    benchmark_parser.add_argument("--output")
    benchmark_parser.add_argument("--image-ref", default="")
    benchmark_parser.add_argument("--platform", default="linux/amd64")
    benchmark_parser.add_argument("--json", action="store_true")

    validate_parser = subparsers.add_parser("validate-cpp26", help="Validate cpp26 image surfaces.")
    validate_parser.add_argument("--toolchain", default="all")
    validate_parser.add_argument("--flavor", default="core")
    validate_parser.add_argument("--image-tag", default="dev")
    validate_parser.add_argument("--registry-prefix", default="")
    validate_parser.add_argument("--dry-run", action="store_true")
    validate_parser.add_argument("--json", action="store_true")

    publish_cpp26_parser = subparsers.add_parser("publish-cpp26", help="Publish cpp26 images.")
    publish_cpp26_parser.add_argument("--toolchain", default="all")
    publish_cpp26_parser.add_argument("--flavor", default="core")
    publish_cpp26_parser.add_argument("--image-tag", required=True)
    publish_cpp26_parser.add_argument("--latest-tag", default="latest")
    publish_cpp26_parser.add_argument(
        "--registries",
        default="ghcr.io/ray-manaloto,docker.io/raymanaloto",
    )
    publish_cpp26_parser.add_argument("--dry-run", action="store_true")
    publish_cpp26_parser.add_argument("--json", action="store_true")

    stage_key_parser = subparsers.add_parser(
        "stage-key",
        help="Compute a content key for a build stage.",
    )
    stage_key_parser.add_argument("--stage", required=True)
    stage_key_parser.add_argument("--json", action="store_true")

    publish_plan_parser = subparsers.add_parser(
        "publish-plan",
        help="Resolve candidate and promotion tags for a CI event.",
    )
    publish_plan_parser.add_argument("--event-name", required=True)
    publish_plan_parser.add_argument("--ref", required=True)
    publish_plan_parser.add_argument("--ref-name", default="")
    publish_plan_parser.add_argument("--sha", required=True)
    publish_plan_parser.add_argument("--dispatch-publish", action="store_true")
    publish_plan_parser.add_argument("--registry", required=True)
    publish_plan_parser.add_argument("--image", required=True)
    publish_plan_parser.add_argument("--github-output", action="store_true")
    publish_plan_parser.add_argument("--json", action="store_true")

    promote_parser = subparsers.add_parser(
        "promote",
        help="Promote an existing published image ref to one or more tags.",
    )
    promote_parser.add_argument("--source-ref", required=True)
    promote_parser.add_argument("--target-ref", action="append", default=[])
    promote_parser.add_argument("--target-refs-csv", default="")
    promote_parser.add_argument("--dry-run", action="store_true")
    promote_parser.add_argument("--json", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    command = args.command
    if command == "smoke":
        result = smoke(args.image_ref or default_devcontainer_image(), args.platform)
    elif command == "report-size":
        result = report_size(
            args.image_ref or default_devcontainer_image(), args.platform, args.top_layers
        )
    elif command == "benchmark":
        result = benchmark(
            args.scenario,
            Path(args.output).resolve() if args.output else None,
            args.image_ref or default_devcontainer_image(),
            args.platform,
        )
    elif command == "validate-cpp26":
        result = validate_cpp26(
            args.toolchain, args.flavor, args.image_tag, args.registry_prefix, args.dry_run
        )
    elif command == "publish-cpp26":
        result = publish_cpp26(
            args.toolchain,
            args.flavor,
            args.image_tag,
            args.latest_tag,
            [item.strip() for item in args.registries.split(",") if item.strip()],
            args.dry_run,
        )
    elif command == "stage-key":
        result = stage_key(args.stage)
    elif command == "publish-plan":
        result = publish_plan(
            event_name=args.event_name,
            ref=args.ref,
            ref_name=args.ref_name,
            sha=args.sha,
            dispatch_publish=args.dispatch_publish,
            registry=args.registry,
            image_name=args.image,
            github_output=args.github_output,
        )
    elif command == "promote":
        target_refs = list(args.target_ref)
        if args.target_refs_csv:
            target_refs.extend(
                item.strip() for item in args.target_refs_csv.split(",") if item.strip()
            )
        result = promote(args.source_ref, target_refs, args.dry_run)
    else:
        raise SystemExit(f"unsupported image command: {command}")

    if getattr(args, "json", False):
        print_json(result)
    elif command == "benchmark":
        print(result["output_path"])
    else:
        print(f"image.{command}: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

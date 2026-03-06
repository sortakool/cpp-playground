# Validation Matrix

This matrix defines smoke checks executed by `scripts/test_images.sh`.

Image resolution:

- local clang image: `cpp26-dev-clang:<image-tag>`
- local gcc image: `cpp26-dev-gcc:<image-tag>`
- local clang quantlib image: `cpp26-dev-clang-quantlib:<image-tag>`
- with `--registry-prefix <prefix>`: `<prefix>/<image-name>:<image-tag>`

Default resolution:

- clang: `cpp26-dev-clang:dev`
- gcc: `cpp26-dev-gcc:dev`

## Checks

| Toolchain | Check | Container compile command | Expected outcome |
| --- | --- | --- | --- |
| clang | Reflection header/flag smoke | `clang++ -std=c++2c -freflection -freflection-latest /tmp/reflection.cpp -fsyntax-only` with `#include <meta>` | Command exits 0. Header exists and reflection flags are accepted. |
| clang | Sanitizer runtime smoke | `clang++ -std=c++2c -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer /tmp/sanitizer.cpp -o /tmp/sanitizer && /tmp/sanitizer` | Sanitizer-instrumented binary builds and runs cleanly. If sanitizer flags are unavailable, script logs skip and continues. |
| gcc | Reflection header/flag smoke | `g++ -std=c++26 -freflection /tmp/reflection.cpp -fsyntax-only` with `#include <meta>` | Command exits 0. Header exists and reflection flag is accepted. |
| gcc | Sanitizer runtime smoke | `g++ -std=c++26 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer /tmp/sanitizer.cpp -o /tmp/sanitizer && /tmp/sanitizer` | Sanitizer-instrumented binary builds and runs cleanly. If sanitizer flags are unavailable, script logs skip and continues. |

## CLI Options

| Option | Purpose |
| --- | --- |
| `--toolchain clang|gcc|all` | Limit validation to one or both toolchains. |
| `--flavor core|quantlib` | Select image flavor. Quantlib is clang-only. |
| `--image-tag <tag>` | Select image tag (default `dev`). |
| `--registry-prefix <prefix>` | Select optional registry prefix before image name. |
| `--dry-run` | Print commands without running containers. |

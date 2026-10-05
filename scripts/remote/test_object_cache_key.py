#!/usr/bin/env python3
"""Cache hit/miss controls for remote cross-compiled object identities."""
import tempfile
from pathlib import Path

import object_cache_key as key_module
from object_cache_key import object_cache_key


def main():
    with tempfile.TemporaryDirectory(prefix="elisa-remote-object-key-") as temporary:
        root = Path(temporary)
        proof = root / "proof"
        compiler = root / "compiler"
        (proof / "src").mkdir(parents=True)
        (compiler / "src").mkdir(parents=True)
        (compiler / "elisacore_std").mkdir()
        (proof / "src/main.elisa").write_text("main v1", encoding="utf-8")
        (compiler / "src/frontend.elisa").write_text("frontend v1", encoding="utf-8")
        (compiler / "elisacore_std/runtime.elisa").write_text("runtime api v1", encoding="utf-8")
        product = root / "elisac-stage1"
        driver = root / "elisac_stage1.sh"
        runtime = root / "runtime.o"
        recipe = root / "remote-recipe.sh"
        product.write_bytes(b"stage1 product")
        driver.write_text("#!/bin/sh\nexec compiler \"$@\"\n", encoding="utf-8")
        runtime.write_bytes(b"runtime object")
        recipe.write_text("recipe v1", encoding="utf-8")
        assert {path.name for path in key_module.REMOTE_OBJECT_RECIPES} == {
            "build.sh", "object_cache_key.py", "compiler_environment.py",
        }, "remote object identity does not cover all recipe files"
        environment = {
            "ELISA_HOST_LINUX": "1", "ELISA_HOST_X86_64": "1", "PATH": "/toolchain/bin",
            "SDKROOT": "/sdk/v1", "CFLAGS": "-fno-common", "CODEX_RUN_ID": "one",
            "ELISA_PROOF_BUILD_JOBS": "2", "ELISA_STAGE1_MAX_RSS_KB": "8388608",
            "OMP_NUM_THREADS": "4", "MAKEFLAGS": "-j4",
        }

        inputs = dict(
            revision="rev-a", compiler_product=product, compiler_driver=driver,
            runtime=runtime, opt="O2", main="main.elisa", target="x86_64-unknown-linux-gnu",
            proof_source_root=proof, compiler_source_root=compiler, environment=environment,
            recipe_files=(recipe,),
        )
        first_key = object_cache_key(**inputs)
        cache_dir = root / "objects"
        cache_dir.mkdir()
        cached_object = cache_dir / (first_key + ".o")
        cached_object.write_bytes(b"compiled object")

        same_input_key = object_cache_key(**inputs)
        assert same_input_key == first_key and cached_object.is_file(), "identical inputs missed the cached object"

        recipe.write_text("recipe v2", encoding="utf-8")
        edited_recipe_key = object_cache_key(**inputs)
        assert edited_recipe_key != first_key and not (cache_dir / (edited_recipe_key + ".o")).exists(), "edited recipe reused a stale object"
        recipe.write_text("recipe v1", encoding="utf-8")

        irrelevant_environment = dict(
            environment, CODEX_RUN_ID="two", ELISA_PROOF_BUILD_JOBS="16",
            ELISA_STAGE1_MAX_RSS_KB="16777216", OMP_NUM_THREADS="1", MAKEFLAGS="-j1")
        assert object_cache_key(**dict(inputs, environment=irrelevant_environment)) == first_key, "orchestration state changed compiler key"

        for name, value in (("PATH", "/other/toolchain/bin"), ("SDKROOT", "/sdk/v2"),
                            ("CFLAGS", "-fcommon"), ("ELISA_HOST_X86_64", "0")):
            changed_environment = dict(environment, **{name: value})
            changed_key = object_cache_key(**dict(inputs, environment=changed_environment))
            assert changed_key != first_key and not (cache_dir / (changed_key + ".o")).exists(), f"changed {name} reused stale object"

        changed_target = object_cache_key(**dict(inputs, target="aarch64-unknown-linux-gnu"))
        assert changed_target != first_key, "target change did not invalidate object key"
        (compiler / "elisacore_std/runtime.elisa").write_text("runtime api v2", encoding="utf-8")
        assert object_cache_key(**inputs) != first_key, "compiler source dependency change did not invalidate object key"

    print("remote object cache identity: same-input hit and environment/target/source misses passed")


if __name__ == "__main__":
    main()

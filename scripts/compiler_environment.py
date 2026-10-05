#!/usr/bin/env python3
"""Select and fingerprint environment variables that can affect compiler artifacts."""
import argparse
import hashlib
import json
import os


COMPILER_ENV_NAMES = {
    "PATH", "HOME", "TMPDIR", "LLVM_CONFIG", "ELISA_LLVM_BIN_DIR", "ELISA_CLANG", "ELISA_AR",
    "ELISACORE_BIN", "ELISA_STAGE1_BIN", "ELISA_STAGE1_SELF", "ELISA_RUNTIME_OBJ",
    "PYTHON_BIN", "PYTHON_CONFIG", "CC", "CXX", "CPP", "AR", "AS", "LD", "NM", "RANLIB",
    "COMPILER_PATH", "GCC_EXEC_PREFIX", "SDKROOT", "DEVELOPER_DIR", "TOOLCHAINS",
    "MACOSX_DEPLOYMENT_TARGET", "IPHONEOS_DEPLOYMENT_TARGET", "TVOS_DEPLOYMENT_TARGET",
    "WATCHOS_DEPLOYMENT_TARGET", "XROS_DEPLOYMENT_TARGET", "CFLAGS", "CPPFLAGS", "CXXFLAGS",
    "OBJCFLAGS", "OBJCXXFLAGS", "LDFLAGS", "LIBRARY_PATH", "CPATH", "C_INCLUDE_PATH",
    "CPLUS_INCLUDE_PATH", "OBJC_INCLUDE_PATH", "INCLUDE", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH",
    "SOURCE_DATE_EPOCH", "ZERO_AR_DATE", "CROSS_COMPILE", "TARGET", "TARGET_TRIPLE", "LANG", "LC_ALL",
}
NON_SEMANTIC_ELISA_ENV = {
    "ELISA_STAGE1_MAX_RSS_KB", "ELISA_PROOF_OBJECT_CACHE", "ELISA_PROOF_BUILD_JOBS",
    "ELISA_PROOF_JOBS", "ELISA_PROOF_HEAVY_JOBS", "ELISA_PROOF_REPORT_CACHE",
    "ELISA_PROOF_SHARDS", "ELISA_PROOF_PREFETCH_PHASE", "ELISA_OPT_LEVEL",
    "ELISA_PROOF_OUTPUT", "ELISA_PROOF_PRODUCTS", "ELISA_PROOF_MAIN",
    "ELISA_PROFILE_HOOKS_OBJ", "ELISA_PROFILE_HOOKS_SOURCE", "ELISA_EXTRA_LINK_INPUTS",
    "ELISA_REMOTE_HOST", "ELISA_REMOTE_PORT", "ELISA_REMOTE_WORK",
}
PARALLELISM_ENV_NAMES = {
    "MAKEFLAGS", "MFLAGS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS",
}


def select_compiler_environment(environment):
    """Keep toolchain/SDK inputs and semantic Elisa settings; discard worker state and limits."""
    selected = {}
    for name, value in environment.items():
        if name.startswith("CODEX_") or name in PARALLELISM_ENV_NAMES or name in NON_SEMANTIC_ELISA_ENV:
            continue
        if name in COMPILER_ENV_NAMES or name.startswith(("ELISA_", "LD_", "DYLD_", "LC_", "LLVM_", "CLANG_")):
            selected[name] = value
    return selected


def environment_digest(environment):
    payload = json.dumps(select_compiler_environment(environment), sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--digest", action="store_true", help="print the selected environment digest")
    parser.parse_args()
    print(environment_digest(os.environ))

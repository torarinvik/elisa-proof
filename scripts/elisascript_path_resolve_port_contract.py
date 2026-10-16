"""Source contracts for non-strict Path.resolve across both ElisaScript engines."""

from pathlib import Path


def check_path_resolve_port_contract(root: Path) -> None:
    script_root = root.parent / "elisa-script"
    read = lambda relative: (script_root / relative).read_text(encoding="utf-8")
    interpreter = read("src/ir/interpret.elisa")
    verifier = read("src/ir/ir_verify.elisa")
    registry = read("vendor/elisa-compiler/src/semantic/builtin_registry.elisa")
    bytecode_engine = read("src/bytecode/bytecode.elisa")
    bytecode_fallback = read("src/bytecode/bytecode_fallback.elisa")
    runner = read("src/ir/runner.elisa")
    execution = read("src/ir/execution.elisa")
    execution_program = read("src/ir/execution_program.elisa")
    program_runner = read("src/ir/runner_program.elisa")
    run_only_launcher = read("src/driver/elisascript_run_only.elisa")

    resolver = (root / "scripts/test_report_output_loop_layout.elisascript").read_text(encoding="utf-8")
    resolver_body = resolver.split("def proof_report_output_loop_layout_resolve_script_file(", 1)[1].split("\n\ndef main(", 1)[0]
    assert "script_invocation.resolve()" in resolver_body
    assert "return (false, script_invocation)" in resolver_body
    assert "path_real(" not in resolver_body
    resolve_row = next(line for line in registry.splitlines() if 'name: "resolve"' in line and 'receiver: "Path"' in line)
    assert 'opcode: "PathReal"' in resolve_row and "lowering_mode: 1" in resolve_row
    assert "mode == 1" in interpreter and "evaluate_path_resolve_non_strict" in interpreter
    assert "instruction.integer != 0 and instruction.integer != 1" in verifier
    assert "path_real_value(path_value.text, instruction.integer)" in bytecode_engine
    assert "EsBoundedText::read_utf8_path_text(path_value.text, maximum_bytes)" in interpreter
    assert "EsBoundedText::read_utf8(path(path_value.text), maximum_bytes)" not in interpreter
    non_strict_resolver = interpreter.split("def evaluate_path_resolve_non_strict(", 1)[1].split("def evaluate_path_real(", 1)[0]
    memo_reentry = non_strict_resolver.split("if memo_found:", 1)[1].split("if memos.count >=", 1)[0]
    assert "if not memos[existing_memo].resolved:" in memo_reentry
    expected_loop_fallback = (
        "if not memos[existing_memo].resolved:\n"
        "                        set_loop_fallback: bool = false\n"
        "                        can Global.Read, Global.Write:\n"
        "                            set_loop_fallback <- path_resolve_set(canonical, candidate_view)\n"
        "                        if not set_loop_fallback:\n"
        "                            interpret_set_failure(machine, InterpretFailure.FileIo)\n"
        "                            return runtime_void()\n"
        "                        root_length <- path_resolve_root_length(candidate_view)\n"
        "                        continue"
    )
    assert expected_loop_fallback in memo_reentry
    assert "Python 3.13+ Path.resolve(strict=False)" in memo_reentry
    readlink_failure = non_strict_resolver.split("if target_count < 0:", 1)[1].split("if target_count.usize() >=", 1)[0]
    assert "memos[memo_index].resolved_path <- memos[memo_index].link_path" in readlink_failure
    assert "memos[memo_index].resolved <- true" in readlink_failure

    assert 'include "../ir/execution_program.elisa"' in run_only_launcher
    assert "EsIr::execute_elisascript_program_file_diagnostic(filename, arguments, diagnostic)" in run_only_launcher
    assert 'include "./runner_program.elisa"' in execution_program
    assert 'include "../runtime/bounded_text_posix.elisa"' in execution_program
    assert 'include "./runner_tests.elisa"' not in execution_program
    assert 'include "./runner_cli.elisa"' not in execution_program
    assert 'include "./runner_tests.elisa"' not in program_runner
    assert 'include "./runner_cli.elisa"' not in program_runner
    assert "using EsScriptTest" not in program_runner and "using EsCli" not in program_runner
    assert 'include "./runner.elisa"' in execution
    assert 'include "./runner_program.elisa"' in runner
    assert 'include "./runner_tests.elisa"' in runner and 'include "./runner_cli.elisa"' in runner
    assert "execute_bytecode_with_resource_policy(lowered.module" in program_runner

    direct_support = bytecode_engine.split("def bytecode_direct_supported(", 1)[1].split("def bytecode_capability_report(", 1)[0]
    assert "return false if instruction.opcode == Opcode.ReadBoundedText" not in direct_support
    assert "Opcode.ReadBoundedText" in direct_support
    direct_reader = bytecode_engine.split("def bytecode_direct_read_bounded_text(", 1)[1].split("# Evaluate the closed scalar", 1)[0]
    assert "path_value.kind != RuntimeValueKind.Text or maximum_value.kind != RuntimeValueKind.Int" in direct_reader
    assert "maximum_value.integer < 0" in direct_reader
    assert "maximum_bytes.i64() != maximum_value.integer" in direct_reader
    assert "EsBoundedText::read_utf8_path_text(path_value.text, maximum_bytes)" in direct_reader
    assert "raise InterpretError.FileIo" in direct_reader
    assert "bytecode_direct_read_bounded_text(path_value, bounded_limit)" in bytecode_engine
    fallback = bytecode_fallback.split("def execute_bytecode_with_process_replacement_authorization(", 1)[1].split("def execute_bytecode(", 1)[0]
    assert "if capability.direct_supported:" in fallback
    assert "interpret_with_resource_policy(ir_module" in fallback
    assert "fallback.engine <- ExecutionEngine.BytecodeInterpreterFallback" in fallback

    def elisa_function(source: str, name: str) -> str:
        start = source.index(f"def {name}(")
        end = source.find("\n\n@test", start)
        return source[start:] if end < 0 else source[start:end]

    lowering_tests = read("test/ir/elisascript_lowering_test.elisa")
    ir_tests = read("test/ir/elisascript_ir_test.elisa")
    interpreter_tests = read("test/ir/elisascript_interpreter_test.elisa")
    bytecode_tests = read("test/ir/elisascript_bytecode_test.elisa")
    lowering_real_paths = elisa_function(lowering_tests, "lowers_typed_real_paths_with_file_read_effect_and_error")
    assert "instruction_pool[0].integer == 0" in lowering_real_paths
    assert "functions[3].instruction_pool[0].integer == 1" in lowering_real_paths
    ir_contract = elisa_function(ir_tests, "verifier_accepts_and_rejects_typed_real_path_contract")
    assert "integer: 1" in ir_contract and "integer: 2" in ir_contract
    assert "bad_mode_issues, IssueKind.InvalidInstruction) == 1" in ir_contract
    interpreter_edges = elisa_function(interpreter_tests, "interpreter_resolves_missing_components_and_dangling_symlinks_non_strictly")
    for fragment in ('\\"absent/../leaf\\"', '\\"dangling-link\\"', '\\"../leaf\\"', ".resolve()"):
        assert fragment in interpreter_edges, fragment
    interpreter_loop = elisa_function(interpreter_tests, "interpreter_resolves_non_strict_realpath_symlink_loops")
    for fragment in (
        '\\"self-loop\\"',
        "self_resolved == self_link",
        '\\"self-loop/../leaf\\"',
        "self_after_parent == self_after_parent_expected",
        '\\"cycle-a\\"',
        '\\"cycle-b\\"',
        "cycle_a_resolved == cycle_a",
        "cycle_b_resolved == cycle_b",
    ):
        assert fragment in interpreter_loop, fragment
    assert '\\"loop-error\\"' not in interpreter_loop
    bytecode_edges = elisa_function(bytecode_tests, "bytecode_direct_real_paths_match_reference_interpreter")
    for fragment in ('\\"absent/../leaf\\"', '\\"dangling-link\\"', '\\"../leaf\\"', ".resolve()", "execute_bytecode(lowered.module"):
        assert fragment in bytecode_edges, fragment
    for fragment in (
        '\\"self-loop\\"',
        "loop_result == loop_link",
        '\\"self-loop/../leaf\\"',
        "loop_after_parent == loop_after_parent_expected",
        '\\"cycle-a\\"',
        '\\"cycle-b\\"',
        "cycle_a_result == cycle_a",
        "cycle_b_result == cycle_b",
    ):
        assert fragment in bytecode_edges, fragment
    assert '\\"loop-error\\"' not in bytecode_edges
    invocation_resolve = elisa_function(
        bytecode_tests, "bytecode_direct_resolves_script_invocation_symlink_like_reference_interpreter"
    )
    for fragment in (
        "launch: Path = Script::invocation_path()",
        "launch.resolve() == expected_target",
        "launch == expected_launch",
        "symlink(target, launch)",
        'interpret_with_resource_policy(module, "main"',
        'execute_bytecode(lowered.module, "main"',
        "direct.value.boolean == reference.value.boolean",
    ):
        assert fragment in invocation_resolve, fragment

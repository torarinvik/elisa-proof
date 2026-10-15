"""Keep branch-local runtime alias indexing bounded and fail-closed."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/proof/check/source_runtime_alias_index.elisa").read_text(encoding="utf-8")


def function_body(source: str, name: str) -> str:
    lines = source.splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            body = []
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            return "\n".join(body)
    raise AssertionError(f"missing function {name}")

index_build = source.split("def proof_source_runtime_alias_index_build(", 1)[1].split(
    "def proof_source_runtime_alias_lookup(", 1
)[0]
lookup = source.split("def proof_source_runtime_alias_lookup(", 1)[1].split(
    "def proof_source_runtime_alias_index_insert(", 1
)[0]
insert = source.split("def proof_source_runtime_alias_index_insert(", 1)[1].split(
    "# The parser rewrites", 1
)[0]
add = source.split("def proof_source_runtime_alias_add(", 1)[1].split(
    "def proof_source_runtime_alias_set_from_names(", 1
)[0]
clone = source.split("def proof_source_runtime_alias_set_clone_with_work(", 1)[1]
statements = (ROOT / "src/proof/check/source_runtime_statements.elisa").read_text(encoding="utf-8")
runtime_index = (ROOT / "src/proof/check/source_runtime_index.elisa").read_text(encoding="utf-8")
condition_aliases = (ROOT / "src/proof/check/source_condition_aliases.elisa").read_text(encoding="utf-8")

assert "PROOF_SOURCE_RUNTIME_ALIAS_INDEX_EMPTY: usize = PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT + 1" in source
assert "aliases.indexed <- false" in index_build and "aliases.valid <- false" in index_build
assert "not proof_source_index_work_charge(report, capacity)" in index_build
assert "not proof_source_index_work_charge(report, count)" in index_build
assert "probes <= PROOF_NAME_INDEX_MAX_CLUSTER" in index_build
assert "current == PROOF_SOURCE_RUNTIME_ALIAS_INDEX_EMPTY" in index_build
assert "return false if current >= count" in index_build
assert "aliases.indexed <- true" in index_build and "aliases.valid <- true" in index_build

assert "not aliases.valid" in lookup
assert "aliases.names.count >= PROOF_SOURCE_RUNTIME_ALIAS_INDEX_THRESHOLD" in lookup
assert "current == PROOF_SOURCE_RUNTIME_ALIAS_INDEX_EMPTY" in lookup
assert "current >= count" in lookup
assert "probes <= PROOF_NAME_INDEX_MAX_CLUSTER" in lookup
assert "current_name == name" in lookup  # Hashes only select candidates; text equality decides.

assert "row >= aliases.names.count" in insert
assert "current >= row" in insert  # Occupied slots must refer to an earlier insertion.
assert "current_name == name" in insert
assert "probes <= PROOF_NAME_INDEX_MAX_CLUSTER" in insert

assert "aliases.valid <- false" in add
assert "aliases.names.push(name)" in add
assert "proof_source_runtime_alias_index_build(aliases, report)" in add
assert "proof_source_runtime_alias_index_insert(aliases, aliases.names.count - 1, report)" in add
assert "aliases.valid <- true" in add

assert "proof_source_runtime_alias_set_empty()" in clone
assert "not source.valid" in clone
assert "for name in source.names" in clone
assert "not proof_source_index_work_charge(report, 1)" in clone
assert "proof_source_runtime_alias_add(&aliases, name, report)" in clone
assert "aliases.names <- source.names" not in clone
assert "aliases.hashes <- source.hashes" not in clone
assert "aliases.values <- source.values" not in clone
assert "detached_statement_aliases" in statements
assert "detached_block_aliases" in statements
assert "detached_body_aliases" in statements
assert statements.count("proof_source_runtime_alias_set_clone_with_work(") == 3
statement_walk_source = function_body(
    statements, "proof_source_statements_have_unsafe_runtime_index_with_set"
)
assert statement_walk_source.index(
    "proof_source_runtime_alias_set_clone_with_work(aliases, report)"
) < statement_walk_source.index("for statement in statements")
block_scope = statement_walk_source.split("Ast::Stmt.Block", 1)[1].split(
    "Ast::Stmt.VarDecl", 1
)[0]
loop_scope = statement_walk_source.split("Ast::Stmt.For", 1)[1].split(
    "Ast::Stmt.Match", 1
)[0]
if_scope = statement_walk_source.split("Ast::Stmt.If", 1)[1].split(
    "Ast::Stmt.While", 1
)[0]
while_scope = statement_walk_source.split("Ast::Stmt.While", 1)[1].split(
    "Ast::Stmt.For", 1
)[0]
match_scope = statement_walk_source.split("Ast::Stmt.Match", 1)[1].split(
    "Ast::Stmt.Contract", 1
)[0]
assert block_scope.index(
    "proof_source_runtime_alias_set_clone_with_work(statement_aliases, report)"
) < block_scope.index("proof_source_runtime_alias_add(&block_aliases")
assert loop_scope.index(
    "proof_source_runtime_alias_set_clone_with_work(statement_aliases, report)"
) < loop_scope.index("for variable in variables |body_aliases")
assert "proof_source_condition_alias_paths(condition, statement_aliases, report, 0)" in if_scope
assert "condition_aliases.true_aliases" in if_scope
assert "condition_aliases.false_aliases" in if_scope
assert "proof_source_condition_true_aliases_with_set(condition, statement_aliases, report)" in while_scope
assert "body_aliases.aliases" in while_scope
assert "proof_source_statements_have_unsafe_runtime_index_with_set(arm.body" in match_scope
assert "statement_aliases, declaration_line, caller_owner, caller_owner_known" in match_scope

# Recursive hot paths must keep the indexed set instead of rebuilding a table from
# ordered-name adapters at each AST node. Array-based functions are API boundaries only.
condition_paths = function_body(condition_aliases, "proof_source_condition_alias_paths")
expression_walk = function_body(runtime_index, "proof_source_expression_has_unsafe_runtime_index_with_set")
statement_walk = function_body(statements, "proof_source_statements_have_unsafe_runtime_index_with_set")
for recursive_walk in (condition_paths, expression_walk, statement_walk):
    assert "proof_source_expression_has_unsafe_runtime_index(" not in recursive_walk
    assert "proof_source_statements_have_unsafe_runtime_index(" not in recursive_walk
    assert "proof_source_condition_true_aliases(" not in recursive_walk
    assert "proof_source_condition_false_aliases(" not in recursive_walk

print("runtime alias index: bounded probes, collision-safe equality, detached scope copies")

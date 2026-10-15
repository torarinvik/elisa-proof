"""Keep duplicate parser lemma markers out of source theorem admission."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/proof/model/report_theorem_source_admission.elisa").read_text(encoding="utf-8")


def body(name: str) -> str:
    lines = SOURCE.splitlines()
    start = next(i for i, line in enumerate(lines) if re.match(rf"\s*def {re.escape(name)}\b", line))
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].strip() and len(lines[i]) - len(lines[i].lstrip()) <= indent), len(lines))
    return "\n".join(lines[start + 1:end])


index = body("proof_report_source_lemma_name_multiplicity_index")
for evidence in (
    "source.file.enum_annotations", 'annotation.owner == "__lemma"',
    "declarations > PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT / 4",
    "proof_report_declaration_name_hash(annotation.name, work)",
    "index.names[current] == annotation.name", "index.counts[current] <- index.counts[current] + 1",
    "probes > PROOF_NAME_INDEX_MAX_CLUSTER", "proof_report_source_work_charge",
):
    assert evidence in index, evidence

unique = body("proof_report_declaration_name_is_unique")
assert "index.counts[current] == 1" in unique
inventory = body("proof_report_source_lemma_inventory_matches_with_work")
inventory_signature = SOURCE.split("def proof_report_source_lemma_inventory_matches_with_work", 1)[1].split("\n", 1)[0]
assert "lemma_names: ProofDeclarationNameMultiplicityIndex" in inventory_signature
assert inventory.index("continue if not unique_name") < inventory.index("summary_index >= report.analysis_1.theorems.summaries.count")

snapshot = body("proof_report_theorem_source_status_snapshot")
assert snapshot.index("proof_report_source_lemma_name_multiplicity_index(source, source_work)") < snapshot.index(
    "proof_report_source_lemma_inventory_matches_with_work(source, report, lemma_names, source_work)"
)
assert "summaries.count == 0" in snapshot

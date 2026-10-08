"""Required permission violations refuse all source-bound CLI routes."""
import json
import tempfile
from pathlib import Path
import test_source_admission_matrix as admission

admission.MALFORMED = {'ungranted_panic': b'\ndef f() -> void:\n    panic("boom")\n', 'ungranted_extern_effect_call': b'\nextern emit(value: int) -> void can[Console.Write]\n\ndef caller() -> void:\n    emit(1)\n', 'ungranted_inferred_effect_call': b'\ndef h() -> void:\n    can Abort.Panic:\n        panic("x")\n\ndef caller() -> void:\n    h()\n', 'ungranted_forward_inferred_effect_call': b'\nextern emit(value: int) -> void can[Console.Write]\n\ndef caller() -> void:\n    callee()\n\ndef callee() -> void:\n    emit(1) can Console.Write\n', 'ungranted_effect_call': b'\ndef g() -> void can[Abort.Panic]:\n    can Abort.Panic:\n        panic("x")\n\ndef caller() -> void:\n    g()\n'}
admission.main()
positive = (b'def f() -> void:\n    can Abort.Panic:\n        panic("boom")\n', b'extern emit(value: int) -> void can[Console.Write]\ndef caller() -> void:\n    can Console.Write:\n        emit(1)\n', b'def h() -> void:\n    can Abort.Panic:\n        panic("x")\ndef caller() -> void:\n    can Abort.Panic:\n        h()\n', b'extern emit(value: int) -> void can[Console.Write]\ndef caller() -> void:\n    can Console.Write:\n        callee()\ndef callee() -> void:\n    can Console.Write:\n        emit(1)\n')
with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    for index, fragment in enumerate(positive):
        source = directory / ("granted-" + str(index) + ".elisa")
        source.write_bytes(admission.BASE + b"\n" + fragment)
        proof = directory / "granted.proof"
        proof.write_bytes(admission.run("--proof", admission.GOAL, source).stdout)
        repair = json.loads(admission.run("--repair", admission.GOAL, source).stdout)
        (directory / "control.script").write_text(repair["script"])
        for name, arguments in admission.routes(directory, source, proof):
            result = admission.run(*arguments)
            assert result.returncode == 0, (index, name, result.stdout[:300])
print("Required permission CLI admission: five violation forms refuse all routes; four granted controls remain admitted")

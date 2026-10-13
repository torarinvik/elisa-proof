"""Keep report, theorem, package, and focused collision checks together."""
import json


def check_pattern_collision_reports(run, binary, path, collisions, theorem_names):
    report_run = run([binary, '--json', str(path)], 'pattern collision report')
    report = json.loads(report_run.stdout)
    assert report_run.returncode == 1 and report['status'] == 'failed', (
        report_run.returncode, report.get('status'), report.get('findings'))
    assert report['source']['admissible'] is True, report['source']
    assert report['summary']['semantic_errors'] == 0, report['semantic_diagnostics']
    assert report['replay']['gaps'] == 0, report['replay']
    assert report['replay']['certificates'] == report['replay']['replayed'], report['replay']
    assert not report['trust']['trusted_assumptions'], report['trust']
    for name in collisions:
        function = next((row for row in report['functions'] if row['name'] == name), None)
        assert function is not None and not function['proved'], (name, report['functions'])
        assert any(goal['name'] == name and not goal['proven'] for goal in report['goals']), (
            name, report['goals'])
        assert any(finding['name'] == name and finding['kind'] == 'ensure-unproven'
                   for finding in report['findings']), (name, report['findings'])

    # The theorem and package APIs must preserve the same unproved collision status.
    theorem_run = run([binary, '--theorems', str(path)], 'pattern collision theorem output')
    theorem_report = json.loads(theorem_run.stdout)
    assert theorem_report['source']['admissible'] is True, theorem_report['source']
    assert theorem_report['source']['goal_admissions_complete'] is True, theorem_report['source']
    for theorem_name in theorem_names:
        theorem = next((row for row in theorem_report['theorems']
                        if row['name'] == theorem_name), None)
        assert theorem is not None, theorem_report['theorems']
        assert theorem['verified'] is False and theorem['kernel_verified'] is False, theorem
        assert theorem['proof_goals'] and not any(goal['proven'] for goal in theorem['proof_goals']), theorem
        assert theorem['proof_goals_valid'] and theorem['source_claim_admissible'], theorem
        assert all(goal['source_admission'] == 'admitted' for goal in theorem['proof_goals']), theorem
    for theorem in theorem_report['theorems']:
        if theorem['name'] in collisions or theorem['name'] in theorem_names:
            assert theorem['verified'] is False, theorem
            assert not any(goal['proven'] for goal in theorem['proof_goals']), theorem

    package_run = run([binary, '--package', str(path)], 'pattern collision package output')
    package_report = json.loads(package_run.stdout)
    assert package_report['source']['admissible'] is True, package_report['source']
    assert package_report['source']['goal_status_snapshot_complete'] is True, package_report['source']
    assert not any(theorem['name'] in collisions or theorem['name'] in theorem_names
                   for theorem in package_report['theorems']), package_report['theorems']

    for name in collisions:
        focused = run([binary, '--function-json', name, str(path)],
                      f'focused pattern collision {name}')
        focused_report = json.loads(focused.stdout)
        assert focused.returncode == 1 and focused_report['status'] == 'failed', (
            name, focused.returncode, focused_report.get('status'))
        assert focused_report['source']['admissible'] is True, (name, focused_report['source'])
        assert focused_report['summary']['semantic_errors'] == 0, (
            name, focused_report.get('semantic_diagnostics'))
        assert focused_report['replay']['gaps'] == 0, (name, focused_report['replay'])
        assert focused_report['replay']['certificates'] == focused_report['replay']['replayed'], (
            name, focused_report['replay'])
        assert not focused_report['trust']['trusted_assumptions'], (
            name, focused_report['trust'])
        declaration = next((row for row in focused_report['declaration_details']
                            if row.get('kind') == 'function' and row.get('name') == name), None)
        assert declaration is not None and not declaration['verified'], (
            name, focused_report['declaration_details'])
        assert any(goal['name'] == name and not goal['proven']
                   for goal in focused_report['goals']), (name, focused_report['goals'])

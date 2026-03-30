"""autospec evaluator — 빌드 실행 및 테스트 결과 파싱"""

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_test_results(test_results_dir: str) -> dict:
    """JUnit XML 리포트를 파싱하여 테스트 결과를 반환한다."""
    total = 0
    failed = 0

    results_path = Path(test_results_dir)
    for xml_file in results_path.glob("TEST-*.xml"):
        tree = ET.parse(xml_file)
        root = tree.getroot()
        tests = int(root.attrib.get("tests", 0))
        failures = int(root.attrib.get("failures", 0))
        errors = int(root.attrib.get("errors", 0))
        skipped = int(root.attrib.get("skipped", 0))
        total += tests - skipped
        failed += failures + errors

    return {
        "test_total": total,
        "test_passed": total - failed,
        "test_failed": failed,
    }


def run_build(project_root: str) -> bool:
    """./gradlew build를 실행하고 성공 여부를 반환한다."""
    result = subprocess.run(
        ["./gradlew", "build"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return result.returncode == 0


def evaluate(project_root: str, previous_test_total: int) -> dict:
    """빌드 실행 후 평가 결과를 반환한다."""
    build_success = run_build(project_root)

    test_results_dir = str(Path(project_root) / "build" / "test-results" / "test")
    test_results = parse_test_results(test_results_dir)

    test_diff = test_results["test_total"] - previous_test_total

    return {
        "build_success": build_success,
        **test_results,
        "test_diff": test_diff,
    }


def judge(evaluation: dict) -> str:
    """평가 결과를 기반으로 accept/reject 판정한다."""
    if not evaluation["build_success"]:
        return "reject"
    if evaluation["test_failed"] > 0:
        return "reject"
    if evaluation["test_diff"] < 0:
        return "reject"
    return "accept"

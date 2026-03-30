"""autospec history — 사이클 실행 기록 관리"""

from pathlib import Path


def write_run(
    runs_dir: str,
    cycle: int,
    verdict: str,
    evaluation: dict,
    commit_message: str,
    changed_files: list[str],
    duration_seconds: float = 0,
    lines_added: int = 0,
    lines_deleted: int = 0,
) -> Path:
    """사이클 실행 결과를 runs/run-{NNN}.md에 기록한다."""
    runs_path = Path(runs_dir)
    runs_path.mkdir(parents=True, exist_ok=True)

    run_file = runs_path / f"run-{cycle:03d}.md"

    test_total = evaluation["test_total"]
    test_passed = evaluation["test_passed"]
    test_diff = evaluation["test_diff"]
    build_status = "성공" if evaluation["build_success"] else "실패"
    diff_str = f"+{test_diff}" if test_diff >= 0 else str(test_diff)
    files_str = ", ".join(changed_files) if changed_files else "없음"
    duration_str = f"{int(duration_seconds)}초" if duration_seconds > 0 else "N/A"

    content = f"""# Run {cycle:03d}
- 사이클: {cycle}
- 판정: {verdict}
- 빌드: {build_status}
- 테스트: {test_passed}/{test_total} (이전 대비 {diff_str})
- 소요 시간: {duration_str}
- 코드 변경: +{lines_added}/-{lines_deleted} lines
- AI 커밋 메시지: "{commit_message}"
- 변경 파일: {files_str}
"""
    run_file.write_text(content)
    return run_file


def read_runs(runs_dir: str) -> list[str]:
    """runs/ 디렉토리의 모든 run 기록을 순서대로 읽는다."""
    runs_path = Path(runs_dir)
    if not runs_path.exists():
        return []

    run_files = sorted(runs_path.glob("run-*.md"))
    return [f.read_text() for f in run_files]


def summarize_runs(runs: list[str]) -> str:
    """run 기록들을 AI에게 전달할 요약으로 변환한다."""
    if not runs:
        return "이전 사이클 결과: 없음 (첫 사이클)"

    lines = ["이전 사이클 결과:"]
    for run_content in runs:
        run_num = ""
        verdict = ""
        commit = ""
        test_info = ""
        for line in run_content.strip().split("\n"):
            line = line.strip()
            if line.startswith("# Run"):
                run_num = line.replace("# ", "")
            elif line.startswith("- 판정:"):
                verdict = line.split(":")[1].strip()
            elif line.startswith("- AI 커밋 메시지:"):
                commit = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("- 테스트:"):
                test_info = line.split(":", 1)[1].strip()
        lines.append(f"- {run_num}: {commit}, 테스트 {test_info}, {verdict}")

    return "\n".join(lines)

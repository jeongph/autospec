#!/usr/bin/env python3
"""autospec orchestrator — AI 자율 개선 루프

Usage:
    python orchestrator.py <project_dir>

Example:
    python orchestrator.py examples/spring-boot-todo
"""

import subprocess
import sys
import time
from pathlib import Path

from evaluator import evaluate, judge
from history import write_run, read_runs, summarize_runs

MAX_CYCLES = 10
MAX_CONSECUTIVE_FAILURES = 3
MAX_NO_IMPROVEMENT = 2
TIMEOUT_SECONDS = 600


def get_last_commit_message(project_root: Path) -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=str(project_root),
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def get_changed_files_in_last_commit(project_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
        cwd=str(project_root),
        capture_output=True, text=True,
    )
    return [f for f in result.stdout.strip().split("\n") if f]


def get_lines_changed(project_root: Path) -> tuple[int, int]:
    result = subprocess.run(
        ["git", "diff", "--numstat", "HEAD~1", "HEAD"],
        cwd=str(project_root),
        capture_output=True, text=True,
    )
    added = 0
    deleted = 0
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if parts[0] != "-":
            added += int(parts[0])
        if parts[1] != "-":
            deleted += int(parts[1])
    return added, deleted


def get_head_sha(project_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(project_root),
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def rollback(project_root: Path) -> None:
    subprocess.run(
        ["git", "reset", "--hard", "HEAD~1"],
        cwd=str(project_root),
        capture_output=True,
    )


def build_prompt(program_md: str, previous_summary: str) -> str:
    return f"""{program_md}

---

{previous_summary}

주의:
- 이전 사이클에서 이미 수행한 작업은 반복하지 마라
- 아직 해결되지 않은 간극을 찾아서 해결하라
- 작업이 끝나면 반드시 커밋하라
- 커밋 메시지는 한글로 작성하라
"""


def run_cycle(project_root: Path, prompt: str) -> bool:
    sha_before = get_head_sha(project_root)

    try:
        subprocess.run(
            ["claude", "-p", prompt, "--allowedTools",
             "Edit,Write,Bash,Read,Glob,Grep"],
            cwd=str(project_root),
            capture_output=True, text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        print("  AI 타임아웃 (10분 초과)")
        return False

    sha_after = get_head_sha(project_root)
    return sha_before != sha_after


def main():
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <project_dir>")
        print("Example: python orchestrator.py examples/spring-boot-todo")
        sys.exit(1)

    project_root = Path(sys.argv[1]).resolve()
    autospec_dir = project_root / ".autospec"

    if not autospec_dir.exists():
        print(f"Error: {autospec_dir} not found")
        sys.exit(1)

    runs_dir = str(autospec_dir / "runs")
    program_md = (autospec_dir / "program.md").read_text()

    print("autospec orchestrator v0.1")
    print(f"프로젝트: {project_root}")
    print(f"최대 사이클: {MAX_CYCLES}")
    print()

    consecutive_failures = 0
    no_improvement_count = 0
    previous_test_total = 0

    initial_eval = evaluate(str(project_root), 0)
    if initial_eval["build_success"]:
        previous_test_total = initial_eval["test_total"]
        print(f"초기 상태: 빌드 성공, 테스트 {previous_test_total}개")
    else:
        print("초기 빌드 실패. 종료.")
        sys.exit(1)
    print()

    for cycle in range(1, MAX_CYCLES + 1):
        print(f"[사이클 {cycle}/{MAX_CYCLES}]")

        runs = read_runs(runs_dir)
        summary = summarize_runs(runs)

        prompt = build_prompt(program_md, summary)
        print("  AI 실행 중... (timeout: 10분)")
        cycle_start = time.time()
        has_new_commit = run_cycle(project_root, prompt)
        cycle_duration = time.time() - cycle_start

        if not has_new_commit:
            print("  AI 완료: 커밋 없음 (변경 사항 없음)")
            no_improvement_count += 1
            if no_improvement_count >= MAX_NO_IMPROVEMENT:
                print(f"  수렴: 연속 {MAX_NO_IMPROVEMENT}회 개선 없음")
                break
            print(f"  개선 없음 ({no_improvement_count}/{MAX_NO_IMPROVEMENT})")
            write_run(runs_dir, cycle, "no_change",
                      {"build_success": True, "test_total": previous_test_total,
                       "test_passed": previous_test_total, "test_failed": 0, "test_diff": 0},
                      "(변경 없음)", [], duration_seconds=cycle_duration, lines_added=0, lines_deleted=0)
            print()
            continue

        commit_msg = get_last_commit_message(project_root)
        changed_files = get_changed_files_in_last_commit(project_root)
        lines_added, lines_deleted = get_lines_changed(project_root)
        print(f'  AI 완료: 커밋 발견 "{commit_msg}"')

        evaluation = evaluate(str(project_root), previous_test_total)
        verdict = judge(evaluation)
        test_str = f"{evaluation['test_passed']}/{evaluation['test_total']}"
        diff_str = f"+{evaluation['test_diff']}" if evaluation['test_diff'] >= 0 else str(evaluation['test_diff'])
        print(f"  평가: {'빌드 성공' if evaluation['build_success'] else '빌드 실패'}, 테스트 {test_str} ({diff_str}), {cycle_duration:.0f}초")

        if verdict == "reject":
            print("  판정: reject ✗ → 롤백")
            rollback(project_root)
            consecutive_failures += 1
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(f"  중단: 연속 {MAX_CONSECUTIVE_FAILURES}회 실패")
                break
        else:
            print("  판정: accept ✓")
            consecutive_failures = 0
            if evaluation["test_diff"] == 0:
                no_improvement_count += 1
                if no_improvement_count >= MAX_NO_IMPROVEMENT:
                    print(f"  수렴: 연속 {MAX_NO_IMPROVEMENT}회 개선 없음")
                    write_run(runs_dir, cycle, verdict, evaluation, commit_msg, changed_files,
                              duration_seconds=cycle_duration, lines_added=lines_added, lines_deleted=lines_deleted)
                    break
                print(f"  개선 없음 ({no_improvement_count}/{MAX_NO_IMPROVEMENT})")
            else:
                no_improvement_count = 0
            previous_test_total = evaluation["test_total"]

        write_run(runs_dir, cycle, verdict, evaluation, commit_msg, changed_files,
                  duration_seconds=cycle_duration, lines_added=lines_added, lines_deleted=lines_deleted)
        print()

    print()
    final_runs = read_runs(runs_dir)
    accept_count = sum(1 for r in final_runs if "판정: accept" in r)
    reject_count = sum(1 for r in final_runs if "판정: reject" in r)
    print(f"완료: {len(final_runs)} 사이클, {accept_count} accept, {reject_count} reject")
    print(f"최종 테스트: {previous_test_total}개")


if __name__ == "__main__":
    main()

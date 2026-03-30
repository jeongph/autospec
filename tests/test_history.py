import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from history import write_run, read_runs, summarize_runs

def test_write_run_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        runs_dir = Path(tmpdir) / "runs"
        write_run(
            runs_dir=str(runs_dir),
            cycle=1,
            verdict="accept",
            evaluation={"build_success": True, "test_total": 25, "test_passed": 25, "test_failed": 0, "test_diff": 3},
            commit_message="feat: 금액 검증 추가",
            changed_files=["TodoService.java", "TodoServiceTest.java"],
        )
        run_file = runs_dir / "run-001.md"
        assert run_file.exists()
        content = run_file.read_text()
        assert "사이클: 1" in content
        assert "accept" in content
        assert "25/25" in content
        assert "금액 검증 추가" in content

def test_write_run_sequential_numbering():
    with tempfile.TemporaryDirectory() as tmpdir:
        runs_dir = Path(tmpdir) / "runs"
        write_run(runs_dir=str(runs_dir), cycle=1, verdict="accept",
                  evaluation={"build_success": True, "test_total": 10, "test_passed": 10, "test_failed": 0, "test_diff": 2},
                  commit_message="feat: a", changed_files=["A.java"])
        write_run(runs_dir=str(runs_dir), cycle=2, verdict="reject",
                  evaluation={"build_success": False, "test_total": 10, "test_passed": 8, "test_failed": 2, "test_diff": 0},
                  commit_message="fix: b", changed_files=["B.java"])
        assert (runs_dir / "run-001.md").exists()
        assert (runs_dir / "run-002.md").exists()

def test_read_runs_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        runs_dir = Path(tmpdir) / "runs"
        runs_dir.mkdir()
        result = read_runs(str(runs_dir))
        assert result == []

def test_read_runs_returns_sorted():
    with tempfile.TemporaryDirectory() as tmpdir:
        runs_dir = Path(tmpdir) / "runs"
        write_run(runs_dir=str(runs_dir), cycle=1, verdict="accept",
                  evaluation={"build_success": True, "test_total": 10, "test_passed": 10, "test_failed": 0, "test_diff": 2},
                  commit_message="feat: a", changed_files=["A.java"])
        write_run(runs_dir=str(runs_dir), cycle=2, verdict="accept",
                  evaluation={"build_success": True, "test_total": 15, "test_passed": 15, "test_failed": 0, "test_diff": 5},
                  commit_message="feat: b", changed_files=["B.java"])
        runs = read_runs(str(runs_dir))
        assert len(runs) == 2
        assert "사이클: 1" in runs[0]
        assert "사이클: 2" in runs[1]

def test_summarize_runs_empty():
    result = summarize_runs([])
    assert result == "이전 사이클 결과: 없음 (첫 사이클)"

def test_summarize_runs_with_data():
    with tempfile.TemporaryDirectory() as tmpdir:
        runs_dir = Path(tmpdir) / "runs"
        write_run(runs_dir=str(runs_dir), cycle=1, verdict="accept",
                  evaluation={"build_success": True, "test_total": 10, "test_passed": 10, "test_failed": 0, "test_diff": 2},
                  commit_message="feat: 금액 검증 추가", changed_files=["A.java"])
        runs = read_runs(str(runs_dir))
        summary = summarize_runs(runs)
        assert "Run 001" in summary
        assert "금액 검증 추가" in summary
        assert "accept" in summary

def test_write_run_includes_duration_and_lines():
    with tempfile.TemporaryDirectory() as tmpdir:
        runs_dir = Path(tmpdir) / "runs"
        write_run(
            runs_dir=str(runs_dir),
            cycle=1,
            verdict="accept",
            evaluation={"build_success": True, "test_total": 25, "test_passed": 25, "test_failed": 0, "test_diff": 3},
            commit_message="feat: CRUD 구현",
            changed_files=["TodoService.java"],
            duration_seconds=245.5,
            lines_added=120,
            lines_deleted=5,
        )
        content = (runs_dir / "run-001.md").read_text()
        assert "245초" in content
        assert "+120/-5 lines" in content

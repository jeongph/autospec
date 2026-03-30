import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluator import parse_test_results, judge

def test_parse_junit_xml_all_pass():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.example.todo.TodoServiceTest" tests="5" skipped="0" failures="0" errors="0" time="1.234">
  <testcase name="test1" classname="com.example.todo.TodoServiceTest" time="0.1"/>
  <testcase name="test2" classname="com.example.todo.TodoServiceTest" time="0.2"/>
  <testcase name="test3" classname="com.example.todo.TodoServiceTest" time="0.1"/>
  <testcase name="test4" classname="com.example.todo.TodoServiceTest" time="0.1"/>
  <testcase name="test5" classname="com.example.todo.TodoServiceTest" time="0.1"/>
</testsuite>"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "TEST-TodoServiceTest.xml"
        path.write_text(xml)
        result = parse_test_results(tmpdir)
        assert result["test_total"] == 5
        assert result["test_passed"] == 5
        assert result["test_failed"] == 0

def test_parse_junit_xml_with_failures():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.example.todo.TodoServiceTest" tests="3" skipped="0" failures="1" errors="0" time="0.5">
  <testcase name="test1" classname="com.example.todo.TodoServiceTest" time="0.1"/>
  <testcase name="test2" classname="com.example.todo.TodoServiceTest" time="0.2">
    <failure message="expected true">assertion failed</failure>
  </testcase>
  <testcase name="test3" classname="com.example.todo.TodoServiceTest" time="0.1"/>
</testsuite>"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "TEST-TodoServiceTest.xml"
        path.write_text(xml)
        result = parse_test_results(tmpdir)
        assert result["test_total"] == 3
        assert result["test_passed"] == 2
        assert result["test_failed"] == 1

def test_parse_multiple_xml_files():
    xml1 = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="Suite1" tests="3" skipped="0" failures="0" errors="0" time="0.3">
  <testcase name="t1" classname="Suite1" time="0.1"/>
  <testcase name="t2" classname="Suite1" time="0.1"/>
  <testcase name="t3" classname="Suite1" time="0.1"/>
</testsuite>"""
    xml2 = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="Suite2" tests="2" skipped="0" failures="0" errors="0" time="0.2">
  <testcase name="t1" classname="Suite2" time="0.1"/>
  <testcase name="t2" classname="Suite2" time="0.1"/>
</testsuite>"""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "TEST-Suite1.xml").write_text(xml1)
        (Path(tmpdir) / "TEST-Suite2.xml").write_text(xml2)
        result = parse_test_results(tmpdir)
        assert result["test_total"] == 5
        assert result["test_passed"] == 5

def test_parse_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = parse_test_results(tmpdir)
        assert result["test_total"] == 0
        assert result["test_passed"] == 0
        assert result["test_failed"] == 0

def test_judge_accept():
    evaluation = {"build_success": True, "test_total": 10, "test_passed": 10, "test_failed": 0, "test_diff": 2}
    assert judge(evaluation) == "accept"

def test_judge_reject_build_failure():
    evaluation = {"build_success": False, "test_total": 10, "test_passed": 10, "test_failed": 0, "test_diff": 0}
    assert judge(evaluation) == "reject"

def test_judge_reject_test_failure():
    evaluation = {"build_success": True, "test_total": 10, "test_passed": 9, "test_failed": 1, "test_diff": 0}
    assert judge(evaluation) == "reject"

def test_judge_reject_test_decrease():
    evaluation = {"build_success": True, "test_total": 8, "test_passed": 8, "test_failed": 0, "test_diff": -2}
    assert judge(evaluation) == "reject"

def test_judge_accept_no_change():
    evaluation = {"build_success": True, "test_total": 10, "test_passed": 10, "test_failed": 0, "test_diff": 0}
    assert judge(evaluation) == "accept"

import sqlite3

from pipeline import quality


def _run(db):
    with sqlite3.connect(db) as conn:
        return quality.run_checks(conn)


def _status(report):
    return {c["id"]: c["status"] for c in report["checks"]}


def test_clean_sample_has_no_failures(sample_db):
    report = _run(sample_db)
    assert report["passed"], [c for c in report["checks"] if c["status"] == "fail"]
    # The synthetic data is single-tier on purpose, mirroring the real scrape.
    assert _status(report)["participants_rank_tier_informative"] == "warn"


def test_two_winners_is_a_failure(sample_db):
    with sqlite3.connect(sample_db) as conn:
        conn.execute("UPDATE teams SET win = 1 WHERE match_id = (SELECT match_id FROM matches LIMIT 1)")
    report = _run(sample_db)
    assert not report["passed"]
    assert _status(report)["teams_one_winner_per_match"] == "fail"


def test_participant_win_must_match_team(sample_db):
    with sqlite3.connect(sample_db) as conn:
        conn.execute("UPDATE participants SET win = 1 - win WHERE participant_id = 1")
    assert _status(_run(sample_db))["participant_win_matches_team"] == "fail"


def test_orphan_participants_are_detected(sample_db):
    with sqlite3.connect(sample_db) as conn:
        conn.execute("DELETE FROM matches WHERE match_id = (SELECT match_id FROM matches LIMIT 1)")
    assert _status(_run(sample_db))["participants_orphans"] == "fail"


def test_missing_detail_is_only_a_warning(sample_db):
    with sqlite3.connect(sample_db) as conn:
        conn.execute("INSERT INTO matches SELECT 'X_1', region, platform_id, region_group, queue_id, "
                     "queue_type, game_version, patch_version, game_creation, game_start_timestamp, "
                     "game_end_timestamp, game_duration, match_date, match_date_simple, duration_mmss "
                     "FROM matches LIMIT 1")
    report = _run(sample_db)
    assert report["passed"]
    assert _status(report)["matches_have_participant_detail"] == "warn"


def test_row_count_regression_detection():
    assert quality.row_count_regressions({"a": 50, "b": 100}, {"a": 100, "b": 100}) == {"a": (100, 50)}
    assert quality.row_count_regressions({"a": 95}, {"a": 100}) == {}
    assert quality.row_count_regressions({"a": 1}, {}) == {}


def test_report_flags_regression_between_runs(sample_db, tmp_path):
    report = _run(sample_db)
    quality.write_report(report, tmp_path)
    shrunk = {**report, "row_counts": {**report["row_counts"], "participants": 1}}
    quality.write_report(shrunk, tmp_path)
    assert shrunk["passed"] is False
    assert "participants" in shrunk["row_count_regressions"]

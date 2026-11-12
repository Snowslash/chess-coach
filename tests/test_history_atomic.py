"""Atomic history faults exercise real files, never a personal coach history."""
import io
import json
import os
from pathlib import Path

import pytest

from chess_coach.cli import main
from chess_coach.history import CoachState, GameHistoryEntry, load_state, save_state


def state_for(name):
    return CoachState(games={name: GameHistoryEntry(key=name, game_id=name)})


def test_save_replaces_complete_json_from_the_same_directory(tmp_path, monkeypatch):
    path = tmp_path / ".coach/state.json"
    path.parent.mkdir()
    previous = state_for("previous")
    path.write_text(previous.model_dump_json(indent=2))
    before = path.read_bytes()
    replacement = state_for("replacement")
    real_replace = os.replace
    published = []

    def observe_replace(source, destination):
        source, destination = Path(source), Path(destination)
        assert source.parent == destination.parent == path.parent
        assert source != destination == path
        assert path.read_bytes() == before
        assert load_state(path) == previous
        assert load_state(source) == replacement
        published.append(source)
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", observe_replace)
    assert save_state(replacement, path) == path
    assert len(published) == 1
    assert load_state(path) == replacement
    assert path.read_text() == replacement.model_dump_json(indent=2)
    assert set(json.loads(path.read_text())) == {"schema_version", "games", "patterns", "runs"}
    assert list(path.parent.iterdir()) == [path]


def test_partial_write_failure_keeps_previous_history_bytes(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    previous = state_for("previous")
    path.write_text(previous.model_dump_json(indent=2))
    before = path.read_bytes()
    real_open = io.open

    class BrokenWriter:
        def __init__(self, file):
            self.file = file

        def __getattr__(self, name):
            return getattr(self.file, name)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.file.__exit__(*args)

        def write(self, text):
            self.file.write(text[:20])
            self.file.flush()
            raise OSError("injected partial write failure")

    def fail_writes(file, mode="r", *args, **kwargs):
        opened = real_open(file, mode, *args, **kwargs)
        return BrokenWriter(opened) if "w" in mode else opened

    monkeypatch.setattr(io, "open", fail_writes)
    with pytest.raises(OSError, match="injected partial write failure"):
        save_state(state_for("replacement"), path)
    assert path.read_bytes() == before
    assert load_state(path) == previous
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("existing", [True, False], ids=["previous-history", "first-save"])
@pytest.mark.parametrize("failure", ["fsync", "replace"])
def test_prepublication_failures_are_visible_and_clean_up(tmp_path, monkeypatch, failure, existing):
    path = tmp_path / "state.json"
    previous = state_for("previous")
    if existing:
        path.write_text(previous.model_dump_json(indent=2))
    before = path.read_bytes() if existing else None

    def fail(*_args):
        if existing:
            assert path.read_bytes() == before
            assert load_state(path) == previous
        else:
            assert not path.exists()
        raise OSError(f"injected {failure} failure")

    monkeypatch.setattr(os, failure, fail)
    with pytest.raises(OSError, match=f"injected {failure} failure"):
        save_state(state_for("replacement"), path)
    assert (path.read_bytes() if path.exists() else None) == before
    assert list(tmp_path.iterdir()) == ([path] if existing else [])


def test_serialization_failure_does_not_touch_previous_history(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    previous = state_for("previous")
    path.write_text(previous.model_dump_json(indent=2))
    before = path.read_bytes()

    def fail(*_args, **_kwargs):
        raise ValueError("injected serialization failure")

    monkeypatch.setattr(CoachState, "model_dump_json", fail)
    with pytest.raises(ValueError, match="injected serialization failure"):
        save_state(state_for("replacement"), path)
    assert path.read_bytes() == before
    assert load_state(path) == previous
    assert list(tmp_path.iterdir()) == [path]


def test_cli_history_is_opt_in_and_failed_save_never_reports_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MAIA2_ENABLED", "false")
    pgn = tmp_path / "synthetic.pgn"
    pgn.write_text('[Event "Synthetic history"]\n\n1. e4 e5 *\n')
    path = tmp_path / ".coach/state.json"
    args = ["analyse", "--pgn", str(pgn), "--out", str(tmp_path / "reports/result.md"), "--mock", "--state-path", str(path)]
    assert main(args) == 0
    assert not path.exists()
    assert "Updated coach state" not in capsys.readouterr().out
    assert main([*args, "--update-state"]) == 0
    previous = load_state(path)
    assert len(previous.runs) == 1 and len(previous.games) == 1
    before = path.read_bytes()
    capsys.readouterr()

    def fail(*_args):
        raise OSError("injected save failure")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError, match="injected save failure"):
        main([*args, "--update-state"])
    assert "Updated coach state" not in capsys.readouterr().out
    assert path.read_bytes() == before
    assert load_state(path) == previous

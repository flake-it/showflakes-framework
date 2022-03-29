import os
import json
import pytest

from experiment import (
    LOG_FILE, RECORD_FILE, SUBJECTS_FILE, RECORD_DIR, get_waiting_init, 
    get_trial_name, load_log, get_results
)


LOG = [
    "bar_5eb2d0_rerun_python3.7",
    "bar_fd569a_rerun_python3.7",
    "qux_fe6f61_noisy_python3.7",
    "qux_fe6f61_noisy_python3.8"
]


@pytest.fixture
def tmp_experiment(tmp_path):
    subjects = {
        "foo/bar": {
            "5eb2d0": [
                "10f89e",
                ["python3.6", "python3.7"],
                ["pip install -I --no-deps -e ."],
                ["python -m pytest"],
                9,
                3
            ],
            "fd569a": [
                "276a43",
                ["python3.6", "python3.7"],
                ["pip install -I --no-deps -e ."],
                ["python -m pytest"],
                8,
                6
            ]
        },
        "baz/qux": {
            "fe6f61": [
                "3b9240",
                ["python3.5", "python3.6", "python3.7", "python3.8"],
                ["pip install -I --no-deps -e ."],
                ["python -m pytest"],
                2,
                6
            ],
            "d4755a": [
                "2fe03b",
                ["python3.5", "python3.6", "python3.7", "python3.8"],
                ["pip install -I --no-deps -e ."],
                ["python -m pytest"],
                0,
                2
            ]
        }
    }

    cwd = os.getcwd()
    os.chdir(tmp_path)

    with open(LOG_FILE, "w") as fd:
        for name in LOG:
            fd.write(f"{name}\n")

    with open(SUBJECTS_FILE, "w") as fd:
        json.dump(subjects, fd)

    os.mkdir(RECORD_DIR)

    with open(os.path.join(RECORD_DIR, f"{LOG[0]}.json"), "w") as fd:
        json.dump({"test_a": [0, 1000], "test_b": [1, 1000]}, fd)

    with open(os.path.join(RECORD_DIR, f"{LOG[1]}.json"), "w") as fd:
        json.dump({"test_a": [0, 1000], "test_b": [0, 1000]}, fd)

    with open(os.path.join(RECORD_DIR, f"{LOG[2]}.json"), "w") as fd:
        json.dump({"test_a": [0, 250], "test_b": [250, 250]}, fd)

    with open(os.path.join(RECORD_DIR, f"{LOG[3]}.json"), "w") as fd:
        json.dump({"test_a": [0, 250], "test_b": [0, 250]}, fd)
    
    yield

    os.chdir(cwd)


def test_get_waiting_init(tmp_experiment):
    waiting = get_waiting_init()
    len_waiting_exp = 0

    with open(SUBJECTS_FILE, "r") as fd:
        subjects = json.load(fd)

    for subjects_repo in subjects.values():
        for _, executables, *_ in subjects_repo.values():
            len_waiting_exp += 1 + len(executables)

    assert len(waiting) == len_waiting_exp


def test_load_log(tmp_experiment):
    log, record = load_log()
    trials = set([get_trial_name(name) for name in log])

    assert set(LOG) == log
    assert trials.issuperset(record.keys())

    assert record == {
        "bar_5eb2d0_rerun": {"test_a": [0, 1000], "test_b": [1, 1000]}, 
        "bar_fd569a_rerun": {"test_a": [0, 1000], "test_b": [0, 1000]}, 
        "qux_fe6f61_noisy": {"test_a": [0, 500], "test_b": [250, 500]}
    }


def test_get_results(tmp_experiment):
    results = load_log()[1]

    with open(RECORD_FILE, "w") as fd:
        json.dump(results, fd)

    assert get_results() == {
        "bar": {"5eb2d0": [True, False], "fd569a": [False, False]}, 
        "qux": {"fe6f61": [False, True]}
    }
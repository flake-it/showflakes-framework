#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import shlex
import random
import shutil
import subprocess as sp

from multiprocessing import Pool

N_PROC = 20

LOG_FILE = "log.txt"
RECORD_FILE = "record.json"
SUBJECTS_FILE = "subjects.json"
SELECTION_FILE = "selection.txt"

STDOUT_DIR = "stdout"
RECORD_DIR = "record"
SUBJECTS_DIR = "subjects"
CONT_DIR = os.path.join("/", "home", "user")
CONT_RECORD_DIR = os.path.join(CONT_DIR, RECORD_DIR)
CONT_SUBJECTS_DIR = os.path.join(CONT_DIR, SUBJECTS_DIR)

PIP_VERSION = "pip==20.2.4"
PIP_INSTALL = ["pip", "install", "-I", "--no-deps"]

PLUGIN_BLACKLIST = [
    "-p", "no:cov",
    "-p", "no:flaky",
    "-p", "no:xdist",
    "-p", "no:sugar",
    "-p", "no:replay",
    "-p", "no:forked",
    "-p", "no:ordering",
    "-p", "no:randomly",
    "-p", "no:flakefinder",
    "-p", "no:random_order",
    "-p", "no:rerunfailures"
]

CAUSES = [
    "Async. Wait",
    "Concurrency",
    "Floating Point",
    "I/O",
    "Network",
    "Order Dependency",
    "Randomness",
    "Resource Leak",
    "Time",
    "Unordered Coll.",
    "Miscellaneous"
]


def load_subjects():
    with open(SUBJECTS_FILE, "r") as fd:
        return json.load(fd)


def clone_project(url, proj):
    repo_dir = os.path.join(CONT_SUBJECTS_DIR, proj, proj)
    sp.run(["git", "clone", url, repo_dir], check=True)


def clone_subjects():
    args = []

    for repo in load_subjects():
        url = f"https://github.com/{repo}"
        proj = repo.split("/", 1)[1]
        args.append((url, proj))

    random.shuffle(args)

    with Pool(processes=N_PROC) as pool:
        pool.starmap(clone_project, args)


def mk_dir(path):
    os.makedirs(path, exist_ok=True)


def setup_env(proj, sha, exe, setup_cmds):
    repo_dir = os.path.join(CONT_SUBJECTS_DIR, proj, proj)
    exe_dir = os.path.join(CONT_SUBJECTS_DIR, proj, sha, exe)

    work_dir = os.path.join(exe_dir, proj)
    venv_dir = os.path.join(exe_dir, "venv")

    shutil.copytree(repo_dir, work_dir, symlinks=True)
    sp.run(["git", "reset", "--hard", sha], check=True, cwd=work_dir)
    sp.run(["virtualenv", f"--python={exe}", venv_dir], check=True)

    env = os.environ.copy()
    bin_dir = os.path.join(venv_dir, "bin")
    env["PATH"] = bin_dir + ":" + env["PATH"]

    req_file = os.path.join(exe_dir, "requirements.txt")
    showflakes_dir = os.path.join(CONT_DIR, "showflakes")

    sp.run([*PIP_INSTALL, PIP_VERSION], check=True, env=env)
    sp.run([*PIP_INSTALL, "-r", req_file], check=True, env=env)
    sp.run([*PIP_INSTALL, showflakes_dir], check=True, env=env)

    for cmd in setup_cmds:
        sp.run(shlex.split(cmd), check=True, cwd=work_dir, env=env)


def setup_image():
    args = []
    
    for repo, subjects_repo in load_subjects().items():
        proj = repo.split("/", 1)[1]

        for sha, executables, setup_cmds, *_ in subjects_repo.values():
            for exe in executables:
                args.append((proj, sha, exe, setup_cmds))
                
    random.shuffle(args)
    mk_dir(CONT_RECORD_DIR)

    with Pool(processes=N_PROC) as pool:
        pool.starmap(setup_env, args)


def manage_container(name, max_runs, *exec_cmds):
    proj, sha, mode, exe = name.split("_", 3)
    sha_dir = os.path.join(CONT_SUBJECTS_DIR, proj, sha)
    selection_file = os.path.join(sha_dir, SELECTION_FILE)
    record_file = os.path.join(CONT_RECORD_DIR, f"{name}.json")

    exe_dir = os.path.join(sha_dir, exe)
    work_dir = os.path.join(exe_dir, proj)
    bin_dir = os.path.join(exe_dir, "venv", "bin")

    env = os.environ.copy()
    env["PATH"] = bin_dir + ":" + env["PATH"]

    for cmd in exec_cmds[:-1]:
        sp.run(shlex.split(cmd), check=True, cwd=work_dir, env=env)

    sp.run(
        [
            *shlex.split(exec_cmds[-1]), "-v", *PLUGIN_BLACKLIST, 
            f"--record-file={record_file}", 
            f"--selection-file={selection_file}", 
            f"--max-runs={max_runs}", "--max-fail=100", "--max-time=300"
            *["--n-extra=100", "--shuffle", "--deprioritize"] * mode == "noisy"
        ],
        check=True, cwd=work_dir, env=env
    )


class Container:
    def __init__(self, name, max_runs, exec_cmds):
        self.name = name
        self.max_runs = str(max_runs)
        self.exec_cmds = exec_cmds

    def cancel(self):
        sp.run(
            ["docker", "stop", self.name], 
            stdout=sp.DEVNULL, stderr=sp.DEVNULL
        )

        self.stdout.close()

    def poll(self):
        exitcode = self.proc.poll()

        if exitcode is not None:
            self.stdout.close()

        return exitcode

    def throttle(self):
        down, up = [str(random.randint(1, 1024)) for _ in range(2)]

        for cmd in (["clear", "eth0"], ["eth0", down, up]):
            sp.run(
                ["docker", "exec", "-u=root", self.name, "wondershaper", *cmd], 
                stdout=sp.DEVNULL, stderr=sp.DEVNULL
            )

    def start(self):
        host_record_dir = os.path.join(os.getcwd(), RECORD_DIR)
        self.stdout = open(os.path.join(STDOUT_DIR, self.name), "w")

        self.proc = sp.Popen(
            [
                "docker", "run", f"-v={host_record_dir}:{CONT_RECORD_DIR}:rw", 
                "--rm", "--init", "--cpus=1", "--cap-add=NET_ADMIN", 
                f"--name={self.name}", "showflakes-framework", "python3.9", 
                "experiment.py", "container", self.name, self.max_runs,
                *self.exec_cmds
            ],
            stdout=self.stdout, stderr=self.stdout
        )


def split_between(coll, n):
    split = [0] * len(coll)

    for i in range(n):
        split[i % len(coll)] += 1

    return zip(coll, split)


def get_waiting_init():
    waiting = []

    for repo, subjects_repo in load_subjects().items():
        proj = repo.split("/", 1)[1]

        for sha, executables, _, exec_cmds, *_ in subjects_repo.values():
            name = f"{proj}_{sha}_rerun_{executables[-1]}"
            cont = Container(name, 1000, exec_cmds)
            waiting.append(cont)

            for exe, max_runs in split_between(executables, 1000):
                name = f"{proj}_{sha}_noisy_{exe}"
                cont = Container(name, max_runs, exec_cmds)
                waiting.append(cont)

    random.shuffle(waiting)
    return waiting


def get_trial_name(name):
    return "_".join(name.split("_")[:3])


def update_record(name, record):
    trial = get_trial_name(name)
    record_trial = record.setdefault(trial, {})
    record_file = os.path.join(RECORD_DIR, f"{name}.json")

    with open(record_file, "r") as fd:
        for nid, (n_fail, n_runs) in json.load(fd).items():
            record_nid = record_trial.setdefault(nid, [0, 0])
            record_nid[0] += n_fail
            record_nid[1] += n_runs


def load_log():
    log = set()
    record = {}

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as fd:
            for line in fd:
                name = line.strip()

                log.add(name)
                update_record(name, record)

    return log, record


def check_record(record):
    return any(0 < n_fail < n_runs for n_fail, n_runs in record.values())


def run_experiment():
    mk_dir(STDOUT_DIR)
    mk_dir(RECORD_DIR)
    log, record = load_log()
    waiting = get_waiting_init()
    running, running_new = [], []

    while running or waiting:
        for cont in running:
            trial = get_trial_name(cont.name)
            record_trial = record.get(trial, {})

            if check_record(record_trial):
                print(f"cancelled: {cont.name}")
                cont.cancel()
                continue

            exitcode = cont.poll()
            
            if exitcode is None:
                running_new.append(cont)
                mode = cont.name.split("_", 3)[2]

                if mode == "noisy":
                    cont.throttle()
            elif exitcode == 0:
                print(f"succeeded: {cont.name}")
                update_record(cont.name, record)

                with open(LOG_FILE, "a") as fd:
                    fd.write(f"{cont.name}\n")
            else:
                print(f"failed: {cont.name}")

        while len(running_new) < N_PROC and waiting:
            cont = waiting.pop()            
            trial = get_trial_name(cont.name)
            record_trial = record.get(trial, {})

            if cont.name in log or check_record(record_trial):
                print(f"skipped: {cont.name}")
            else:
                mode = trial.split("_", 2)[2]
                running_new.append(cont)
                cont.start()

                if mode == "noisy":
                    cont.throttle()

        running, running_new = running_new, running
        running_new.clear()
        time.sleep(10)

    with open(RECORD_FILE, "w") as fd:
        json.dump(record, fd, indent=4)


def get_results():
    results = {}

    with open(RECORD_FILE, "r") as fd:
        record = json.load(fd)

    for trial, record_trial in record.items():
        proj, sha, mode = trial.split("_", 2)
        results_proj = results.setdefault(proj, {})
        results_sha = results_proj.setdefault(sha, [False, False])
        results_sha[mode == "noisy"] = check_record(record_trial)

    return results


def cellfn(cell):
    if isinstance(cell, str):
        return cell
    elif isinstance(cell, int):
        return "-" if cell == 0 else str(cell)


def write_table(table_file, table):
    with open(table_file, "w") as fd:
        for i, table_i in enumerate(table):
            i and fd.write("\\midrule\n")

            for j, table_j in enumerate(table_i):
                j % 2 and fd.write("\\rowcolor{gray!20}\n")
                fd.write(" & ".join([cellfn(c) for c in table_j]) + " \\\\\n")


def write_figures():
    results = get_results()
    table_commits = [[], [["{\\bf Total}", 0, 0, 0]]]

    table_categories = [
        [[c, *[0] * 10] for c in CAUSES], [["{\\bf Total}", *[0] * 10]]
    ]

    for repo, subjects_repo in load_subjects().items():
        proj = repo.split("/", 1)[1]
        results_proj = results[proj]
        n_commits = len(subjects_repo)
        table_commits[1][0][1] += n_commits
        table_categories[1][0][10] += n_commits
        table_commits_proj = [repo, n_commits, 0, 0]

        for sha, *_, cause, repair in subjects_repo.values():
            results_parent = results_proj[sha]

            for row in (table_commits_proj, table_commits[1][0]):
                row[2] += results_parent[0]
                row[3] += results_parent[1]

            table_categories[0][cause][repair + 1] += 1
            table_categories[1][0][repair + 1] += 1
            table_categories[0][cause][10] += 1

        table_commits[0].append(table_commits_proj)

    write_table("commits.tex", table_commits)
    write_table("categories.tex", table_categories)


if __name__ == "__main__":
    if len(sys.argv) > 1:        
        command, *args = sys.argv[1:]

        if command == "clone":
            clone_subjects(*args)
        elif command == "setup":
            setup_image(*args)
        elif command == "container":
            manage_container(*args)
        elif command == "run":
            run_experiment(*args)
        elif command == "figures":
            write_figures(*args)
        else:
            raise ValueError("Unrecognized command given")
    else:
        raise ValueError("No command given")

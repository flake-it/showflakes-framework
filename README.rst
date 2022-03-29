=========================================================================================================
What Do Developer-Repaired Flaky Tests Tell Us About the Effectiveness of Automated Flaky Test Detection?
=========================================================================================================

Replication package.

Contents
========

- ``Dockerfile`` configuration file for the Docker image.
- ``experiment.py`` script for setting up the Docker image, executing containers, and collating results.
- ``log.txt`` log of completed containers.
- ``record/`` output of ShowFlakes.
- ``record.json`` result of collating the records in ``record/``.
- ``showflakes/`` submodule for the ShowFlakes plugin (see ``showflakes/README.rst``).
- ``subjects/`` contains selection files for the developer-repaired flaky tests of each commit along with requirements files.
- ``subjects.json`` contains information about each commit.
- ``test_experiment.py`` test suite for ``experiment.py``.

Installing
==========

Clone this repository with the ``--recursive`` option to ensure that the ShowFlakes submodule is also fetched. Build the Docker image with ``docker build -t showflakes-framework .`` from inside this directory. Note that this will result in an image that is roughly 130gb in size.

Usage
=====

Before running the experiment, you need to build the Docker image with ``docker build -t showflakes-framework .`` and then the main experiment automation script can be executed with ``python experiment.py TASK``, where ``TASK`` is one of:

- ``run`` run the main experiment. The script will execute many containers, named using the following convention: ``PROJECT_COMMIT_MODE_PYTHON``, where ``MODE`` is either ``rerun`` or ``noisy`` and ``PYTHON`` is the Python interpreter. Within these containers, ShowFlakes reruns the developer-repaired flaky tests of ``COMMIT`` and records test case outcomes inside ``record/``. Upon successful completion, the container name is appended to ``log.txt``. Once there are no more containers to execute, the script collates the results into ``record.json``.
- ``figures`` generate the contents of the LaTeX tables. Requires a full ``record/``.

Subjects
========

Information about each commit can be found in the JSON file ``subjects.json`` and is structured as follows:

::

    {
        REPOSITORY: {
            COMMIT: {
                PARENT-COMMIT,
                [PYTHON-INTERPRETERS],
                [SETUP-COMMANDS],
                [EXEC-COMMANDS],
                CAUSE-CATEGORY,
                REPAIR-CATEGORY
            },
            ...
        },
        ...
    }

The ``CAUSE-CATEGORY`` and ``REPAIR-CATEGORY`` are integer values described in the following tables:

``CAUSE-CATEGORY``
------------------

===== ==============
Value Cause Category
===== ==============
0     Async. Wait
1     Concurrency
2     Floating Point
3     I/O
4     Network
5     Order Dependency
6     Randomness
7     Resource Leak
8     Time
9     Unordered Coll.
10    Miscellaneous
===== ==============

``REPAIR-CATEGORY``
-------------------

===== ===============
Value Repair Category
===== ===============
0     Add Mock
1     Add/Adjust Wait
2     Guarantee Order
3     Isolate State
4     Manage Resource
5     Reduce Randomness
6     Reduce Scope
7     Widen Assertion
8     Miscellaneous
===== ===============
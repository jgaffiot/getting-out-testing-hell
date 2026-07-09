Getting out of testing hell!

We know we should write automated tests. But too often, it is a real chore:
they may be slow, unreliable, difficult to run, to maintain, even to write!
Why is it so hard? How to take back control?

For that, you will work on a realistic project: a Python app with FastAPI backend,
a PostgreSQL database, configuration files, third-party APIs, ...
and tests that are awful.

You will review:

    the quality culture of the project
    how it is architectured
    the existing tests
    and the code quality

Then you will prepare the plan:

    your own test pyramid / strategy
    testing tools needed
    essential scenarios
    the CI to have your back

And start coding:

    updating the existing tests
    adding new tests using powerful tooling
    minimal refactoring to enable testing
    creating fakes/mocks/simulators to enable testing

You'll leave able to:

    diagnose what makes tests slow or convoluted
    design a pragmatic test strategy for your codebase
    implement reliable tests, with fakes and testcontainers
    refactor just enough to make code testable

It will be around 65% hands-on, and 35% guided analysis.
The first two parts will take the first half of the session, so that you have plenty of
time to actually implement the strategy during the second half.
The code repository will stay available to you after the workshop,
along with an example of the end-result.

Setup :

    uv
    (optional) docker or podman, to run TestContainers
    (optional) a GitHub or GitLab account, to run CI

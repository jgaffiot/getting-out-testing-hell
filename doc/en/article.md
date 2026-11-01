# Getting out of the testing hell

## Intro

The need to write automated tests is now well established among developers. It is the
only way to test systematically and completely, to avoid regressions or simply to avoid
moving forward blindly.

But once that consensus is reached, the trouble starts. Writing tests is seen as a
chore, often pushed back to the end of the project, and one that doesn't attract
volunteers.
Then the tests turn out to be too often slow, brittle, costly to maintain, not obvious
to run, incomplete... and we end up getting used to negative test reports ("the CI is
red all the time, but that's normal").
This is called normalization of deviance, and it can lead to disaster, such as crashing
[Challenger](https://en.wikipedia.org/wiki/Space_Shuttle_Challenger_disaster)
*and* [Columbia](https://en.wikipedia.org/wiki/Space_Shuttle_Columbia_disaster).

Granted, when automated tests are useless or missing, it's an app that crashes rather
than a shuttle, but the process is the same.

So, how do we regain control of our automated tests?

## Asking the right questions

More than the tests themselves, the goal is to ensure the quality and mastery of the
code, code that we can therefore ship and evolve with confidence.
Tests form a software system, parallel to the main project, whose goal is to ensure its
quality: reliability, repeatability, maintainability, evolvability.

Like any software system, it requires development time and expensive skills to acquire.
Thus, the test suite is an investment for the main project, which must therefore reap a
benefit in quality. It is therefore crucial to define what is expected from the tests.
Since it's always possible to add more tests, we also need to define the resources
allocated to testing, which will later allow us to arbitrate between adding tests or
adding features.

Automated tests, as opposed to manual tests, form all or part of the test suite, and are
run automatically and systematically, typically on every commit.
This protects against most regressions, and this information reaches the developer
quickly.
It is therefore a central part of the continuous integration (CI) process, to the point
that "CI" now refers to automated test pipelines!

Some tests remain mostly manual, for example user tests (including usability tests, A/B
tests...), load tests, performance tests, penetration tests...

Automated tests are there to bring a certain level of confidence in code quality, in
order to reach the project's quality goals within the allocated resources. Never
forgotten, they prevent bugs and stop quality from drifting, but are often limited by
the difficulty of automating things.

## Starting back from the basics

Tests are part of the toolbox for reaching the quality goal, but they are not alone.
Several successive layers of tools are needed to catch the different quality issues.

The first layer is a code formatter, which standardizes the code. The benefits are
making the code easier to read (for those who still read code), reducing the developer's
workload (for those who still write it), and cleaning up code comparisons from all
whitespace differences, which reduces the size of Pull Requests / Merge Requests.

The second layer consists of analysis software, starting with static analysis tools.
These do not execute the code (hence the name "static") but look for bad practices by
following simple text-recognition rules, such as regular expressions. Their big
advantage is detecting bugs very quickly and without risk (the code doesn't run) and
without conditions (no need for a test environment or anything else).

This category also includes compilers, especially with their warnings enabled, and type
checkers (for interpreted languages), which make sure types are consistent, again
without having executed a single line of code.

Finally, dynamic analyzers study the code while it's running, often at the cost of a
performance hit (memory and CPU), to look for logic errors that are harder to detect
(typically memory errors).

The last layer is of course to automate all the chosen tools, as close to the developer
as possible. First, a runner like [`doit`](https://pydoit.org/) or
[`just`](https://just.systems/man/en/introduction.html) lets you run all the chosen
quality tools with a single simple command. Then, we can take advantage of Git hooks to
automatically run these tools on certain commands, and typically on commit. Utilities
like the well-known [`pre-commit`](https://pre-commit.com/) or the more recent
[`prek`](https://prek.j178.dev/) make it easy to configure Git hooks. To avoid losing
your train of thought waiting for long tests to finish at commit time, only use tools
with a short execution time (up to a few seconds) in the pre-commit hook.

## Cleaning up the tests

Let's continue by cleaning up the existing tests, since of course some tests can be
deleted. First, unreliable tests must be disabled or removed, because they don't bring
the information the team needs: whether the test passes or not, we don't learn anything
more about the quality of the tested code. These tests can be re-enabled once
stabilized, which requires identifying the cause of the instability. Random number
generation, triggering based on the real clock, the (lack of) synchronization of code
running in parallel (multithreading, async...), and dependencies on external processes
or APIs are the most likely causes.

For example, this test fails unpredictably, because it depends on the real clock:

```python
# Fragile: depends on the system clock... and gets stuck for an hour!
def test_reporting_each_hour():
    manager = Manager()            # creates a report exactly on the hour
    assert manager.report is None  # false if the test is run exactly on the hour
    time.sleep(3600)               # that's long...
    assert manager.report is not None
```

The solution is to inject the clock so it can be controlled from the test, which makes
it both reliable and instantaneous:

```python
# Reliable: time is injected, and therefore controlled
def test_reporting_each_hour():
    clock = FakeClock(now=datetime(2025, 1, 1, 12, 1))
    manager = Manager(clock)           # refactoring of Manager
    assert manager.report is None      # starting 1 minute after noon: no report
    clock.advance(timedelta(hours=1))  # advance time without waiting
    assert manager.report is not None  # new report
```

Next, tests that take too long don't get the information to developers in time. They
can be deleted, sped up, or split off into a second test suite if the test is really
necessary and the execution time truly can't be reduced. This second test suite will
always be automated, but not run on every commit — at a lower frequency, such as once a
day (often overnight), or only just before merging to the main branch. What matters is
that the developer doesn't need the immediate result of the test to keep working, but
that the information brought by this suite of long tests is only needed, for example,
for a new release.

Finally, don't hesitate to prune the test suite: some tests aren't relevant anymore,
because they're too old, too specific, too coupled, or they test too little code.

## Making the code testable

The most serious testing problems are most often caused by the code under test: too
coupled and not observable enough, it forces the test to set up a whole environment, to
run the entire code at once, to play out a whole complex scenario to reach the initial
state in which the test can finally be run, and to rely on roundabout or fragile means
(log parsing...) to know whether the test succeeded.

The first thing to do is to isolate side effects as much as possible, especially
input/output, so that the project-specific code and business logic can be tested
independently. For any project that isn't a simple "pass-through", as much code as
possible should be testable without any special setup, just by running it.

Let's then sort side effects into 3 categories: black holes, white fountains, and the
rest. A black hole is write-only: you can only throw data into it, which is immediately
lost. This category includes logging and telemetry systems. A white fountain, the
theoretical opposite of a black hole, is read-only and can only be initialized, once.
This category includes the configuration system, which reconciles environment
variables, files, command line... and makes the result available to the rest of the
code.

Black holes and white fountains can have a lifetime equivalent to that of the entire
program and a global scope. They are the only side effects that can be tolerated across
the whole codebase. Once well identified, a setup shared by all tests will allow them to
be handled once and for all.

All other side effects must be isolated, and if possible injected into the business
code that uses them, rather than owned by the business code. Indeed, an injected
dependency gives the test complete freedom to disconnect the side effect and isolate the
code, whereas tight coupling makes testing difficult, especially with static languages.
With these languages, however, an appropriate type must be planned for class members
that will be replaced by a substitute. Testability must therefore be planned for at
design time.

```c++
// Hard to test, always instantiates a real, non-substitutable connection
class MyClassWithInternalConnection {
private:
    Client client;
public:
    MyClassWithInternalConnection(const char* host, int port) { client = Client(host, port); }
};
// Easy to test, can instantiate a substitute as well as a real connection. But more
// complex with a static language, ownership and lifetime of the client need to be defined.
class MyClassWithInvertedDependency {
private:
    // New type to hold the real connection or a substitute
    AbstractClient& client;  // can hold the real connection or the substitute
public:
    // In this example, the class instance takes ownership of the client
    MyClassWithInvertedDependency(AbstractClient&& client_): client(client_) {}
};
```

## Getting a grip on your test framework

All major languages have one or more test frameworks, which bring their share of
features on top of making tests easier to write, such as:

- launching from a single entry point
- organization into test suites, suites of suites...
- managing the environment, the OS, signals
- temporary files and directories
- capturing standard input and standard outputs
- collecting and structuring test results
- setup/teardown: a pair of special functions to respectively create and destroy a
  test's initial state
- fixture: a function that "fixes" the initial state for a test (a generalization of
  setup)
- assertions to compare results against expected values, or check an expected behavior
  (exception, function call...)
- injecting substitutes or mocks
- parallelization, plugins...

Using a test framework therefore brings a lot, at the cost of an onboarding time that
quickly pays for itself.

Substitute injection deserves special attention: it consists of selectively replacing
code that is hard to test (often because it has a side effect) with test-specific code,
by reimplementing the interface of the original code.
For example, a database connection object can be replaced with an object that does
nothing, immediately returning a fixed value.

The substitute can be built specifically to emulate complex or random behavior, but
with an instant and repeatable result.
It can also be completely empty, but let you check that the interface was called, with
which arguments...
Some dynamic-language frameworks even let you create substitutes without declaring the
interface at all, the interface being created on the fly, just to disconnect a side
effect.
Many plugins or libraries offer ready-to-use substitutes for the most common cases:
connections, time, randomness, databases, logs...

By combining these features, a test stays short and readable. The given/when/then
structure (also known as arrange/act/assert) clearly separates setup, the tested
action, and verification, turning it into executable documentation:

```python
def test_alert_sent_if_balance_negative():
    # given: an overdrawn account and a substituted mail-sending service
    mailer = FakeMailer()
    account = Account(balance=-50, mailer=mailer)

    # when: we trigger the overdraft check
    account.check_overdraft()

    # then: one, and only one, alert was sent to the account holder
    assert mailer.sent == [("overdraft_alert", account.holder)]
```

Here the `FakeMailer` substitute doesn't send any real mail: it just records the calls,
which lets us assert that the alert was indeed triggered, and only once, without
depending on a mail server.

## Speeding up the tests

Many approaches can help speed up tests:

- modularize the code and possibly split it into several libraries. That way, there's
  less code, fewer inputs, fewer edge cases to test, and each library is validated
  independently.
- prepare artifacts (libs, executables, images...) for testing (and for compilation if
  needed) so they're ready to use and cached. Using a precompiled lib is faster than
  recompiling it along with the whole project. If a test needs a container, the image
  must be available in cache and ready to use as soon as the container starts (no
  entrypoint that finishes the setup, for example).
- profile your tests, first to get the time per test, and then to know where the long
  tests spend their time.
  This step is essential to avoid moving forward blindly.
- parallelize tests (but CI workers may only have a single core)
- factor out setup and teardown shared across several tests
- avoid waiting during a test (`sleep(...)`), and instead react as soon as the action is
  done. Sometimes the code needs to be changed so it reports its state (return code,
  log, internal variable...) or lets the test retrieve it through a new API.
- reduce the number of different values tested, to focus on expected values and edge
  cases
- focus tests on a clear given/when/then sequence, avoiding chaining too many actions
- optimize the code whose test is irreducibly slow. Sometimes the problem is in the
  code.
- selectively enable certain options that slow down tests, such as coverage measurement
  or memory integrity checking
- selectively run tests based on the code that changed, easy when the code is
  well-structured and modular

Replacing a fixed wait with a conditional wait is a good illustration of this gain:
instead of sleeping "long enough" hoping the action is done (slow, and fragile if the
machine is under load), we return control as soon as the condition is met.

```python
# Slow and fragile: we wait an arbitrary duration
start_job()
time.sleep(5)
assert result_file.exists()

# Fast and reliable: we react as soon as the condition is true
job = start_job()
wait_until(lambda: job.is_done(), timeout=5)   # returns as soon as it's ready
assert result_file.exists()
```

## Filling the gaps in the tests

Once the existing tests are back in working order, we need to check that the test suite
achieves its goal, and in particular that there's no big hole left in test coverage. If
it hasn't been done already, coverage measurement needs to be added to the framework.
Beware, measuring coverage tends to slow down tests, sometimes a lot, so an option to
enable it selectively should be planned.

Test coverage should already be roughly uniform across the codebase, so the first thing
to look for is an untested part of the code (a whole file, class, function...). Then,
coverage should be used to check that the business logic (without side effects) is very
well tested, with coverage approaching 100%. Finally, coverage must be analyzed against
goals and resources: can the untested code easily be tested? Is it reused heavily
throughout the codebase? Is it critical? Is it business logic?

Once coverage has been analyzed, it's time to come back to input/output tests, for
which coverage is not the relevant metric. Indeed, it's easy to cover them with tests
that disconnect so many side effects that the test no longer provides much of a
guarantee. Instead, we should check that normal cases, edge cases, and error cases are
tested, check that the link with the rest of the system is genuinely tested at some
point (API connection, database...), or consider a communication contract to validate
(OpenAPI, for example).

There's no precise coverage percentage to reach, especially since it's relatively easy
to game that number by marking lines as excluded from coverage or by overusing
substitutes. Moreover, the last few percent are far harder to reach than the first ones.
A figure of 80% is a good starting point for discussion, with quality projects sitting
above that. It's more important to follow the trend: as the project evolves, coverage
should not go down, but go up (even slowly) as bugs get fixed and therefore tests get
added. Adding a check to your test pipelines that coverage doesn't regress notably
prevents adding features without their tests.

## Using AI wisely

For all these tasks, which are rather tedious and seen as a waste of time compared to
making progress on the project, AI is a valuable helper. It can be very tempting to
delegate the whole problem to AI (and the latest models will do a good job). But tests
are also the system that guarantees the code works, and that let the developer take
responsibility for the delivered code.
Does the generated test really check the important points? Or is it just a spaghetti of
substitutes that in fact tests nothing at all? Either way, the responsibility rests on
the developer's shoulders.

Depending on the developer and the project, several strategies are possible: generate
but review carefully, work step by step from the specifications, write the tests
manually or at least the main ones, use a verifying AI after generation...

Beyond the developer's ownership of generated tests, AI is above all a golden
opportunity to go further with testing: performance testing and optimization,
interface testing, fuzz testing, mutation testing... So many advanced testing
strategies that become accessible to every project.

## Conclusion

Once brought back under control, tests provide the confidence needed to move forward,
and become a development tool that makes it possible to ship fast and well.
At that point, the team has acquired a whole range of new skills, from getting a grip on
the framework to optimization, from refactoring the code to adding missing tests, which
make writing new tests routine.
Having become an everyday tool, tests can be written first, in some cases starting from
the specifications, turning what was a chore pushed to the end of the project into a
preparatory step that signals the end of development and guarantees quality.

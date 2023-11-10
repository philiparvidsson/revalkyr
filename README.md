Someone once told me...

``` text
So, "Revalkyr" could stand for:

ReScript Efficient Verification Analytics Logical Knowledge-Intensive Yielding Revolutionary

This interpretation emphasizes the tool's focus on providing efficient and logical verification, analytics, and knowledge-intensive solutions in ReScript programming, aiming to yield revolutionary results.
```

# What is this?

This is an attempt to automate the painstaking process and avant garde process of writing bindings for your ReScript projects. The goal of the project is to:

In general: Use AI to automatically do things for you in the background while you work on your ReScript code bases.

More specifically: Fix errors, write bindings, give suggestions and more.

We'll be using AI mainly, but there may also be inferenced operations done on static analysis (for example, pointing out trivial patterns that are still worth pointing out). In the end, revalkyr should be a sort of all-encompassing assistant suite for ReScript projects.

# Trusting the AI
The assistants API is fantastic, but due to the stochastic nature of the AI, the test results are difficult to assess over single runs. We should likely be gathering statistics over time to see failure rates. E.g., even if a test succeeds once, that says nothing about the reproducibility of the success.

# Running the tests

First off, you'll need to set up your OpenAI API key.

To just run the tests, simply:

``` shell
cd revalkyr
python -m --run-tests
```

If you want to run the tests without resetting everything:

``` shell
cd revalkyr
python -m --run-tests-dirty
```


# Contributing

I haven't really gotten far enough into the autobinds setup to be able to reason about it well enough to receive help, I think. It's still very experimental. But if you feel you can contribute to it then go ahead and do pull requests.

Mainly, I'm working on coming up with various test cases right now.

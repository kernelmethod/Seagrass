# Seagrass unit tests

This directory contains all of the unit tests for Seagrass.

## Installing testing dependencies

In order to run the tests in this directory, please install the testing
dependencies from the root of the repository:

```
pip install -r requirements_dev.txt
```

## Running tests

From the root of the repository, you can simply run the unit tests with

```
pytest test/
```

You can get a code coverage report by using the
[pytest-cov](https://github.com/pytest-dev/pytest-cov/) extension for pytest

```
pytest -rsf --cov-report term-missing cov=seagrass test/
```

This will also generate a `.coverage` file that you can use with other code
coverage tools. E.g., generate an HTML report with

```
pip install coverage
coverage html
```


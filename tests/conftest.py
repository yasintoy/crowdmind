"""Shared fixtures for CrowdMind tests."""

import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace


class MockResults:
    """Simulates EDSL Results object."""

    def __init__(self, data: dict, has_exceptions: bool = False):
        self._data = data
        self.has_unfixed_exceptions = has_exceptions

    def select(self, key):
        return SimpleNamespace(to_list=lambda: self._data.get(key, []))


class MockModel:
    """Simulates EDSL Model."""

    def __init__(self, name="test-model"):
        self.model_name = name


class MockAgent:
    """Simulates EDSL Agent."""

    def __init__(self, traits=None):
        self.traits = traits or {}


class MockSurvey:
    """Simulates EDSL Survey with chainable .by().run() API."""

    def __init__(self, results=None, should_fail=False, fail_count=0):
        self._results = results or MockResults({})
        self._should_fail = should_fail
        self._fail_count = fail_count
        self._call_count = 0

    def by(self, arg):
        return self

    def run(self, **kwargs):
        self._call_count += 1
        if self._should_fail and self._call_count <= self._fail_count:
            raise Exception("rate_limit_error: 429 Too Many Requests")
        return self._results


@pytest.fixture
def mock_model():
    return MockModel()


@pytest.fixture
def mock_agents():
    return [
        MockAgent({"persona": f"Test persona {i}", "category": "test"})
        for i in range(5)
    ]


@pytest.fixture
def mock_survey_factory():
    """Factory to create MockSurvey with specific behavior."""
    def _factory(data=None, should_fail=False, fail_count=0):
        results = MockResults(data or {"interest": [7]})
        return MockSurvey(results, should_fail, fail_count)
    return _factory

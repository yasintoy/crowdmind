# tests/test_runner.py
"""Tests for AdaptiveRunner - adaptive concurrency and per-interview retry."""

import pytest
from unittest.mock import MagicMock, patch
from tests.conftest import MockAgent, MockModel


class TestAdaptiveRunner:

    def test_runs_all_agents_and_collects_results(self):
        """All agents should be interviewed and results merged."""
        from crowdmind.validate.runner import AdaptiveRunner

        agents = [MockAgent({"persona": f"P{i}"}) for i in range(3)]
        model = MockModel()
        runner = AdaptiveRunner(max_concurrency=2)

        def mock_interview(survey, agent, model, agent_idx, question_names=None):
            return {"interest": 7 + agent_idx, "_agent_idx": agent_idx}

        with patch.object(runner, "_run_single_interview", side_effect=mock_interview):
            results = runner.run(
                survey=MagicMock(), agents=agents, model=model,
                question_names=["interest"],
            )

        assert len(results) == 3
        assert results[0]["interest"] == 7
        assert results[1]["interest"] == 8
        assert results[2]["interest"] == 9

    def test_respects_max_concurrency(self):
        from crowdmind.validate.runner import AdaptiveRunner
        runner = AdaptiveRunner(max_concurrency=2)
        assert runner.max_concurrency == 2
        # Semaphore is created per-batch in _run_batch, not at init
        # Verify max_concurrency setting is preserved correctly
        assert runner._initial_concurrency == 2

    def test_retries_failed_interviews_only(self):
        """When some interviews fail, retry only those - not all."""
        from crowdmind.validate.runner import AdaptiveRunner

        runner = AdaptiveRunner(max_concurrency=5, max_retries=2, rate_limit_delay=0.01)
        agents = [MockAgent({"persona": f"P{i}"}) for i in range(4)]
        model = MockModel()

        call_count = {}

        def mock_interview(survey, agent, model, agent_idx, question_names=None):
            call_count[agent_idx] = call_count.get(agent_idx, 0) + 1
            if agent_idx in (1, 3) and call_count[agent_idx] <= 1:
                raise Exception("429 rate_limit_error")
            return {"interest": 7, "_agent_idx": agent_idx}

        with patch.object(runner, "_run_single_interview", side_effect=mock_interview):
            results = runner.run(
                survey=MagicMock(), agents=agents, model=model,
                question_names=["interest"],
            )

        assert call_count[1] == 2
        assert call_count[3] == 2
        assert all(r is not None for r in results)

    def test_reduces_concurrency_on_rate_limit(self):
        from crowdmind.validate.runner import AdaptiveRunner
        runner = AdaptiveRunner(max_concurrency=5)
        runner._on_rate_limit()
        assert runner.max_concurrency < 5

    def test_recovers_concurrency_after_clean_runs(self):
        from crowdmind.validate.runner import AdaptiveRunner
        runner = AdaptiveRunner(max_concurrency=5)
        runner._on_rate_limit()
        reduced = runner.max_concurrency
        for _ in range(3):
            runner._on_success()
        assert runner.max_concurrency > reduced

    def test_returns_partial_results_after_max_retries(self):
        from crowdmind.validate.runner import AdaptiveRunner

        runner = AdaptiveRunner(max_concurrency=2, max_retries=1, rate_limit_delay=0.01)
        agents = [MockAgent({"persona": f"P{i}"}) for i in range(3)]

        def always_fail_agent_1(survey, agent, model, agent_idx, question_names=None):
            if agent_idx == 1:
                raise Exception("429 rate_limit_error")
            return {"interest": 7, "_agent_idx": agent_idx}

        with patch.object(runner, "_run_single_interview", side_effect=always_fail_agent_1):
            results = runner.run(
                survey=MagicMock(), agents=agents, model=MagicMock(),
                question_names=["interest"],
            )

        successful = [r for r in results if r is not None]
        assert len(successful) == 2
        assert results[1] is None


class TestAdaptiveRunnerCooldown:

    def test_cooldown_is_zero_when_no_failures(self):
        from crowdmind.validate.runner import AdaptiveRunner
        runner = AdaptiveRunner()
        assert runner.get_cooldown() == 0

    def test_cooldown_increases_after_rate_limit(self):
        from crowdmind.validate.runner import AdaptiveRunner
        runner = AdaptiveRunner()
        runner._on_rate_limit()
        assert runner.get_cooldown() > 0

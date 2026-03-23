# tests/test_survey_integration.py
"""Tests for survey.py integration with AdaptiveRunner."""

import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import MockAgent


@pytest.fixture
def mock_edsl_env():
    """Patch all EDSL dependencies so tests work without EDSL installed."""
    with patch("crowdmind.validate.survey.HAS_EDSL", True), \
         patch("crowdmind.validate.survey.create_survey", return_value=MagicMock()), \
         patch("crowdmind.validate.survey.Agent", MockAgent), \
         patch("crowdmind.validate.survey.AgentList", lambda agents: agents), \
         patch("crowdmind.validate.survey.Model", lambda name: MagicMock()), \
         patch("crowdmind.validate.personas.random") as mock_random:
        mock_random.sample = lambda pop, k: pop[:k]
        yield


class TestSurveyUsesAdaptiveRunner:
    """Verify survey.py delegates to AdaptiveRunner."""

    def test_multi_metric_survey_uses_runner(self, mock_edsl_env):
        """run_multi_metric_survey should call run_interviews, not batch .run()."""
        with patch("crowdmind.validate.survey.run_interviews") as mock_run:
            mock_run.return_value = [
                {"interest": 7, "usefulness": 6, "urgency": 5,
                 "would_pay": "Yes, definitely",
                 "reasoning": "Good tool", "missing": "Nothing",
                 "_agent_idx": 0},
                {"interest": 8, "usefulness": 7, "urgency": 6,
                 "would_pay": "Maybe, depends on price",
                 "reasoning": "Decent", "missing": "Docs",
                 "_agent_idx": 1},
            ]

            from crowdmind.validate.survey import run_multi_metric_survey

            result = run_multi_metric_survey(
                content="Test product idea",
                num_agents=2,
                verbose=False,
                report_api_issues=False,
            )

            mock_run.assert_called_once()
            assert result.scores["interest"] == 7.5
            assert result.scores["usefulness"] == 6.5

    def test_handles_partial_failures(self, mock_edsl_env):
        """When some interviews return None, scores use available results only."""
        with patch("crowdmind.validate.survey.run_interviews") as mock_run:
            mock_run.return_value = [
                {"interest": 8, "usefulness": 7, "urgency": 6,
                 "would_pay": "Yes, definitely",
                 "reasoning": "Great", "missing": "Nothing",
                 "_agent_idx": 0},
                None,  # Failed interview
                {"interest": 6, "usefulness": 5, "urgency": 4,
                 "would_pay": "No",
                 "reasoning": "Meh", "missing": "Everything",
                 "_agent_idx": 2},
            ]

            from crowdmind.validate.survey import run_multi_metric_survey

            result = run_multi_metric_survey(
                content="Test idea",
                num_agents=3,
                verbose=False,
                report_api_issues=False,
            )

            assert result.scores["interest"] == 7.0
            assert len(result.feedback) == 2

    def test_accepts_shared_runner(self, mock_edsl_env):
        """Should pass runner param through to run_interviews."""
        from crowdmind.validate.runner import AdaptiveRunner

        shared_runner = AdaptiveRunner(max_concurrency=3)

        with patch("crowdmind.validate.survey.run_interviews") as mock_run:
            mock_run.return_value = [
                {"interest": 7, "usefulness": 6, "urgency": 5,
                 "would_pay": "Yes, definitely",
                 "reasoning": "OK", "missing": "None",
                 "_agent_idx": 0},
            ]

            from crowdmind.validate.survey import run_multi_metric_survey

            run_multi_metric_survey(
                content="Test",
                num_agents=1,
                verbose=False,
                runner=shared_runner,
            )

            # Verify runner was passed through
            call_kwargs = mock_run.call_args
            passed_runner = call_kwargs.kwargs.get("runner") or (
                call_kwargs[1].get("runner") if len(call_kwargs) > 1 else None
            )
            assert passed_runner is shared_runner

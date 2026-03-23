"""End-to-end test: validate flow with adaptive runner (all mocked)."""

import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import MockAgent


class TestEndToEnd:
    """Full flow: survey -> AdaptiveRunner -> mock EDSL interviews."""

    def test_validate_flow_with_rate_limit_recovery(self):
        """Simulate: 2 of 5 interviews hit 429 on first try, retry succeeds."""
        from crowdmind.validate.runner import AdaptiveRunner

        call_counts = {}

        def mock_interview(survey, agent, model, agent_idx, question_names=None):
            call_counts[agent_idx] = call_counts.get(agent_idx, 0) + 1
            if agent_idx in (1, 3) and call_counts[agent_idx] == 1:
                raise Exception("429 rate_limit_error")
            return {
                "interest": 7, "usefulness": 6, "urgency": 5,
                "would_pay": "Yes, definitely",
                "reasoning": "Good product", "missing": "Nothing",
                "_agent_idx": agent_idx,
            }

        with patch.object(
            AdaptiveRunner, "_run_single_interview", side_effect=mock_interview
        ), \
        patch("crowdmind.validate.survey.HAS_EDSL", True), \
        patch("crowdmind.validate.survey.create_survey", return_value=MagicMock()), \
        patch("crowdmind.validate.survey.Agent", MockAgent), \
        patch("crowdmind.validate.survey.AgentList", lambda agents: agents), \
        patch("crowdmind.validate.survey.Model", lambda name: MagicMock()), \
        patch("crowdmind.validate.personas.random") as mock_random:
            mock_random.sample = lambda pop, k: pop[:k]

            from crowdmind.validate.survey import run_multi_metric_survey

            result = run_multi_metric_survey(
                content="Test product idea for e2e test",
                num_agents=5,
                verbose=False,
                report_api_issues=False,
            )

        # All 5 should have results (2 retried successfully)
        assert len(result.feedback) == 5
        assert result.scores["interest"] == 7.0
        # Agents 1 and 3 should have been called twice
        assert call_counts[1] == 2
        assert call_counts[3] == 2

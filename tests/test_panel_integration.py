# tests/test_panel_integration.py
"""Tests for panel.py integration with AdaptiveRunner."""

import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import MockAgent


@pytest.fixture
def mock_panel_edsl():
    """Patch EDSL for panel.py tests."""
    with patch("crowdmind.validate.panel.HAS_EDSL", True), \
         patch("crowdmind.validate.panel.Agent", MockAgent), \
         patch("crowdmind.validate.panel.AgentList") as mock_al, \
         patch("crowdmind.validate.panel.Model", lambda name: MagicMock()), \
         patch("crowdmind.validate.panel.Survey", MagicMock()):
        mock_al.side_effect = lambda agents: MagicMock(_agents=agents)
        yield


class TestPanelUsesAdaptiveRunner:
    def test_run_evaluation_uses_runner(self, mock_panel_edsl):
        """run_evaluation should use run_interviews."""
        with patch("crowdmind.validate.panel.run_interviews") as mock_run:
            mock_run.return_value = [
                {"star": 7, "_agent_idx": 0},
                {"star": 8, "_agent_idx": 1},
                {"star": 6, "_agent_idx": 2},
            ]

            from crowdmind.validate.panel import run_evaluation

            result = run_evaluation(
                readme_content="Test product",
                num_agents=3,
                verbose=False,
            )

            mock_run.assert_called_once()
            assert result["avg_star"] == 7.0

# tests/test_optimize_pipelining.py
"""Tests for optimize loop adaptive cooldown and proposal pipelining."""

import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace


class TestOptimizeCooldown:
    """The optimize loop should use a shared runner across iterations."""

    @patch("crowdmind.optimize.autoresearch._run_survey")
    def test_passes_runner_to_survey(self, mock_survey):
        """Shared runner should be passed through to _run_survey."""
        mock_survey.return_value = SimpleNamespace(scores={"overall": 9.0})

        from crowdmind.optimize.autoresearch import AutoresearchLoop

        loop = AutoresearchLoop()
        loop.client = MagicMock()
        loop.client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Add examples")]
        )

        with patch.object(loop, "_apply_proposal", return_value="improved"):
            loop.optimize(
                content="test",
                target_score=95.0,
                max_iterations=1,
                verbose=False,
                num_personas=2,
            )

        # _run_survey should have been called with a runner kwarg
        for call_args in mock_survey.call_args_list:
            assert "runner" in call_args.kwargs

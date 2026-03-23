"""
Adaptive Interview Runner

Sits between CrowdMind and EDSL to control concurrency, retry failed
interviews, and auto-tune based on observed rate limits.

Instead of survey.by(all_agents).by(model).run() which fires everything
at once, this runs individual per-agent interviews through a thread pool
with a semaphore, retrying only the specific interviews that fail.
"""

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

try:
    from edsl import AgentList
    HAS_EDSL = True
except ImportError:
    HAS_EDSL = False


# Read defaults from env (previously lived in survey.py)
DEFAULT_MAX_RETRIES = int(os.environ.get("CROWDMIND_MAX_RETRIES", "2"))
DEFAULT_RATE_LIMIT_DELAY = float(os.environ.get("CROWDMIND_RATE_LIMIT_DELAY", "10"))


class AdaptiveRunner:
    """
    Runs EDSL surveys with adaptive concurrency control.

    - Starts at max_concurrency, drops on 429s, recovers after clean runs
    - Retries only failed interviews (not the entire batch)
    - Provides cooldown hints for callers (e.g., optimize loop)
    """

    MIN_CONCURRENCY = 1
    RECOVERY_THRESHOLD = 3  # clean batches before increasing concurrency

    def __init__(
        self,
        max_concurrency: int = 5,
        max_retries: int = DEFAULT_MAX_RETRIES,
        rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY,
        verbose: bool = False,
    ):
        self._initial_concurrency = max_concurrency
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.rate_limit_delay = rate_limit_delay
        self.verbose = verbose

        self._semaphore = threading.Semaphore(max_concurrency)
        self._lock = threading.Lock()
        self._consecutive_clean = 0
        self._total_rate_limits = 0
        self._cooldown_seconds = 0.0

    def run(
        self,
        survey: Any,
        agents: List[Any],
        model: Any,
        question_names: Optional[List[str]] = None,
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Run survey for each agent with adaptive concurrency.

        Returns:
            List of result dicts (one per agent), None for failed interviews.
        """
        results: List[Optional[Dict[str, Any]]] = [None] * len(agents)
        failed_indices: List[int] = list(range(len(agents)))

        for attempt in range(1 + self.max_retries):
            if not failed_indices:
                break

            if attempt > 0:
                delay = self.rate_limit_delay * attempt
                if self.verbose:
                    print(
                        f"  Retrying {len(failed_indices)} failed interview(s) "
                        f"in {delay:.0f}s (attempt {attempt + 1})..."
                    )
                time.sleep(delay)

            batch_failures = []
            batch_results = self._run_batch(
                survey, agents, model, failed_indices, question_names
            )

            for idx, result in batch_results:
                if result is not None:
                    results[idx] = result
                else:
                    batch_failures.append(idx)

            failed_indices = batch_failures

            if not batch_failures:
                self._on_success()
            else:
                self._on_rate_limit()

        if failed_indices and self.verbose:
            print(
                f"  Warning: {len(failed_indices)} interview(s) failed after "
                f"{self.max_retries + 1} attempts."
            )

        return results

    def _run_batch(
        self,
        survey: Any,
        agents: List[Any],
        model: Any,
        indices: List[int],
        question_names: Optional[List[str]],
    ) -> List[tuple]:
        """Run a batch of interviews with concurrency control."""
        batch_results = []
        self._semaphore = threading.Semaphore(self.max_concurrency)

        with ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
            futures = {}
            for idx in indices:
                future = executor.submit(
                    self._guarded_interview,
                    survey, agents[idx], model, idx, question_names,
                )
                futures[future] = idx

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    batch_results.append((idx, result))
                except Exception:
                    batch_results.append((idx, None))

        return batch_results

    def _guarded_interview(
        self,
        survey: Any,
        agent: Any,
        model: Any,
        agent_idx: int,
        question_names: Optional[List[str]],
    ) -> Optional[Dict[str, Any]]:
        """Run a single interview, guarded by the semaphore."""
        self._semaphore.acquire()
        try:
            return self._run_single_interview(
                survey, agent, model, agent_idx, question_names
            )
        finally:
            self._semaphore.release()

    def _run_single_interview(
        self,
        survey: Any,
        agent: Any,
        model: Any,
        agent_idx: int,
        question_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute a single EDSL interview for one agent."""
        if not HAS_EDSL:
            raise ImportError("EDSL is required")

        single_agent = AgentList([agent]) if not isinstance(agent, AgentList) else agent

        result = survey.by(single_agent).by(model).run(
            print_exceptions=False,
            verbose=False,
        )

        if getattr(result, "has_unfixed_exceptions", False):
            raise RuntimeError("EDSL interview failed with exceptions")

        data = {"_agent_idx": agent_idx}
        if question_names:
            for qname in question_names:
                values = result.select(qname).to_list()
                data[qname] = values[0] if values else None

        return data

    def _on_rate_limit(self):
        """Called when a batch had rate limit failures."""
        with self._lock:
            self._consecutive_clean = 0
            self._total_rate_limits += 1
            old = self.max_concurrency
            self.max_concurrency = max(
                self.MIN_CONCURRENCY,
                self.max_concurrency // 2,
            )
            self._cooldown_seconds = min(
                30.0, self.rate_limit_delay * self._total_rate_limits
            )
            if self.verbose and old != self.max_concurrency:
                print(f"  Concurrency reduced: {old} -> {self.max_concurrency}")

    def _on_success(self):
        """Called when a batch completed with no failures."""
        with self._lock:
            self._consecutive_clean += 1
            if (
                self._consecutive_clean >= self.RECOVERY_THRESHOLD
                and self.max_concurrency < self._initial_concurrency
            ):
                old = self.max_concurrency
                self.max_concurrency = min(
                    self._initial_concurrency,
                    self.max_concurrency + 1,
                )
                self._consecutive_clean = 0
                self._cooldown_seconds = max(0, self._cooldown_seconds - 5.0)
                if self.verbose and old != self.max_concurrency:
                    print(f"  Concurrency recovered: {old} -> {self.max_concurrency}")

    def get_cooldown(self) -> float:
        """Suggested cooldown in seconds before next batch (for optimize loop)."""
        return self._cooldown_seconds


def run_interviews(
    survey: Any,
    agents: List[Any],
    model: Any,
    question_names: Optional[List[str]] = None,
    max_concurrency: int = 5,
    max_retries: int = DEFAULT_MAX_RETRIES,
    verbose: bool = False,
    runner: Optional[AdaptiveRunner] = None,
) -> List[Optional[Dict[str, Any]]]:
    """
    Convenience function: run survey across agents with adaptive rate limiting.

    Pass a shared `runner` instance to preserve rate-limit state across
    multiple calls (e.g., market analysis running 3 surveys back-to-back).
    """
    if runner is None:
        runner = AdaptiveRunner(
            max_concurrency=max_concurrency,
            max_retries=max_retries,
            verbose=verbose,
        )
    return runner.run(survey, agents, model, question_names)

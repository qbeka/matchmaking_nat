import math


class SkillPosterior:
    """
    Represents the posterior distribution of a skill proficiency using a Beta
    distribution. The proficiency is a probability, modeled as the parameter `p`
    of a Binomial distribution. The Beta distribution is the conjugate prior for
    the Binomial likelihood, which makes Bayesian updating straightforward.

    Attributes:
        alpha (float): The alpha parameter of the Beta distribution, representing successes + 1.
        beta (float): The beta parameter of the Beta distribution, representing failures + 1.
    """

    def __init__(self, alpha: float = 1.0, beta: float = 1.0):
        """Initializes with a uniform prior by default (alpha=1, beta=1)."""
        if alpha <= 0 or beta <= 0:
            raise ValueError("Alpha and beta parameters must be positive.")
        self.alpha = alpha
        self.beta = beta

    def update(self, successes: int, failures: int):
        """
        Updates the posterior distribution with new evidence.

        Args:
            successes: The number of successful outcomes.
            failures: The number of failed outcomes.
        """
        if successes < 0 or failures < 0:
            raise ValueError("Successes and failures must be non-negative.")
        self.alpha += successes
        self.beta += failures

    def update_from_self_rating(self, rating: int, max_rating: int = 5):
        """
        Updates the posterior based on a self-rated skill level.
        The rating is converted to a number of successes and failures.
        """
        if not 0 <= rating <= max_rating:
            raise ValueError(f"Rating must be between 0 and {max_rating}.")
        successes = rating
        failures = max_rating - rating
        self.update(successes, failures)

    def update_from_github_stats(self, lines_of_code: int, repo_count: int):
        """A simple heuristic to update from GitHub stats."""
        # This is a placeholder for a more sophisticated model.
        successes = min(lines_of_code // 10000, 5) + min(repo_count // 5, 5)
        self.update(successes, 1)

    def update_from_quiz(self, score: float, max_score: float = 1.0):
        """Updates from a quiz score, normalized to 10 trials."""
        if not 0.0 <= score <= max_score:
            raise ValueError(f"Score must be between 0.0 and {max_score}.")
        successes = int(round(score / max_score * 10))
        failures = 10 - successes
        self.update(successes, failures)

    def update_from_gpt_review(self, quality_score: float):
        """Updates from a GPT-4 code quality review score (0.0 to 1.0)."""
        if not 0.0 <= quality_score <= 1.0:
            raise ValueError("Quality score must be between 0.0 and 1.0.")
        successes = int(round(quality_score * 10))
        failures = 10 - successes
        self.update(successes, failures)

    @property
    def mean(self) -> float:
        """Calculates the mean of the posterior Beta distribution."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def std_dev(self) -> float:
        """Calculates the standard deviation of the posterior Beta distribution."""
        return math.sqrt(
            (self.alpha * self.beta)
            / ((self.alpha + self.beta) ** 2 * (self.alpha + self.beta + 1))
        ) 
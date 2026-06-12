from dataclasses import dataclass

@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 3
    base_delay_seconds: int = 2
    max_delay_seconds: int = 60
    exponential_backoff: bool = True

    def calculate_delay(self, attempt: int) -> int:
        """Deterministically calculate backoff delay."""
        if not self.exponential_backoff:
            return min(self.base_delay_seconds, self.max_delay_seconds)
            
        delay = self.base_delay_seconds * (2 ** max(0, attempt - 1))
        return min(delay, self.max_delay_seconds)

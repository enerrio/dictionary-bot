import argparse
import logging
import os
import signal
import sys
from contextlib import contextmanager

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ExecutionTimeoutError(TimeoutError):
    """Raised when a bot run exceeds the allowed execution time."""


def _handle_timeout(signum, frame) -> None:
    raise ExecutionTimeoutError


@contextmanager
def execution_timeout(timeout_seconds: int):
    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _handle_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def run_bot_with_timeout(timeout_seconds: int) -> bool:
    from bot import post

    try:
        with execution_timeout(timeout_seconds):
            return post.run()
    except ExecutionTimeoutError:
        logging.error("Bot run timed out after %s seconds", timeout_seconds)
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    parser = argparse.ArgumentParser(description="Run the dictionary bot.")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    args = parser.parse_args()
    raise SystemExit(0 if run_bot_with_timeout(args.timeout_seconds) else 1)

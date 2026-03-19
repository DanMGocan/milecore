"""Run all TrueCore.cloud tests with verbose output."""
import sys
import pytest

sys.exit(pytest.main(["tests/", "-v", "--tb=short"]))

"""
Test suite for agent name generator.

Follows TDD: tests written first, then implementation.
"""

import re
from agent_namer import generate_agent_name


class TestAgentNameGenerator:
    """Test cases for the agent_namer module."""

    def test_generate_agent_name_returns_string(self):
        """Test that generate_agent_name returns a string."""
        name = generate_agent_name()
        assert isinstance(name, str)

    def test_generate_agent_name_format(self):
        """Test that agent names follow adjective-animal format."""
        name = generate_agent_name()
        # Should be "word-word" format
        parts = name.split("-")
        assert len(parts) == 2, f"Expected format 'adjective-animal', got '{name}'"

    def test_agent_name_contains_only_alphanumerics_and_hyphen(self):
        """Test that names only contain lowercase alphanumerics and hyphens."""
        # Generate multiple names to increase coverage
        for _ in range(20):
            name = generate_agent_name()
            # Check format: lowercase letters and hyphens only
            assert re.match(r"^[a-z]+-[a-z]+$", name), \
                f"Name '{name}' contains invalid characters"

    def test_agent_name_is_safe(self):
        """Test that names are safe for use as identifiers."""
        for _ in range(20):
            name = generate_agent_name()
            # Should be valid Python identifier (alphanumerics + underscore, but we use hyphens)
            # At minimum, should not have spaces, special chars
            assert " " not in name, f"Name contains spaces: {name}"
            assert not any(c in name for c in "!@#$%^&*()[]{}"), \
                f"Name contains special characters: {name}"
            # Hyphens are allowed (as specified)
            assert name.replace("-", "").isalnum(), \
                f"Name contains invalid characters: {name}"

    def test_agent_name_is_unique_over_time(self):
        """Test that generating multiple names produces variety."""
        names = set()
        for _ in range(100):
            names.add(generate_agent_name())
        # With 10 adjectives and 10 animals, we expect at least 50 unique names
        # out of 100 generations (accounting for randomness)
        assert len(names) > 50, \
            f"Expected >50 unique names from 100 generations, got {len(names)}"

"""
Agent name generator - produces random names in adjective-animal format.

Generates unique, memorable agent names for Claude Agents Orchestrator
instances. Names are safe for use as identifiers and contain only
lowercase letters and hyphens.

Example: "proud-falcon", "swift-eagle", "clever-owl"
"""

import random

ADJECTIVES = [
    "proud", "swift", "clever", "bold", "quiet",
    "eager", "gentle", "nimble", "smart", "strong"
]

ANIMALS = [
    "falcon", "fox", "owl", "eagle", "raven",
    "wolf", "lynx", "tiger", "cobra", "hawk"
]


def generate_agent_name() -> str:
    """
    Generate a random agent name in adjective-animal format.

    Returns:
        str: A randomly generated name like "proud-falcon" or "swift-eagle".
             Format is guaranteed to be lowercase alphanumerics + hyphen only.

    Examples:
        >>> name = generate_agent_name()
        >>> len(name.split("-")) == 2
        True
        >>> name.islower()
        True
    """
    adj = random.choice(ADJECTIVES)
    animal = random.choice(ANIMALS)
    return f"{adj}-{animal}"

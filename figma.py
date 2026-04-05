"""Root-level launcher — run from anywhere in the project."""
import sys
import os

# Add the agent-harness to the path BEFORE importing cli_anything
harness = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figma", "agent-harness")
sys.path.insert(0, harness)

from cli_anything.figma.figma_cli import main

if __name__ == "__main__":
    main()

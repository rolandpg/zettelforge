# Contributing to ZettelForge

Thank you for your interest in contributing to ZettelForge! This document provides guidelines for contributing to the project.

## Development Setup

1. Fork and clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
4. Install in development mode: `pip install -e ".[dev]"`
5. Run tests to verify your setup: `pytest tests/ -v`

No external services (Ollama, TypeDB, Docker) are required for development. ZettelForge defaults to SQLite for storage and fastembed for in-process embeddings.

## Development Workflow

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Run tests: `pytest tests/ -v`
4. Run linting: `ruff check src/zettelforge/`
5. Run formatting: `black src/zettelforge/`
6. Commit with clear messages
7. Push and create a pull request

## Where to contribute

All of `src/zettelforge/` is MIT-licensed and open to contributions.
Feature ideas, bug fixes, documentation, benchmarks — all welcome.

If your contribution needs TypeDB or OpenCTI, open an issue to discuss.
We keep the extension boundary clear so contributors know their work
will always remain open source.

## Code Style

- Follow PEP 8
- Use type hints where possible
- Document functions with docstrings
- Keep functions focused and small
- Write tests for new functionality

## Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Tests that require extension features should use the `enable_extensions` fixture from `tests/conftest.py`
- Use meaningful test names that describe behavior

## Commit Messages

Use clear, descriptive commit messages:

- `feat: Add entity extraction for CVE patterns`
- `fix: Correct vector similarity calculation`
- `docs: Update API reference`
- `test: Add tests for recall_cve method`

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure CI passes
4. Request review from maintainers
5. Address review feedback

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions or ideas
- Check existing issues before creating new ones

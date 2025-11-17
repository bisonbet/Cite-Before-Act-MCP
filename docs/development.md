# Development

This guide covers setting up a development environment and contributing to Cite-Before-Act MCP.

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/bisonbet/Cite-Before-Act-MCP.git
cd Cite-Before-Act-MCP
```

### 2. Install Development Dependencies

```bash
pip install -e ".[dev]"
```

This installs the package in editable mode with development dependencies including:
- `pytest` - Testing framework
- `black` - Code formatter
- `ruff` - Linter
- `mypy` - Type checker

### 3. Set Up Pre-commit Hooks (Optional)

```bash
pip install pre-commit
pre-commit install
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_detection.py
```

### Run with Coverage

```bash
pytest --cov=cite_before_act --cov-report=html
```

View coverage report: `open htmlcov/index.html`

### Run with Verbose Output

```bash
pytest -v
```

## Code Quality

### Format Code

```bash
black .
```

### Lint Code

```bash
ruff check .
```

### Fix Linting Issues Automatically

```bash
ruff check --fix .
```

### Type Checking

```bash
mypy cite_before_act/
```

## Project Structure

See [Architecture](architecture.md) for detailed project structure.

Key files for development:
- `cite_before_act/` - Core library code
- `server/` - Proxy server implementation
- `tests/` - Test suite
- `examples/` - Usage examples
- `config/` - Configuration management

## Making Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Write clean, well-documented code
- Follow existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run tests
pytest

# Check formatting
black --check .

# Check linting
ruff check .

# Check types
mypy cite_before_act/
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add your feature description"
```

Use conventional commit messages:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test changes
- `chore:` - Maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Contributing Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Write docstrings for public functions and classes
- Keep functions focused and single-purpose
- Use descriptive variable names

### Testing

- Write tests for all new functionality
- Maintain or improve code coverage
- Use pytest fixtures for common test setup
- Test both success and error cases

### Documentation

- Update README if adding user-facing features
- Add docstrings to new functions/classes
- Update relevant documentation in `docs/`
- Include examples for new features

### Pull Request Process

1. Ensure all tests pass
2. Update documentation
3. Add description of changes to PR
4. Link related issues
5. Request review from maintainers

## Building and Testing the Proxy

### Test Locally with Claude Desktop

1. Make your changes
2. Update your Claude Desktop config to point to your local copy
3. Restart Claude Desktop
4. Test functionality

### Test Standalone Server

```bash
# stdio mode
python -m server.main --transport stdio

# HTTP mode
python -m server.main --transport http --port 8000
```

## Release Process

Releases are managed by maintainers:

1. Update version in `pyproject.toml`
2. Update CHANGELOG
3. Create git tag: `git tag v1.0.0`
4. Push tag: `git push origin v1.0.0`
5. Create GitHub release
6. Publish to PyPI (if applicable)

## Getting Help

- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions
- **Questions**: Check existing documentation first

## License

By contributing, you agree that your contributions will be licensed under the AGPL-3.0 License.

## Acknowledgments

Thank you for contributing to Cite-Before-Act MCP!

## Next Steps

- [Architecture](architecture.md) - Understand the codebase
- [Advanced Usage](advanced-usage.md) - Library integration examples

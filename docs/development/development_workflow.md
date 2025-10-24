# Development Workflow

## Development Environment Setup

### Prerequisites
- Raspberry Pi 5 with 16GB RAM (or development machine)
- Raspberry Pi OS (64-bit) Bookworm or later
- Python 3.11+
- Git 2.40+
- VS Code with Python extension (recommended)

### Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd ai_home_security_notifications

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install
```

### IDE Configuration
**VS Code Settings (.vscode/settings.json):**
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/.pytest_cache": true
    }
}
```

### Environment Variables
Create `.env` file in project root:
```bash
# Development settings
DEBUG=true
LOG_LEVEL=DEBUG
MOCK_CAMERA=true
MOCK_NOTIFICATIONS=true

# Database
DATABASE_URL=sqlite:///dev.db

# API Keys (use test keys in development)
TWILIO_ACCOUNT_SID=test_sid
TWILIO_AUTH_TOKEN=test_token
SMTP_PASSWORD=test_password
```

## Testing Strategy

### Unit Testing
- **Framework:** pytest
- **Coverage Target:** >80%
- **Location:** `tests/unit/`
- **Naming:** `test_<module_name>.py`

```bash
# Run unit tests
pytest tests/unit/

# Run with coverage
pytest --cov=src tests/unit/

# Run specific test
pytest tests/unit/test_motion_detection.py::test_motion_detection_basic
```

### Integration Testing
- **Framework:** pytest with test containers
- **Location:** `tests/integration/`
- **Scope:** API endpoints, database operations, external services

```bash
# Run integration tests
pytest tests/integration/

# Run with test database
pytest --test-db tests/integration/
```

### Hardware-in-Loop Testing
- **Framework:** Custom test harness
- **Location:** `tests/hardware/`
- **Scope:** Camera integration, motion detection, AI inference

```bash
# Run hardware tests (requires Pi 5)
pytest tests/hardware/ --hardware-tests
```

### Performance Testing
- **Framework:** pytest-benchmark
- **Location:** `tests/performance/`
- **Scope:** AI inference speed, video processing, memory usage

```bash
# Run performance tests
pytest tests/performance/ --benchmark-only
```

### Test Data Management
- **Location:** `tests/data/`
- **Types:** Sample videos, test images, mock configurations
- **Management:** Git LFS for large files

## CI/CD Pipeline

### GitHub Actions Workflow
**File:** `.github/workflows/ci.yml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run linting
        run: |
          flake8 src/
          black --check src/
          mypy src/
      - name: Run tests
        run: pytest --cov=src tests/
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Deployment Pipeline
**Stages:**
1. **Build:** Package application and dependencies
2. **Test:** Run full test suite
3. **Security Scan:** Run security vulnerability scans
4. **Deploy:** Deploy to Pi 5 (staging/production)

### Quality Gates
- **Code Coverage:** >80%
- **Linting:** No critical issues
- **Security:** No high-severity vulnerabilities
- **Performance:** Tests pass within time limits

## Git Workflow

### Branching Strategy
```
main (production)
├── develop (integration)
│   ├── feature/epic-1-hardware-setup
│   ├── feature/epic-2-motion-detection
│   └── feature/epic-3-ai-classification
├── hotfix/critical-bug-fix
└── release/v1.0.0
```

### Branch Naming Convention
- **Features:** `feature/epic-<number>-<description>`
- **Bugfixes:** `bugfix/<issue-number>-<description>`
- **Hotfixes:** `hotfix/<critical-issue>`
- **Releases:** `release/v<version>`

### Commit Message Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Build process or auxiliary tool changes

**Examples:**
```
feat(motion): add zone-based motion detection
fix(camera): resolve camera initialization timeout
docs(api): update API documentation for v1.2
```

### Pull Request Process
1. **Create Branch:** From `develop` branch
2. **Develop Feature:** Implement changes with tests
3. **Run Tests:** Ensure all tests pass locally
4. **Create PR:** Against `develop` branch
5. **Code Review:** At least one approval required
6. **Merge:** Squash and merge to `develop`

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes
```

## Code Quality Standards

### Linting and Formatting
```bash
# Run linting
flake8 src/ tests/

# Format code
black src/ tests/

# Type checking
mypy src/

# Security scanning
bandit -r src/
```

### Code Style Guidelines
- **PEP 8:** Python style guide compliance
- **Docstrings:** Google style docstrings
- **Type Hints:** Use type hints for all functions
- **Error Handling:** Comprehensive error handling
- **Logging:** Use structured logging

### Documentation Standards
- **Code Comments:** Explain complex logic
- **API Documentation:** Auto-generated from docstrings
- **README Updates:** Keep README current
- **Architecture Decisions:** Document in ADRs

## Development Tools

### Pre-commit Hooks
**File:** `.pre-commit-config.yaml`
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v0.950
    hooks:
      - id: mypy
```

### Development Scripts
**File:** `scripts/dev-setup.sh`
```bash
#!/bin/bash
# Development environment setup script

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Run initial tests
pytest tests/unit/

echo "Development environment ready!"
```

### Debugging Tools
- **pdb:** Python debugger
- **logging:** Structured logging with different levels
- **profiling:** cProfile for performance analysis
- **memory profiling:** memory_profiler for memory usage

### Monitoring and Observability
- **Application Metrics:** Prometheus metrics
- **Logging:** Structured JSON logging
- **Tracing:** OpenTelemetry for distributed tracing
- **Health Checks:** Health check endpoints

## Release Process

### Version Management
- **Semantic Versioning:** MAJOR.MINOR.PATCH
- **Changelog:** Keep CHANGELOG.md updated
- **Git Tags:** Tag releases in Git

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version bumped
- [ ] Changelog updated
- [ ] Security scan passed
- [ ] Performance tests passed
- [ ] Release notes prepared

### Deployment Process
1. **Create Release Branch:** From `develop`
2. **Run Full Test Suite:** All environments
3. **Security Scan:** Vulnerability assessment
4. **Performance Test:** Load and stress testing
5. **Deploy to Staging:** Test deployment
6. **User Acceptance Testing:** Stakeholder approval
7. **Deploy to Production:** Production deployment
8. **Monitor:** Post-deployment monitoring

## Troubleshooting

### Common Issues
- **Import Errors:** Check virtual environment activation
- **Test Failures:** Verify test data and dependencies
- **Performance Issues:** Profile code and optimize
- **Memory Leaks:** Use memory profiling tools

### Development Resources
- **Documentation:** `/docs/` directory
- **API Reference:** Auto-generated from docstrings
- **Troubleshooting Guide:** `/docs/troubleshooting.md`
- **FAQ:** `/docs/faq.md`

### Getting Help
- **Issues:** GitHub Issues for bug reports
- **Discussions:** GitHub Discussions for questions
- **Code Review:** Request reviews from team members
- **Documentation:** Check existing documentation first

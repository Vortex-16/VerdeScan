# 🤝 Contributing to Verde Scan

Thank you for your interest in contributing to Verde Scan! This document provides guidelines and instructions for contributing.

---

## 📋 Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Making Changes](#making-changes)
5. [Testing](#testing)
6. [Submitting Changes](#submitting-changes)
7. [Style Guidelines](#style-guidelines)

---

## 📜 Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect differing viewpoints and experiences

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Git
- Basic understanding of FastAPI and PyTorch
- Familiarity with computer vision concepts

### Areas for Contribution

- 🐛 Bug fixes
- ✨ New features
- 📝 Documentation improvements
- 🧪 Test coverage
- 🎨 UI/UX enhancements
- ⚡ Performance optimizations

---

## 💻 Development Setup

1. **Fork the Repository**
   - Click "Fork" on GitHub
   - Clone your fork locally

2. **Set Up Development Environment**
```bash
git clone https://github.com/YOUR_USERNAME/verde_scan.git
cd verde_scan
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov black flake8
```

3. **Create a Branch**
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

---

## 🔨 Making Changes

### Branch Naming Convention

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `test/` - Test additions/changes
- `refactor/` - Code refactoring

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

**Example:**
```
feat: Add batch processing endpoint

- Implement /api/process-batch endpoint
- Add queue management for multiple images
- Update documentation

Closes #123
```

---

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Tests
```bash
pytest tests/test_forest_processor.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=. --cov-report=html
```

### Test Checklist

- [ ] All existing tests pass
- [ ] New tests added for new features
- [ ] Code coverage maintained or improved
- [ ] Manual testing completed
- [ ] Edge cases considered

---

## 📤 Submitting Changes

### Pull Request Process

1. **Update Your Branch**
```bash
git fetch upstream
git rebase upstream/main
```

2. **Run Tests**
```bash
pytest tests/
python test_system.py
```

3. **Format Code**
```bash
black .
flake8 .
```

4. **Push Changes**
```bash
git push origin feature/your-feature-name
```

5. **Create Pull Request**
   - Go to GitHub
   - Click "New Pull Request"
   - Fill in the template
   - Link related issues

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Tests pass locally
- [ ] New tests added
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes
- [ ] Commit messages are clear

## Related Issues
Closes #123
```

---

## 🎨 Style Guidelines

### Python Code Style

- Follow PEP 8
- Use Black for formatting
- Maximum line length: 100 characters
- Use type hints

**Example:**
```python
from typing import List, Optional

def process_image(
    image_path: str,
    threshold: float = 0.5
) -> Optional[List[dict]]:
    """
    Process a single image.
    
    Args:
        image_path: Path to the image file
        threshold: Detection threshold (0.0-1.0)
    
    Returns:
        List of detections or None if processing fails
    """
    # Implementation
    pass
```

### Documentation Style

- Use clear, concise language
- Include code examples
- Add docstrings to all functions
- Update README when needed

### API Design

- RESTful conventions
- Clear endpoint names
- Proper HTTP status codes
- Comprehensive error messages

---

## 🔍 Code Review Process

### What We Look For

- ✅ Code quality and readability
- ✅ Test coverage
- ✅ Documentation completeness
- ✅ Performance considerations
- ✅ Security implications
- ✅ Backward compatibility

### Review Timeline

- Initial review: 2-3 days
- Follow-up reviews: 1-2 days
- Merge: After approval from maintainers

---

## 🐛 Reporting Bugs

### Bug Report Template

```markdown
**Describe the bug**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What should happen

**Screenshots**
If applicable

**Environment:**
- OS: [e.g., Ubuntu 20.04]
- Python version: [e.g., 3.9]
- Verde Scan version: [e.g., 1.0.0]

**Additional context**
Any other relevant information
```

---

## 💡 Feature Requests

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
Clear description of the problem

**Describe the solution you'd like**
What you want to happen

**Describe alternatives you've considered**
Other solutions you've thought about

**Additional context**
Any other relevant information
```

---

## 📚 Resources

### Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [PyTorch Docs](https://pytorch.org/docs/)
- [OpenCV Docs](https://docs.opencv.org/)

### Learning Resources
- [Python Best Practices](https://docs.python-guide.org/)
- [Git Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows)
- [Testing in Python](https://realpython.com/pytest-python-testing/)

---

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

---

## 📞 Getting Help

- 💬 GitHub Discussions
- 🐛 GitHub Issues
- 📧 Email maintainers

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Verde Scan! 🌲**

# Python Environment & Pathing Configuration

## Overview

This project uses **UV** (via `uv` and `uvx`) as the modern, fast Python package manager, replacing traditional `pip` usage.

## Python Best Practices

### ✅ DO: Use UV for Package Management

```bash
# Install packages using UV
uv pip install package-name

# Run tools with uvx (doesn't require installation)
uvx ruff check .

# Create virtual environments
uv venv

# Install from requirements
uv pip install -r requirements.txt
```

### ❌ DON'T: Use pip directly

```bash
# AVOID - Don't use pip
pip install package-name
python -m pip install package-name
```

## Why UV?

- **10-100x faster** than pip for package installation
- **Better dependency resolution** - more reliable and consistent
- **Drop-in replacement** for pip with familiar syntax
- **Built in Rust** - memory safe and highly performant
- **Better caching** - faster reinstalls and reduced network usage

## Container Environment PATH

The development container has the following PATH precedence (first = highest priority):

```
1. /home/developer/.venv/bin          # Python virtual environment
2. /home/developer/.local/bin         # User-installed tools (pipx, uv)
3. /go/bin                            # Go binaries
4. /go/bin                            # GOROOT binaries
5. /usr/local/share/npm-global/bin    # NPM global packages
6. [System PATH]                      # Standard system binaries
```

## Pre-installed Python Tools

### UV - Package Manager
```bash
# UV is installed via pipx and available globally
uv --version

# UV venv is pre-created at /home/developer/.venv
echo $VIRTUAL_ENV  # /home/developer/.venv
```

### OR-Tools - Route Optimization
```bash
# OR-Tools is pre-installed in the venv for route optimization
python3 -c "from ortools.constraint_solver import pywrapcp; print('OR-Tools ready!')"
```

## Virtual Environment

A Python virtual environment is automatically created and activated:

- **Location:** `/home/developer/.venv`
- **Activated by default** in all shells
- **Managed by UV** for faster package operations

## Using Python Packages

### Installing New Packages

```bash
# Install into the active venv
uv pip install requests

# Install specific version
uv pip install "requests==2.31.0"

# Install from requirements.txt
uv pip install -r requirements.txt
```

### Running Python Scripts

```bash
# Python automatically uses the venv
python3 script.py

# Or be explicit
/home/developer/.venv/bin/python3 script.py
```

### Running Tools Without Installation (uvx)

```bash
# Run tools directly without installing
uvx ruff check .
uvx black .
uvx pytest

# Run specific versions
uvx ruff@0.1.0 check .
```

## Project-Specific Environments

If you need a project-specific environment:

```bash
# Create project venv
cd /workspace/my-project
uv venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

## Common Workflows

### Adding a New Python Dependency

```bash
# Install the package
uv pip install new-package

# If using requirements.txt, add it
echo "new-package==1.2.3" >> requirements.txt
```

### Upgrading Packages

```bash
# Upgrade a specific package
uv pip install --upgrade package-name

# Upgrade all packages (use with caution)
uv pip install --upgrade -r requirements.txt
```

### Listing Installed Packages

```bash
# List all packages in current environment
uv pip list

# Show package details
uv pip show package-name
```

## Troubleshooting

### Package Not Found
```bash
# Make sure you're in the venv
echo $VIRTUAL_ENV  # Should show /home/developer/.venv

# Check Python location
which python3  # Should be /home/developer/.venv/bin/python3
```

### Import Errors
```bash
# Verify package is installed in the active venv
uv pip list | grep package-name

# Try installing explicitly
uv pip install package-name
```

### PATH Issues
```bash
# Verify PATH order
echo $PATH

# Should start with:
# /home/developer/.venv/bin:/home/developer/.local/bin:...
```

## Best Practices Summary

1. ✅ Always use `uv` instead of `pip`
2. ✅ Use `uvx` for one-off tool runs
3. ✅ Keep the default venv activated for project work
4. ✅ Document dependencies in `requirements.txt` or `pyproject.toml`
5. ❌ Avoid installing packages globally with sudo
6. ❌ Avoid mixing pip and uv in the same environment
7. ❌ Don't modify system Python packages

## References

- [UV Documentation](https://github.com/astral-sh/uv)
- [UV Pip Compatibility](https://github.com/astral-sh/uv#pip-compatibility)
- [Python Virtual Environments](https://docs.python.org/3/library/venv.html)

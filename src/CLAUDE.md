# Development Guidelines (Python + General)

## TDD Workflow

**Red-Green-Refactor:**
1. Write failing test first (verify it fails)
2. Write minimal code to pass
3. Refactor while keeping tests green

**Test naming:** `test_<action>_<condition>_<result>` in snake_case
- Example: `test_divide_by_zero_raises_value_error`
- Describe behavior, not implementation

## Communication Style

**DO:**
- State limitations immediately
- Ask for clarification when ambiguous
- Lead with key information, then details
- Cite sources for claims
- Test before claiming completion

**DON'T:**
- Praise or flatter
- Use "please/thank you" in technical exchanges
- Make assumptions - ask instead

## Code Quality

**Principles:** Follow PEP 8, use type hints, keep functions small, prefer composition over inheritance

**Environment:**
- Command runner: `just` (define tasks in justfile)
- Dev containers: `.devcontainer/` for reproducible environment

**Review perspectives:**
1. Domain Expert - correct business logic?
2. Concurrency - races, thread safety?
3. Security - validated inputs, no injection?
4. Junior Dev - clear, documented, good errors?
5. Architect - testable, clear boundaries?

**Code markers:** `TODO`, `FIXME`, `NOTE`, `HACK`

### MCP Servers (check availability first)

**mcp-tasks:** Sync task lists, track TODOs across sessions

**chroma:** Vector storage for persistent knowledge
- Store: ADRs, error solutions, code patterns, conventions
- **CRITICAL:** Distill to essentials before storing (avoid context bloat)
- Max info in min tokens

### IoC: Default Factory Pattern

Two constructors:
1. `__init__()` - testing constructor, accepts mocks
2. `create()` - classmethod, creates real dependencies (mark `# pragma: no cover`)

Use `typing.Protocol` for dependencies, never instantiate in `__init__`

## Error Handling

**Constants:** Define error messages as constants, use in both code and tests
- Ensures consistency, reduces magic strings
- Tests verify exact messages

```python
# error_messages.py
ERROR_MSG.DIVIDE_BY_ZERO = "Cannot divide by zero"

# Use
raise ValueError(ERROR_MSG.DIVIDE_BY_ZERO)

# Test
with pytest.raises(ValueError, match=ERROR_MSG.DIVIDE_BY_ZERO):
```

## File Creation

**DON'T:** Create STATUS.md, REFACTORING.md, architecture docs unless requested

**DO:** Suggest first, summarize in chat, create code/tests/config only

## Problem Solving

When encountering issues:
1. Don't workaround blindly
2. Prompt with options: fix properly, workaround, disable test, alternatives
3. Cost/benefit analysis: pros/cons, tech debt, effort
4. Document decision

## Questions to Ask

**New feature:** acceptance criteria, performance needs, error cases, security, logging, dependencies, testing, error messages, mcp-tasks/chroma usage

**Component design:** dependencies, interfaces, logging context, error conditions, persistent data

**Problems:** fix vs workaround, pros/cons, tech debt, disable test, alternatives

**Stuck:** what info needed, which approach, speed vs correctness

## Limitations

- Cannot run tests without instruction
- Cannot verify runtime without execution
- Cannot access external APIs without config
- Limited to static analysis
- MCP servers may not be available

---

# Python Development

## Tooling

- Python 3, UV package manager, pytest, ruff, structlog
- Gherkin for acceptance tests (pytest-bdd/behave)

## Structure

```
src/package_name/
  log_messages.py      # Log constants
  error_messages.py    # Error constants
  module.py
  test_module.py       # Unit tests co-located
tests/
  integration/
  acceptance/features/
```

## Logging (structlog)

**Why:** Native structured logging, context binding, thread-safe, flexible processors

```python
# log_messages.py
from dataclasses import dataclass

@dataclass(frozen=True)
class LogMessages:
    USER_CREATED = "user_created"
    USER_LOGIN_FAILED = "user_login_failed"

LOG_MSG = LogMessages()

# Usage
import structlog
logger = structlog.get_logger()
logger.info(LOG_MSG.USER_CREATED, username=username, user_id=user.id)

# Test
def test_logs_creation(caplog):
    create_user("alice")
    assert any(r.msg == LOG_MSG.USER_CREATED for r in caplog.records)

# Config
# Dev: structlog.dev.ConsoleRenderer()
# Prod: structlog.processors.JSONRenderer()
```

## Error Constants

```python
# error_messages.py
@dataclass(frozen=True)
class ErrorMessages:
    DIVIDE_BY_ZERO = "Cannot divide by zero"
    INVALID_EMAIL = "Invalid email format"

ERROR_MSG = ErrorMessages()

# Use
def divide(n: float, d: float) -> float:
    if d == 0:
        raise ValueError(ERROR_MSG.DIVIDE_BY_ZERO)
    return n / d

# Test
def test_divide_by_zero():
    with pytest.raises(ValueError, match=ERROR_MSG.DIVIDE_BY_ZERO):
        divide(10, 0)
```

## IoC Pattern

```python
from typing import Protocol
import structlog

class UserRepository(Protocol):
    def save(self, user: User) -> None: ...
    def find_by_id(self, user_id: str) -> User | None: ...

class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        email_service: EmailService,
        logger: structlog.BoundLogger,
    ) -> None:
        """Testing constructor - inject dependencies."""
        self._user_repo = user_repo
        self._email_service = email_service
        self._logger = logger
    
    @classmethod
    def create(cls, db: DatabaseConnection) -> "UserService":  # pragma: no cover
        """Default factory - create real dependencies."""
        return cls(
            SQLUserRepository(db),
            SMTPEmailService(),
            structlog.get_logger(),
        )
    
    def register_user(self, username: str, email: str) -> User:
        user = User(username, email)
        self._user_repo.save(user)
        self._email_service.send_welcome(email)
        self._logger.info(LOG_MSG.USER_CREATED, username=username)
        return user

# Test
def test_register_saves():
    mock_repo = Mock(spec=UserRepository)
    mock_email = Mock(spec=EmailService)
    mock_logger = Mock(spec=structlog.BoundLogger)
    
    service = UserService(mock_repo, mock_email, mock_logger)
    user = service.register_user("alice", "alice@example.com")
    
    mock_repo.save.assert_called_once()
    mock_email.send_welcome.assert_called_once_with("alice@example.com")
```

## Common Patterns

**Fixtures:**
```python
@pytest.fixture
def user_service(mock_user_repo, mock_email, mock_logger):
    return UserService(mock_user_repo, mock_email, mock_logger)
```

**Type hints:**
```python
from typing import Protocol, Optional

class DataStore(Protocol):
    def save(self, key: str, value: str) -> None: ...
    def get(self, key: str) -> Optional[str]: ...

def process(items: list[str], store: DataStore) -> bool:
    for item in items:
        store.save(item, transform(item))
    return True
```

## Commands (justfile)

```justfile
test:
    uv run pytest

test-cov:
    uv run pytest --cov=src --cov-report=html

lint:
    uv run ruff check .

fmt:
    uv run ruff format .

check: lint test
```

## Dependencies

```bash
uv add structlog
uv add --dev pytest pytest-bdd ruff mypy
```
# Contributing to swiss-housing-mcp

[🇩🇪 Deutsche Version](CONTRIBUTING.de.md)

Thank you for your interest in contributing to `swiss-housing-mcp`! This project is part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide).

---

## Ways to Contribute

### Report a Bug

Open a [GitHub Issue](https://github.com/malkreide/swiss-housing-mcp/issues) and include:

- A clear description of the problem
- Steps to reproduce (ideally with the EGID/EWID or address involved)
- Expected vs. actual behaviour
- Python version and OS

### Suggest a New Canton Dump or Data Source

The GWR/RegBL dumps are published per canton. If you find a canton or dataset that should be supported:

1. Open an issue with the title `[Data] <canton/dataset>: <short description>`
2. Include a sample source URL and a description of the data it contains
3. Ideally, verify it against the live source before submitting

### Improve Documentation

Typos, unclear explanations, or missing examples are always welcome as pull requests — no issue needed.

### Contribute Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Follow the code style (Ruff for linting/formatting)
4. Add or update tests in `tests/`
5. Run the test suite before submitting: `PYTHONPATH=src pytest tests/ -m "not live"`
6. Submit a pull request with a clear description of your changes

---

## Development Setup

```bash
git clone https://github.com/malkreide/swiss-housing-mcp.git
cd swiss-housing-mcp
pip install -e ".[dev]"
```

**Run tests:**

```bash
# Unit tests (no network required, respx-mocked)
PYTHONPATH=src pytest tests/ -m "not live"

# Integration tests (live upstream)
PYTHONPATH=src pytest tests/ -m "live"
```

**Lint and format:**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

---

## Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | When to use |
|---|---|
| `feat:` | New tool or new data source |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `test:` | Adding or updating tests |
| `refactor:` | Code restructuring without behaviour change |
| `chore:` | Build, dependencies, CI |

---

## Code of Conduct

Be respectful and constructive. This is a small open-source project maintained in spare time — patience is appreciated.

---

## The live suite: when it runs, and who sees a red result

**Cadence:** daily at 03:29 UTC, plus on demand via *Actions → CI → Run
workflow*. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

**Who sees it:** A red run opens an issue labelled `upstream` and the stable title “Live-Tests gegen public.madd.bfs.admin.ch rot (<Datum>)”. A second red run recognises the open issue by its title prefix and appends to that same thread rather than opening a second one. Once the suite is green again, the issue closes itself.

**Three answers, not two.** `scripts/classify_live_run.py` reads the JUnit XML rather than
the exit code and separates `clear` (ran, green), `finding` (ran, something
fell) and `unknown` (did not run — install failed, nothing collected,
everything skipped). An `unknown` never closes an issue: closing would claim a
comparison that never happened.

**A red live run does not necessarily mean *our* bug.** It means the contract
with the source has changed, or the source is down. Both belong seen; only the
first belongs fixed. Please read the run before disabling the job — that is how
this check dies, and it is the only one in the repository that can contradict a
wrong assumption about public.madd.bfs.admin.ch. Every other test asserts against a fixture, and
the fixture was written from the same assumption as the code.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).

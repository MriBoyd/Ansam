# Contributing to Ansam (MCP Discovery Server)

Welcome! 👋 Thank you for considering contributing to **Ansam MCP Discovery Server**. We are excited to welcome new contributors, whether you are fixing a typo, resolving your very first open-source issue, or adding a complex retrieval feature.

This guide will walk you through setting up your environment, picking up an issue, and submitting a pull request.

---

## 🧭 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Finding a Good First Issue](#finding-a-good-first-issue)
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Running Qdrant](#running-qdrant)
- [Project Architecture](#project-architecture)
- [Running Tests](#running-tests)
- [Code Style and Formatting](#code-style-and-formatting)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [AI Usage Guidelines](#ai-usage-guidelines)
- [Need Help?](#need-help)

---

## 📜 Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free environment for everyone. Please be respectful, constructive, and supportive in all discussions, issues, and pull requests.

---

## 🎯 Finding a Good First Issue

If you are new to the project or open source in general, start with issues tagged:

- [`good first issue`](https://github.com/MriBoyd/Ansam/labels/good%20first%20issue): Well-defined, scoped tasks with clear instructions.
- [`help wanted`](https://github.com/MriBoyd/Ansam/labels/help%20wanted): Areas where the community would love extra hands.
- [`documentation`](https://github.com/MriBoyd/Ansam/labels/documentation): Improvements to guides, docstrings, or examples.

Before starting work on an issue, please leave a comment on the issue asking to be assigned, so multiple people don't work on the same task simultaneously.

---

## 📋 Prerequisites

- **Python 3.10+** (Python 3.10, 3.11, or 3.12 recommended)
- **Git**
- **Docker** (to run the Qdrant vector database)
- Optional: [`uv`](https://docs.astral.sh/uv/) for blazing-fast dependency installation

---

## 🛠️ Local Development Setup

### 1. Fork and Clone the Repository

```bash
# Fork the repo on GitHub first, then clone your fork:
git clone https://github.com/<your-username>/Ansam.git
cd Ansam

# Add the upstream remote
git remote add upstream https://github.com/MriBoyd/Ansam.git
```

### 2. Set Up a Virtual Environment

**Using `venv`:**
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e ".[dev]"
```

**Or using `uv`:**
```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -e ".[dev]"
```

### 3. Environment Variables

Copy the example environment configuration:
```bash
cp .env.example .env
```
Inspect `.env` and adjust any ports or parameters if needed.

---

## 🐳 Running Qdrant

Ansam requires a running instance of **Qdrant** for hybrid vector search.

**Using Docker:**
```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

**Using Docker Compose:**
```bash
docker-compose up -d
```

Verify that Qdrant is running by visiting [http://localhost:6333/dashboard](http://localhost:6333/dashboard) in your browser.

---

## 🏗️ Project Architecture

Here is a quick tour of the repository to help you orient yourself:

| Path | Purpose |
|---|---|
| `src/mcp_server_production.py` | Main entry point for the discovery server (FastMCP interface). |
| `src/hybrid_searcher.py` | Core hybrid search engine (BM25 + Dense + ColBERT late-interaction). |
| `src/mcp_registry_manager.py` | Discovers tools across stdio/SSE/HTTP transports and updates the registry. |
| `src/circuit_breaker.py` | Fault tolerance implementation preventing cascading downstream failures. |
| `src/rate_limiter.py` | Token bucket rate limiting (global and per-server). |
| `src/auth_manager.py` | Token and OAuth2 credential manager for proxied servers. |
| `src/config.py` | Central configuration values and environment variable overrides. |
| `src/scripts/index_tools.py` | Ingestion script that parses tools and creates Qdrant vector indexes. |
| `tests/` | Comprehensive test suite for unit tests and benchmarks. |

---

## 🧪 Running Tests

Always make sure existing tests pass before submitting your changes:

```bash
# Run all tests
pytest

# Run a specific test module
pytest tests/test_circuit_breaker.py
pytest tests/test_auth_manager.py
pytest tests/test_rate_limiter.py
pytest tests/test_config.py

# Run with verbose output
pytest -v
```

If you add a new feature or fix a bug, please write corresponding tests in the `tests/` directory!

---

## 🎨 Code Style and Formatting

We adhere to standard Python PEP 8 conventions:

- Use clear, descriptive variable and function names.
- Provide type hints for public function signatures.
- Keep functions modular and focused.
- Preserve existing docstrings and add explanations for non-obvious logic.

---

## 🚀 Submitting a Pull Request

1. **Create a branch** for your work:
   ```bash
   git checkout -b feat/my-new-feature
   # or
   git checkout -b fix/issue-123
   ```
2. **Make your changes** and write corresponding tests.
3. **Run tests** and verify everything passes:
   ```bash
   pytest
   ```
4. **Commit with a clear message** using [Conventional Commits](https://www.conventionalcommits.org/):
   ```bash
   git commit -m "feat: Add health check endpoint to production server"
   # or
   git commit -m "fix: Handle missing Qdrant connection gracefully with retry"
   ```
5. **Push your branch** to your fork:
   ```bash
   git push origin feat/my-new-feature
   ```
6. **Open a Pull Request** against the `main` branch of `MriBoyd/Ansam`. Fill out the PR template completely.

---

## 🤖 AI Usage Guidelines

We welcome the responsible use of AI tools (such as Claude, ChatGPT, Gemini, GitHub Copilot) to assist with code, documentation, and tests. However:

- **Disclose AI assistance** in your pull request description.
- **Review and understand** all generated code before opening a PR. You are responsible for the correctness, safety, and maintainability of the submitted code.
- **Ensure tests pass** and edge cases are handled. Unchecked or hallucinated code will be rejected.

---

## 💬 Need Help?

If you have questions, encounter an issue setting up, or need guidance on an implementation detail:
- Open a question on GitHub Issues.
- Join the conversation on the issue thread you are working on.

Thank you for helping make Ansam better! Happy coding! 🚀

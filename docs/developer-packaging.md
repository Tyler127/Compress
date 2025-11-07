# Compressy Developer Packaging Guide

This document walks through everything a maintainer needs to know to build, test, install, and distribute the `compressy` package. It assumes you are working from a local clone of the repository.

---

## 1. Packaging Overview

- `compressy` is published as a standard Python package managed by `pyproject.toml` (PEP 621 compliant).
- Builds produce two distribution artifacts inside `dist/`:
  - **Source distribution (sdist)** — `compressy-<version>.tar.gz`
  - **Built wheel** — `compressy-<version>-py3-none-any.whl`
- The CLI entry point is registered as `compressy` via `[project.scripts]` in `pyproject.toml`; installing the package puts a `compressy` executable on the user’s PATH.

When someone runs `pip install compressy`, pip contacts the Python Package Index (PyPI), downloads the recorded wheel/sdist that we uploaded, and installs it into their environment. Nothing is automatic: maintainers must manually upload the build outputs to PyPI (or TestPyPI) after each release.

---

## 2. Prerequisites

1. **Python 3.13+** (project runtime requirement)
2. **Virtual environment tools** (recommended): `python -m venv .venv`
3. **Build utilities** (install once inside your dev environment):
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install build twine
   ```
4. **PyPI credentials** (username + API token) for publishing to the official index. For test uploads, create a TestPyPI account and token at <https://test.pypi.org>.

---

## 3. Local Setup

```powershell
cd C:\Repos\Compressy
python -m venv .venv
.\.venv\Scripts\activate           # Windows
# source .venv/bin/activate          # macOS/Linux

python -m pip install -r requirements-dev.txt
python -m pip install -e .           # editable install for CLI & imports
```

The editable install wires `compressy` into your environment so running `compressy --help` or `python -m compressy` uses the local sources.

---

## 4. Daily Development Commands

```powershell
# Run all tests
pytest

# Run linters/formatters
black compressy tests
isort compressy tests
flake8 compressy tests
pylint compressy
mypy compressy

# Optional coverage report
pytest --cov=compressy --cov-report=html
```

These commands are also listed in `README.md` under “Development”.

---

## 5. Building Distributions

1. **Update release metadata**
   - Bump the version in `pyproject.toml` (`[project].version`).
   - Mirror the version in `compressy/__init__.py` (`__version__`).
   - Document changes in `CHANGELOG.md`.

2. **Clean previous artifacts** (optional but good hygiene):
   ```powershell
   rmdir /s /q build dist compressy.egg-info
   ```

3. **Build the package**:
   ```powershell
   python -m build
   ```

   This command creates both `dist/compressy-<version>.tar.gz` and `dist/compressy-<version>-py3-none-any.whl`.

4. **Inspect the contents**:
   ```powershell
   tar -tzf dist/compressy-<version>.tar.gz | more   # optional
   python -m zipfile -l dist/compressy-<version>-py3-none-any.whl
   ```

---

## 6. Local Smoke Test of Built Artifacts

After building, install the wheel into a clean environment to ensure the published artifact works end-to-end.

```powershell
python -m pip install --force-reinstall --no-deps dist\compressy-<version>-py3-none-any.whl

# Basic functionality checks
compressy --help
compressy --view-stats

# Remove when done
python -m pip uninstall -y compressy
```

Because statistics now live under `~/.compressy/statistics`, running `compressy --view-stats` should produce either the summary or a “No Statistics Available” message without errors.

---

## 7. Uploading to Package Indexes

### 7.1 Upload to TestPyPI (dry run)

1. Ensure you have created a TestPyPI account and token. Store the token safely.
2. Configure credentials once (optional): create `%APPDATA%\pypirc` with:
   ```ini
   [distutils]
   index-servers =
       testpypi

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-AgENdGVzdC5weXBpLm9yZw...
   ```
3. Upload:
   ```powershell
   python -m twine upload --repository testpypi dist/*
   ```
4. Verify installation from TestPyPI:
   ```powershell
   python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple compressy
   ```

### 7.2 Upload to PyPI (production)

Once satisfied with the TestPyPI dry run:

```powershell
python -m twine upload dist/*
```

PyPI hosts the distributions behind a CDN. When users call `pip install compressy`, pip fetches the **simple index** page for `compressy`, selects the appropriate wheel (or sdist fallback), downloads it from PyPI, and installs it. No additional hosting is required once the upload succeeds.

> **Important:** PyPI uploads are immutable—if you need to re-release, bump the version (e.g., 1.0.1) and rebuild/upload.

---

## 8. Tagging & Release Notes

Although optional, tagging releases helps consumers track versions:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

Update GitHub Releases (if used) with highlights from `CHANGELOG.md` and provide installation instructions.

---

## 9. Frequently Asked Questions

**Q: Where does `pip install compressy` download the files from?**  
A: From PyPI’s package repository (<https://pypi.org/project/compressy/>). After you upload via `twine`, PyPI stores your distributions on its CDN. Pip checks PyPI’s “simple” API and retrieves the wheel/sdist you uploaded.

**Q: Do I have to host the files anywhere else?**  
A: No. PyPI handles distribution. Optionally, you can stage builds on TestPyPI first to catch issues before pushing to production.

**Q: Can I automate releases?**  
A: Yes. You can add a CI workflow that runs `python -m build` and `twine upload` when a tag is pushed. The current repo doesn’t yet include that automation; follow PyPI’s best practices if you add it.

**Q: What if someone needs to install from source directly?**  
A: Users can still clone the repo and run `pip install -e .` or `python -m pip install .`. The packaging configuration ensures both source installs and wheel installs share the same CLI entry points.

---

## 10. Quick Checklist (Copy/Paste Before Each Release)

```
[ ] Update pyproject.toml version
[ ] Update compressy/__init__.py __version__
[ ] Update CHANGELOG.md
[ ] Run black / isort / flake8 / pylint / mypy
[ ] Run pytest (optionally with coverage)
[ ] python -m build
[ ] python -m pip install --force-reinstall --no-deps dist/compressy-<version>-py3-none-any.whl
[ ] compressy --view-stats
[ ] python -m pip uninstall -y compressy
[ ] python -m twine upload --repository testpypi dist/* (optional trial)
[ ] python -m twine upload dist/*
[ ] Tag release in git and publish notes
```

---

Following these steps ensures maintainers can confidently package and publish Compressy so end users can simply run `pip install compressy` and begin compressing media immediately.


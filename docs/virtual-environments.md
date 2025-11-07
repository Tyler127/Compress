# Python Virtual Environments for Compressy Developers

Maintaining Compressy requires running tests, linters, and packaging commands without polluting your system Python installation. Python virtual environments (“venvs”) solve this by giving every project its own isolated interpreter, site-packages directory, and PATH setup.

This guide explains:

1. What a virtual environment is
2. Why Compressy contributors should use one
3. How to create and activate a venv on Windows, macOS, and Linux
4. Tips for using the venv in day-to-day development

---

## 1. What Is a Virtual Environment?

A virtual environment is a self-contained directory tree that houses:

- A copy (or symlink) of the Python interpreter
- Its own `site-packages` folder where `pip` installs packages
- Activation scripts that temporarily adjust your PATH/variables so you use the environment’s interpreter and dependencies

When the venv is active, `python`, `pip`, and any console scripts you install point to the environment instead of your global Python installation.

---

## 2. Why Compressy Maintainers Need a Venv

- **Isolation:** Test dependencies (pytest, coverage, build, etc.) won’t collide with versions used by other projects or system tools.
- **Reproducibility:** Everyone on the project shares the same dependency set defined by `requirements-dev.txt`, ensuring consistent CI results.
- **Safety:** Experimenting with the packaged CLI (install/uninstall) won’t modify your global site-packages.
- **Packaging Validation:** When you test installation of `dist/compressy-<version>-py3-none-any.whl`, doing so in a fresh venv mirrors how end users install the project.

---

## 3. Creating a Virtual Environment

### 3.1 Recommended Layout

Create the venv inside the repository root as `.venv/`. The leading dot keeps it hidden in most directory listings and mirrors common tooling defaults (e.g., VS Code recognizes `.venv`).

```text
Compressy/
├── .venv/            # virtual environment (generated)
├── compressy/        # package source
├── docs/             # documentation
├── pyproject.toml
└── ...
```

### 3.2 Windows (PowerShell)

```powershell
cd C:\Repos\Compressy
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

The prompt changes to show `(.venv)` when activated. To deactivate:

```powershell
deactivate
```

### 3.3 Windows (Command Prompt)

```cmd
cd C:\Repos\Compressy
python -m venv .venv
.\venv\Scripts\activate.bat
```

Deactivate with `deactivate`.

### 3.4 macOS/Linux (bash/zsh)

```bash
cd ~/Repos/Compressy
python3 -m venv .venv
source .venv/bin/activate
```

Deactivate with `deactivate`.

> **Tip:** Ensure the version of `python`/`python3` you invoke matches Compressy’s requirement (3.13+).

---

## 4. Installing Project Dependencies Inside the Venv

Once activated, run the dev setup:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

The editable install wires the CLI (`compressy`) and package imports to the working copy.

---

## 5. Daily Workflow Tips

- **Activate first:** Always activate `.venv` before running `pytest`, `black`, or packaging commands to ensure they use the isolated environment.
- **Prompt indicator:** Most shells display `(.venv)` in the prompt; if it disappears, reactivate.
- **Multiple shells:** Each shell session needs its own activation. Opening a new PowerShell tab requires rerunning `Activate.ps1`.
- **Version upgrades:** If you change Python versions (e.g., upgrade to Python 3.14), recreate the venv: delete `.venv/` and rerun `python -m venv .venv`.
- **Git hygiene:** `.venv/` is already ignored via `.gitignore`; never commit the environment directory.

---

## 6. Resetting or Recreating the Venv

If dependencies become inconsistent or you want a fresh start:

```bash
deactivate  # if active
rm -rf .venv  # or rmdir /s /q .venv on Windows
python -m venv .venv
# re-run installation commands (Section 4)
```

---

## 7. Integrating with Editors/IDEs

- **VS Code:** After creating `.venv`, open the command palette (`Ctrl+Shift+P`), run “Python: Select Interpreter”, and choose `.venv`.
- **PyCharm:** Go to Settings → Project → Python Interpreter → Add → Existing environment → select `.venv`.
- **GitHub Actions:** CI uses its own virtual environments. Locally matching the same `requirements-dev.txt` ensures parity.

---

## 8. Summary Checklist

```
[ ] python -m venv .venv
[ ] Activate the environment
[ ] python -m pip install --upgrade pip
[ ] python -m pip install -r requirements-dev.txt
[ ] python -m pip install -e .
[ ] Run pytest / black / isort / pylint / mypy inside the venv
[ ] Deactivate when done
```

Using a dedicated virtual environment keeps Compressy development predictable, isolated, and easy to reproduce across different machines and team members.


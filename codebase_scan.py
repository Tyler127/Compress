#!/usr/bin/env python3
"""
Codebase Scanner - Analyzes codebase structure and generates statistics.

Scans all files in the codebase, generates ASCII folder structure,
and provides detailed statistics including line counts, function counts,
and statement counts.
"""

import ast
import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Directories to exclude from scanning
EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    "dist",
    "build",
    ".pytest_cache",
    "htmlcov",
    ".mypy_cache",
    "node_modules",
    ".venv",
    "venv",
    ".tox",
    ".nox",
    ".pyre",
    ".pytype",
    "cython_debug",
    ".eggs",
    "develop-eggs",
    "downloads",
    "eggs",
    ".eggs",
    "lib",
    "lib64",
    "parts",
    "sdist",
    "var",
    "wheels",
    "pip-wheel-metadata",
    "share",
    ".installed.cfg",
    ".coverage",
    ".dmypy.json",
    "dmypy.json",
    ".cursor",
}

# File extensions that indicate Python files
PYTHON_EXTENSIONS = {".py"}


class FileScanner:
    """Scans and analyzes files in the codebase."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()
        self.files: List[Path] = []
        self.directories: List[Path] = []

    def should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from scanning."""
        # Check if any part of the path matches excluded directories
        for part in path.parts:
            if part in EXCLUDED_DIRS:
                return True
            # Check for .egg-info directories
            if part.endswith(".egg-info"):
                return True
        return False

    def scan_directory(self) -> None:
        """Recursively scan directory and collect all files."""
        self.files = []
        self.directories = [self.root_dir]

        for path in self.root_dir.rglob("*"):
            if self.should_exclude(path):
                continue

            if path.is_file():
                self.files.append(path)
            elif path.is_dir():
                self.directories.append(path)

        # Sort for consistent output
        self.files.sort()
        self.directories.sort()

    def count_python_lines(self, content: str) -> Tuple[int, int, int, int]:
        """
        Count lines in Python code.
        Returns: (code_lines, blank_lines, comment_lines, total_lines)
        """
        lines = content.splitlines()
        total_lines = len(lines)
        code_lines = 0
        blank_lines = 0
        comment_lines = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
            elif stripped.startswith("#"):
                comment_lines += 1
            else:
                code_lines += 1

        return code_lines, blank_lines, comment_lines, total_lines

    def count_python_stats(self, content: str) -> Tuple[int, int, int]:
        """
        Count functions, classes, and statements using AST.
        Returns: (function_count, class_count, statement_count)
        """
        try:
            tree = ast.parse(content)
        except (SyntaxError, ValueError):
            # If file has syntax errors, return zeros
            return 0, 0, 0

        function_count = 0
        class_count = 0
        statement_count = 0

        def count_statements(node):
            """Recursively count statements in AST."""
            nonlocal statement_count
            statement_count += 1

            for child in ast.iter_child_nodes(node):
                count_statements(child)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_count += 1
            elif isinstance(node, ast.ClassDef):
                class_count += 1

        # Count statements (excluding module-level)
        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.Expr,
                    ast.Assign,
                    ast.AugAssign,
                    ast.AnnAssign,
                    ast.Delete,
                    ast.Pass,
                    ast.Break,
                    ast.Continue,
                    ast.Return,
                    ast.Raise,
                    ast.Assert,
                    ast.Import,
                    ast.ImportFrom,
                    ast.Global,
                    ast.Nonlocal,
                    ast.If,
                    ast.For,
                    ast.While,
                    ast.With,
                    ast.Try,
                    ast.ExceptHandler,
                ),
            ):
                statement_count += 1

        return function_count, class_count, statement_count

    def analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single file and return statistics."""
        relative_path = file_path.relative_to(self.root_dir)
        file_size = file_path.stat().st_size
        file_ext = file_path.suffix.lower()

        stats = {
            "path": relative_path,
            "size": file_size,
            "extension": file_ext,
            "is_python": file_ext in PYTHON_EXTENSIONS,
            "total_lines": 0,
            "code_lines": 0,
            "blank_lines": 0,
            "comment_lines": 0,
            "functions": 0,
            "classes": 0,
            "statements": 0,
        }

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            stats["total_lines"] = len(content.splitlines())

            if stats["is_python"]:
                code, blank, comment, total = self.count_python_lines(content)
                stats["code_lines"] = code
                stats["blank_lines"] = blank
                stats["comment_lines"] = comment
                stats["total_lines"] = total

                funcs, classes, stmts = self.count_python_stats(content)
                stats["functions"] = funcs
                stats["classes"] = classes
                stats["statements"] = stmts
        except Exception:
            # If we can't read the file, just return basic stats
            pass

        return stats


class StatisticsCollector:
    """Collects and aggregates statistics from file analysis."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.file_stats: List[Dict] = []
        self.directory_stats: Dict[str, Dict] = defaultdict(
            lambda: {
                "files": 0,
                "total_lines": 0,
                "code_lines": 0,
                "blank_lines": 0,
                "comment_lines": 0,
                "functions": 0,
                "classes": 0,
                "statements": 0,
                "file_types": defaultdict(int),
            }
        )
        self.overall_stats: Dict = {
            "total_files": 0,
            "total_directories": 0,
            "total_lines": 0,
            "python_files": 0,
            "python_total_lines": 0,
            "code_lines": 0,
            "blank_lines": 0,
            "comment_lines": 0,
            "functions": 0,
            "classes": 0,
            "statements": 0,
            "file_types": defaultdict(int),
        }

    def collect_file_stats(self, stats: Dict) -> None:
        """Add file statistics to collection."""
        self.file_stats.append(stats)

        # Update directory stats
        dir_path = str(stats["path"].parent)
        if dir_path == ".":
            dir_path = "root"

        self.directory_stats[dir_path]["files"] += 1
        self.directory_stats[dir_path]["total_lines"] += stats["total_lines"]
        self.directory_stats[dir_path]["file_types"][stats["extension"]] += 1

        if stats["is_python"]:
            self.directory_stats[dir_path]["code_lines"] += stats["code_lines"]
            self.directory_stats[dir_path]["blank_lines"] += stats["blank_lines"]
            self.directory_stats[dir_path]["comment_lines"] += stats["comment_lines"]
            self.directory_stats[dir_path]["functions"] += stats["functions"]
            self.directory_stats[dir_path]["classes"] += stats["classes"]
            self.directory_stats[dir_path]["statements"] += stats["statements"]

    def generate_summary(self) -> Dict:
        """Generate overall summary statistics."""
        self.overall_stats["total_files"] = len(self.file_stats)
        self.overall_stats["total_directories"] = len(self.directory_stats)

        for stats in self.file_stats:
            self.overall_stats["total_lines"] += stats["total_lines"]
            self.overall_stats["file_types"][stats["extension"]] += 1

            if stats["is_python"]:
                self.overall_stats["python_files"] += 1
                self.overall_stats["python_total_lines"] += stats["total_lines"]
                self.overall_stats["code_lines"] += stats["code_lines"]
                self.overall_stats["blank_lines"] += stats["blank_lines"]
                self.overall_stats["comment_lines"] += stats["comment_lines"]
                self.overall_stats["functions"] += stats["functions"]
                self.overall_stats["classes"] += stats["classes"]
                self.overall_stats["statements"] += stats["statements"]

        return self.overall_stats


class OutputGenerator:
    """Generates output files in text and markdown formats."""

    def __init__(self, root_dir: Path, scanner: FileScanner, collector: StatisticsCollector):
        self.root_dir = root_dir
        self.scanner = scanner
        self.collector = collector

    def _filter_files_by_prefix(self, prefix: str) -> List[Dict]:
        """Filter file stats by path prefix."""
        return [s for s in self.collector.file_stats if str(s["path"]).startswith(prefix)]

    def _calculate_section_stats(self, files: List[Dict]) -> Dict:
        """Calculate statistics for a section of files."""
        stats = {
            "total_files": len(files),
            "total_lines": 0,
            "python_files": 0,
            "python_total_lines": 0,
            "code_lines": 0,
            "blank_lines": 0,
            "comment_lines": 0,
            "functions": 0,
            "classes": 0,
            "statements": 0,
            "file_types": defaultdict(int),
        }

        for file_stat in files:
            stats["total_lines"] += file_stat["total_lines"]
            stats["file_types"][file_stat["extension"]] += 1

            if file_stat["is_python"]:
                stats["python_files"] += 1
                stats["python_total_lines"] += file_stat["total_lines"]
                stats["code_lines"] += file_stat["code_lines"]
                stats["blank_lines"] += file_stat["blank_lines"]
                stats["comment_lines"] += file_stat["comment_lines"]
                stats["functions"] += file_stat["functions"]
                stats["classes"] += file_stat["classes"]
                stats["statements"] += file_stat["statements"]

        return stats

    def generate_tree_structure(self, use_links: bool = False) -> str:
        """Generate ASCII tree structure of the codebase."""
        lines = []
        root_name = self.root_dir.name

        # Build directory tree
        dir_tree = {}
        for file_path in self.scanner.files:
            parts = file_path.relative_to(self.root_dir).parts
            current = dir_tree
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = None

        def format_tree(tree, prefix="", is_last=True, path_parts=None):
            """Recursively format tree structure."""
            if path_parts is None:
                path_parts = []
            items = sorted([(k, v) for k, v in tree.items() if v is not None], key=lambda x: x[0])
            files = sorted([k for k, v in tree.items() if v is None])

            # Add directories
            for i, (name, subtree) in enumerate(items):
                is_last_item = i == len(items) - 1 and len(files) == 0
                connector = "└── " if is_last_item else "├── "
                current_path = "/".join(path_parts + [name])
                
                if use_links:
                    # Create anchor link for directory
                    anchor = f"#{current_path.replace('/', '-').lower()}"
                    dir_name = f"[{name}/]({anchor})"
                else:
                    dir_name = f"{name}/"
                
                lines.append(f"{prefix}{connector}{dir_name}")
                new_prefix = prefix + ("    " if is_last_item else "│   ")
                format_tree(subtree, new_prefix, is_last_item, path_parts + [name])

            # Add files
            for i, filename in enumerate(files):
                is_last_file = i == len(files) - 1
                connector = "└── " if is_last_file else "├── "
                current_path = "/".join(path_parts + [filename])
                
                # Find file stats for additional info
                file_path = self.root_dir / Path(*path_parts) / filename
                try:
                    rel_path = file_path.relative_to(self.root_dir)
                    file_stat = next((s for s in self.collector.file_stats if s["path"] == rel_path), None)
                    
                    if use_links:
                        # Create anchor link for file
                        anchor = f"#file-{str(rel_path).replace('/', '-').replace('\\', '-').lower()}"
                        file_display = f"[{filename}]({anchor})"
                    else:
                        file_display = filename
                    
                    if file_stat and file_stat["is_python"]:
                        info = f" ({file_stat['total_lines']} lines"
                        if file_stat["functions"] > 0:
                            info += f", {file_stat['functions']} functions"
                        if file_stat["classes"] > 0:
                            info += f", {file_stat['classes']} classes"
                        info += ")"
                        lines.append(f"{prefix}{connector}{file_display}{info}")
                    else:
                        lines.append(f"{prefix}{connector}{file_display}")
                except Exception:
                    lines.append(f"{prefix}{connector}{filename}")

        if dir_tree:
            lines.insert(0, f"{root_name}/")
            format_tree(dir_tree)
        else:
            lines.append(f"{root_name}/")

        return "\n".join(lines)

    def generate_file_list(self, files: Optional[List[Dict]] = None) -> str:
        """Generate detailed file listing with statistics."""
        if files is None:
            files = self.collector.file_stats
            
        lines = []
        lines.append("DETAILED FILE STATISTICS")
        lines.append("=" * 80)
        lines.append("")

        # Group files by directory
        files_by_dir = defaultdict(list)
        for stats in files:
            dir_path = str(stats["path"].parent)
            if dir_path == ".":
                dir_path = "root"
            files_by_dir[dir_path].append(stats)

        # Sort directories
        for dir_path in sorted(files_by_dir.keys()):
            if dir_path != "root":
                lines.append(f"\nDirectory: {dir_path}/")
            else:
                lines.append("\nRoot Directory:")
            lines.append("-" * 80)

            for stats in sorted(files_by_dir[dir_path], key=lambda x: x["path"]):
                lines.append(f"\nFile: {stats['path']}")
                lines.append(f"  Size: {stats['size']:,} bytes")
                lines.append(f"  Total Lines: {stats['total_lines']:,}")

                if stats["is_python"]:
                    lines.append(f"    Code Lines: {stats['code_lines']:,}")
                    lines.append(f"    Blank Lines: {stats['blank_lines']:,}")
                    lines.append(f"    Comment Lines: {stats['comment_lines']:,}")
                    lines.append(f"  Functions: {stats['functions']}")
                    lines.append(f"  Classes: {stats['classes']}")
                    lines.append(f"  Statements: {stats['statements']:,}")

        return "\n".join(lines)

    def generate_section_summary_text(self, stats: Dict, section_name: str) -> str:
        """Generate summary statistics for a section in text format."""
        lines = []
        lines.append(f"\n{section_name.upper()} SUMMARY")
        lines.append("=" * 80)
        lines.append("")

        lines.append(f"Total Files: {stats['total_files']:,}")
        lines.append(f"Total Lines (All Files): {stats['total_lines']:,}")
        lines.append("")

        lines.append(f"Python Files: {stats['python_files']:,}")
        if stats["python_files"] > 0:
            lines.append(f"  Total Lines: {stats['python_total_lines']:,}")
            lines.append(f"  Code Lines: {stats['code_lines']:,}")
            lines.append(f"  Blank Lines: {stats['blank_lines']:,}")
            lines.append(f"  Comment Lines: {stats['comment_lines']:,}")
            lines.append(f"  Functions: {stats['functions']:,}")
            lines.append(f"  Classes: {stats['classes']:,}")
            lines.append(f"  Statements: {stats['statements']:,}")
        lines.append("")

        lines.append("File Type Distribution:")
        for ext, count in sorted(stats["file_types"].items(), key=lambda x: x[1], reverse=True):
            ext_display = ext if ext else "(no extension)"
            lines.append(f"  {ext_display}: {count:,} files")

        return "\n".join(lines)

    def generate_summary_text(self) -> str:
        """Generate summary statistics in text format."""
        lines = []
        lines.append("\n" + "=" * 80)
        lines.append("OVERALL SUMMARY")
        lines.append("=" * 80)
        lines.append("")

        stats = self.collector.overall_stats
        lines.append(f"Total Files: {stats['total_files']:,}")
        lines.append(f"Total Directories: {stats['total_directories']:,}")
        lines.append(f"Total Lines (All Files): {stats['total_lines']:,}")
        lines.append("")

        lines.append(f"Python Files: {stats['python_files']:,}")
        if stats["python_files"] > 0:
            lines.append(f"  Total Lines: {stats['python_total_lines']:,}")
            lines.append(f"  Code Lines: {stats['code_lines']:,}")
            lines.append(f"  Blank Lines: {stats['blank_lines']:,}")
            lines.append(f"  Comment Lines: {stats['comment_lines']:,}")
            lines.append(f"  Functions: {stats['functions']:,}")
            lines.append(f"  Classes: {stats['classes']:,}")
            lines.append(f"  Statements: {stats['statements']:,}")
        lines.append("")

        lines.append("File Type Distribution:")
        for ext, count in sorted(stats["file_types"].items(), key=lambda x: x[1], reverse=True):
            ext_display = ext if ext else "(no extension)"
            lines.append(f"  {ext_display}: {count:,} files")

        return "\n".join(lines)

    def write_text_output(self, output_file: Path) -> None:
        """Write plain text output file."""
        lines = []
        lines.append("CODEBASE STRUCTURE")
        lines.append("=" * 80)
        lines.append("")
        lines.append(self.generate_tree_structure())
        lines.append("")
        
        # Compressy section
        compressy_files = self._filter_files_by_prefix("compressy")
        if compressy_files:
            lines.append(self.generate_file_list(compressy_files))
            compressy_stats = self._calculate_section_stats(compressy_files)
            lines.append(self.generate_section_summary_text(compressy_stats, "Compressy"))
        
        # Tests section
        tests_files = self._filter_files_by_prefix("tests")
        if tests_files:
            lines.append(self.generate_file_list(tests_files))
            tests_stats = self._calculate_section_stats(tests_files)
            lines.append(self.generate_section_summary_text(tests_stats, "Tests"))
        
        # Overall summary
        lines.append(self.generate_summary_text())

        output_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"Text output written to: {output_file}")

    def generate_markdown_file_list(self, files: Optional[List[Dict]] = None, section_id: str = "") -> str:
        """Generate detailed file listing in markdown format."""
        if files is None:
            files = self.collector.file_stats
            
        lines = []
        lines.append("## Detailed File Statistics\n")

        # Group files by directory
        files_by_dir = defaultdict(list)
        for stats in files:
            dir_path = str(stats["path"].parent)
            if dir_path == ".":
                dir_path = "root"
            files_by_dir[dir_path].append(stats)

        # Sort directories
        for dir_path in sorted(files_by_dir.keys()):
            if dir_path != "root":
                anchor = f"{section_id}-{dir_path.replace('/', '-').lower()}" if section_id else dir_path.replace('/', '-').lower()
                lines.append(f"\n### <a id=\"{anchor}\"></a>Directory: `{dir_path}/`\n")
            else:
                anchor = f"{section_id}-root" if section_id else "root"
                lines.append(f"\n### <a id=\"{anchor}\"></a>Root Directory\n")

            lines.append("| File | Size | Lines | Code | Blank | Comments | Functions | Classes | Statements |")
            lines.append("|------|------|-------|------|-------|----------|-----------|---------|------------|")

            for stats in sorted(files_by_dir[dir_path], key=lambda x: x["path"]):
                file_anchor = f"file-{str(stats['path']).replace('/', '-').replace('\\', '-').lower()}"
                # Add anchor before the table row (using HTML anchor)
                file_col = f"[`{stats['path']}`](#{file_anchor})"
                size_col = f"{stats['size']:,}"
                total_col = f"{stats['total_lines']:,}"

                if stats["is_python"]:
                    code_col = f"{stats['code_lines']:,}"
                    blank_col = f"{stats['blank_lines']:,}"
                    comment_col = f"{stats['comment_lines']:,}"
                    func_col = str(stats["functions"])
                    class_col = str(stats["classes"])
                    stmt_col = f"{stats['statements']:,}"
                else:
                    code_col = "-"
                    blank_col = "-"
                    comment_col = "-"
                    func_col = "-"
                    class_col = "-"
                    stmt_col = "-"

                # Add HTML anchor before the table row for linking
                lines.append(f"<a id=\"{file_anchor}\"></a>")
                lines.append(
                    f"| {file_col} | {size_col} | {total_col} | {code_col} | "
                    f"{blank_col} | {comment_col} | {func_col} | {class_col} | {stmt_col} |"
                )

        return "\n".join(lines)

    def generate_markdown_section_summary(self, stats: Dict, section_name: str, section_id: str) -> str:
        """Generate summary statistics for a section in markdown format."""
        lines = []
        lines.append(f"## <a id=\"{section_id}\"></a>{section_name} Summary\n")

        lines.append("### General Statistics\n")
        lines.append(f"- **Total Files:** {stats['total_files']:,}")
        lines.append(f"- **Total Lines (All Files):** {stats['total_lines']:,}\n")

        lines.append("### Python Statistics\n")
        lines.append(f"- **Python Files:** {stats['python_files']:,}")
        if stats["python_files"] > 0:
            lines.append(f"- **Total Lines:** {stats['python_total_lines']:,}")
            lines.append(f"- **Code Lines:** {stats['code_lines']:,}")
            lines.append(f"- **Blank Lines:** {stats['blank_lines']:,}")
            lines.append(f"- **Comment Lines:** {stats['comment_lines']:,}")
            lines.append(f"- **Functions:** {stats['functions']:,}")
            lines.append(f"- **Classes:** {stats['classes']:,}")
            lines.append(f"- **Statements:** {stats['statements']:,}")
        lines.append("")

        lines.append("### File Type Distribution\n")
        lines.append("| Extension | Count |")
        lines.append("|-----------|-------|")
        for ext, count in sorted(stats["file_types"].items(), key=lambda x: x[1], reverse=True):
            ext_display = ext if ext else "(no extension)"
            lines.append(f"| `{ext_display}` | {count:,} |")

        return "\n".join(lines)

    def generate_markdown_summary(self) -> str:
        """Generate summary statistics in markdown format."""
        lines = []
        lines.append("## <a id=\"overall-summary\"></a>Overall Summary\n")

        stats = self.collector.overall_stats

        lines.append("### General Statistics\n")
        lines.append(f"- **Total Files:** {stats['total_files']:,}")
        lines.append(f"- **Total Directories:** {stats['total_directories']:,}")
        lines.append(f"- **Total Lines (All Files):** {stats['total_lines']:,}\n")

        lines.append("### Python Statistics\n")
        lines.append(f"- **Python Files:** {stats['python_files']:,}")
        if stats["python_files"] > 0:
            lines.append(f"- **Total Lines:** {stats['python_total_lines']:,}")
            lines.append(f"- **Code Lines:** {stats['code_lines']:,}")
            lines.append(f"- **Blank Lines:** {stats['blank_lines']:,}")
            lines.append(f"- **Comment Lines:** {stats['comment_lines']:,}")
            lines.append(f"- **Functions:** {stats['functions']:,}")
            lines.append(f"- **Classes:** {stats['classes']:,}")
            lines.append(f"- **Statements:** {stats['statements']:,}")
        lines.append("")

        lines.append("### File Type Distribution\n")
        lines.append("| Extension | Count |")
        lines.append("|-----------|-------|")
        for ext, count in sorted(stats["file_types"].items(), key=lambda x: x[1], reverse=True):
            ext_display = ext if ext else "(no extension)"
            lines.append(f"| `{ext_display}` | {count:,} |")

        return "\n".join(lines)

    def write_markdown_output(self, output_file: Path) -> None:
        """Write markdown output file."""
        lines = []
        lines.append("# Codebase Structure and Statistics\n")
        lines.append(f"Generated for: `{self.root_dir.name}`\n")
        lines.append("---\n")

        # Table of contents
        lines.append("## Table of Contents\n")
        lines.append("- [Codebase Structure](#codebase-structure)")
        lines.append("- [Compressy Section](#compressy-summary)")
        lines.append("- [Tests Section](#tests-summary)")
        lines.append("- [Overall Summary](#overall-summary)\n")
        lines.append("---\n")

        lines.append("## <a id=\"codebase-structure\"></a>Codebase Structure\n")
        lines.append("```")
        lines.append(self.generate_tree_structure(use_links=True))
        lines.append("```\n")

        # Compressy section
        compressy_files = self._filter_files_by_prefix("compressy")
        if compressy_files:
            lines.append(self.generate_markdown_file_list(compressy_files, "compressy"))
            compressy_stats = self._calculate_section_stats(compressy_files)
            lines.append(self.generate_markdown_section_summary(compressy_stats, "Compressy", "compressy-summary"))
            lines.append("\n---\n")

        # Tests section
        tests_files = self._filter_files_by_prefix("tests")
        if tests_files:
            lines.append(self.generate_markdown_file_list(tests_files, "tests"))
            tests_stats = self._calculate_section_stats(tests_files)
            lines.append(self.generate_markdown_section_summary(tests_stats, "Tests", "tests-summary"))
            lines.append("\n---\n")

        # Overall summary
        lines.append(self.generate_markdown_summary())

        output_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"Markdown output written to: {output_file}")


def main():
    """Main entry point for the codebase scanner."""
    parser = argparse.ArgumentParser(description="Scan codebase and generate structure/statistics")
    parser.add_argument(
        "root_dir",
        nargs="?",
        default=".",
        type=Path,
        help="Root directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for output files (default: root directory)",
    )

    args = parser.parse_args()
    root_dir = Path(args.root_dir).resolve()

    if not root_dir.exists():
        print(f"Error: Directory '{root_dir}' does not exist")
        return 1

    if not root_dir.is_dir():
        print(f"Error: '{root_dir}' is not a directory")
        return 1

    output_dir = args.output_dir.resolve() if args.output_dir else root_dir

    print(f"Scanning codebase: {root_dir}")
    print("This may take a moment...\n")

    # Scan files
    scanner = FileScanner(root_dir)
    scanner.scan_directory()
    print(f"Found {len(scanner.files)} files in {len(scanner.directories)} directories")

    # Analyze files
    collector = StatisticsCollector(root_dir)
    for file_path in scanner.files:
        stats = scanner.analyze_file(file_path)
        collector.collect_file_stats(stats)

    collector.generate_summary()

    # Generate outputs
    generator = OutputGenerator(root_dir, scanner, collector)
    text_output = output_dir / "codebase_outline.txt"
    md_output = output_dir / "codebase_outline.md"

    generator.write_text_output(text_output)
    generator.write_markdown_output(md_output)

    print("\nScan complete!")
    return 0


if __name__ == "__main__":
    exit(main())


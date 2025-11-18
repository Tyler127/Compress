# Compressy Test Suite

This directory contains comprehensive unit and integration tests for the compressy media compression application.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_utils/              # Test utilities and helpers
│   ├── fixtures.py          # Test data creation helpers
│   ├── mocks.py             # Reusable mock objects
│   └── test_format.py       # Tests for format utilities
├── test_core/               # Core compression functionality tests
│   ├── test_config.py       # Configuration and validation tests
│   ├── test_ffmpeg_executor.py  # FFmpeg execution tests
│   ├── test_video_compressor.py # Video compression tests
│   ├── test_image_compressor.py # Image compression tests
│   └── test_media_compressor.py # Media compressor orchestrator tests
├── test_services/            # Service layer tests
│   ├── test_reports.py      # Report generation tests
│   ├── test_statistics.py   # Statistics tracking tests
│   └── test_backup.py       # Backup manager tests
└── test_integration/         # End-to-end integration tests
    └── test_end_to_end.py   # Full workflow tests
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=compressy --cov-report=html
```

### Run Specific Test File
```bash
pytest tests/test_core/test_config.py
```

### Run Specific Test
```bash
pytest tests/test_core/test_config.py::TestParameterValidator::test_validate_video_crf_valid_range
```

### Run Tests by Marker
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Coverage Goals

- **Overall**: 80% line coverage minimum
- **Core modules**: 90% coverage (critical business logic)
- **Utils**: 95% coverage (simple, pure functions)
- **Services**: 85% coverage
- **Error paths**: 100% coverage (all error handling tested)

## Test Execution in CI

Tests are automatically run on:
- Push to main/master/develop branches
- Pull requests to main/master/develop branches
- Python 3.14
- Multiple operating systems (Ubuntu, Windows, macOS)

## Writing New Tests

When adding new functionality:

1. **Write tests first** (TDD approach) or alongside implementation
2. **Test edge cases** - boundary conditions, empty inputs, invalid inputs
3. **Test error handling** - all error paths should be covered
4. **Use fixtures** - Leverage `conftest.py` fixtures for common setup
5. **Mock external dependencies** - FFmpeg, file system operations
6. **Keep tests isolated** - Each test should be independent
7. **Use descriptive names** - Test names should clearly describe what they test

## Mocking Strategy

- **FFmpeg/Subprocess**: Mock `subprocess.Popen` and `subprocess.run`
- **File System**: Use `tempfile` and `unittest.mock.patch` for file operations
- **JSON Files**: Mock JSON reading/writing where appropriate
- **Time/Date**: Mock `datetime.now()` for consistent timestamps
- **shutil**: Mock `shutil.copytree`, `shutil.copy2` for backup tests

## Test Fixtures

Common fixtures available in `conftest.py`:

- `temp_dir`: Temporary directory for test files
- `sample_video`: Mock video file path
- `sample_image_png`: Mock PNG file path
- `sample_image_jpg`: Mock JPEG file path
- `mock_ffmpeg_executor`: Mocked FFmpegExecutor
- `mock_config`: Sample CompressionConfig
- `mock_statistics`: Sample statistics dictionary

## Continuous Integration

The GitHub Actions workflow (`.github/workflows/tests.yml`) runs:
- Tests on multiple Python versions
- Tests on multiple operating systems
- Coverage reporting
- Coverage threshold enforcement (80%)


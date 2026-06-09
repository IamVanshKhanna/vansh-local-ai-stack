# Tests

Unit tests for the local AI stack automation scripts.

## Running Tests

```bash
# Install test dependencies
pip install pytest

# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_health_check.py -v

# Run a specific test
pytest tests/test_scan_drives.py::TestFormatSize::test_bytes -v
```

## Test Coverage

| Script | Test File | Key Tests |
|--------|-----------|-----------|
| scan_drives.py | test_scan_drives.py | Format size, skip dirs, scan directory |
| classify_files.py | test_classify_files.py | Extension/path/default classification |
| apply_moves.py | test_apply_moves.py | Validation, move/copy execution, plan generation |
| disk_report.py | test_disk_report.py | Drive info, report generation |
| health_check.py | test_health_check.py | Ollama/RAM/disk/scripts checks |

## Adding Tests

1. Create `test_<script_name>.py` in this directory
2. Import from `scripts.<name>` after adding scripts to path
3. Use `tmp_path` fixture for filesystem tests
4. Run `pytest tests/ -v` to verify

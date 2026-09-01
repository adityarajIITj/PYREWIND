# PyRewind v0.2.0a0 - PyPI Publishing Guide

## 🎯 Steps to Publish

### 1. Prerequisites
- ✅ Package built (dist/ folder exists)
- ✅ PyPI account created with API token
- ✅ `twine` installed

### 2. Get Your API Token

**From TestPyPI (for testing):**
https://test.pypi.org/manage/account/#api-tokens

**From Real PyPI (for production):**
https://pypi.org/manage/account/#api-tokens

Create a token with scope "Entire account" and copy it.

### 3. Upload to TestPyPI (Recommended First)

**Windows (PowerShell):**
```powershell
cd c:\Users\adity\OneDrive\文档\pyrewind
python -m twine upload --repository testpypi dist/*
```

**Mac/Linux:**
```bash
python3 -m twine upload --repository testpypi dist/*
```

When prompted:
- Username: `__token__`
- Password: Paste your TestPyPI API token (including `pypi-` prefix)

### 4. Test Your Package from TestPyPI

```bash
pip install --index-url https://test.pypi.org/simple/ --no-deps pyrewind
```

Then verify:
```python
from pyrewind import rewindable, TraceInspector
print("✅ PyRewind v0.2.0a0 installed and working!")
```

### 5. Upload to Real PyPI (After Testing)

**Windows (PowerShell):**
```powershell
cd c:\Users\adity\OneDrive\文档\pyrewind
python -m twine upload dist/*
```

**Mac/Linux:**
```bash
python3 -m twine upload dist/*
```

When prompted:
- Username: `__token__`
- Password: Paste your real PyPI API token (including `pypi-` prefix)

### 6. Verify on PyPI

Visit: https://pypi.org/project/pyrewind/

Your package should be visible with:
- Version: 0.2.0a0 (Alpha)
- Description with v2 features
- Links to GitHub repository
- MIT License

### 7. Install from Real PyPI

```bash
pip install pyrewind
```

---

## 📦 Package Contents

```
pyrewind-0.2.0a0/
├── pyrewind/
│   ├── __init__.py                    (Main exports)
│   ├── decorator.py                   (v0.1: @rewindable)
│   ├── replay.py                      (v0.1: replay API)
│   ├── trace_model.py                 (v0.1: Trace class)
│   ├── tracer.py                      (v0.1: Tracer implementation)
│   ├── serializer.py                  (v0.1: JSON serialization)
│   ├── compat.py                      (Compatibility utilities)
│   ├── errors.py                      (Custom exceptions)
│   ├── replay_builder.py              (v2: Fluent API)
│   ├── async_tracer.py                (v2: Async support)
│   ├── trace_comparison.py            (v2: Filtering & comparison)
│   ├── core/                          (v2: Architecture)
│   │   ├── event_system.py            (Event dispatcher)
│   │   ├── plugin.py                  (Plugin system)
│   │   ├── storage.py                 (Storage backends)
│   │   └── strategy.py                (Serialization strategies)
│   ├── analysis/                      (v2: Analysis tools)
│   │   └── inspector.py               (TraceInspector)
│   ├── trace/                         (v2: Filtering & slicing)
│   │   └── filter.py                  (AdvancedTraceFilter, TraceSlice)
│   ├── cli/                           (v2: Command-line interface)
│   │   └── main.py                    (PyRewindCLI)
│   ├── metadata/                      (v2: Tagging system)
│   │   └── tagger.py                  (TraceTagger)
│   ├── plugins/                       (v2: Plugin examples)
│   │   └── examples.py                (3 example plugins)
│   ├── storage/                       (v2: Storage backends)
│   │   ├── writer.py                  (Streaming writer)
│   │   ├── formats.py                 (JSON, MessagePack, CSV)
│   │   └── backends.py                (SQLite backend)
│   └── export/                        (v2: Export formats)
│       └── formats.py                 (HTML viewer, etc)
├── tests/                             (51 comprehensive tests)
├── examples/                          (3 working examples)
├── README.md                          (Full documentation)
├── LICENSE                            (MIT License)
└── pyproject.toml                     (Package metadata)
```

---

## 📊 Package Metadata

- **Name**: pyrewind
- **Version**: 0.2.0a0 (Alpha)
- **Python**: 3.10+
- **License**: MIT
- **Status**: Pre-Alpha (stable v0.1 API, new v2 features)

---

## 🔄 Update Process for Future Releases

### For v0.2.0 (stable):
1. Update `pyproject.toml`: version = "0.2.0"
2. Run `python -m build`
3. Upload to PyPI with `python -m twine upload dist/*`

### For v0.3.0:
1. Update version in `pyproject.toml`
2. Make changes
3. Run tests: `pytest tests/ -v`
4. Git commit and push
5. Build: `python -m build`
6. Upload: `python -m twine upload dist/*`

---

## 📝 Note

For this alpha release:
- ✅ 100% backwards compatible with v0.1
- ✅ 40+ new v2 features
- ✅ 51 comprehensive tests passing
- ✅ Full documentation

After gathering feedback, you can release v0.2.0 as stable!

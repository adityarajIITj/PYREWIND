#!/bin/bash
# PyRewind v0.2.0a0 - Upload to TestPyPI

echo "================================================"
echo "PyRewind v0.2.0a0 - TestPyPI Upload"
echo "================================================"
echo ""
echo "You'll need your TestPyPI API token from:"
echo "https://test.pypi.org/manage/account/#api-tokens"
echo ""
echo "When prompted for username, use: __token__"
echo "When prompted for password, paste your token"
echo ""

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Upload to TestPyPI
python -m twine upload --repository testpypi $SCRIPT_DIR/dist/*

echo ""
echo "✅ Upload complete!"
echo ""
echo "Your package should be visible at:"
echo "https://test.pypi.org/project/pyrewind"
echo ""
echo "To test installation:"
echo "pip install --index-url https://test.pypi.org/simple/ --no-deps pyrewind"

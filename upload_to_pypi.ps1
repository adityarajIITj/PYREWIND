# PyRewind v0.2.0a0 - Upload to PyPI (Windows PowerShell)

Write-Host "================================================"
Write-Host "PyRewind v0.2.0a0 - PyPI Upload"
Write-Host "================================================"
Write-Host ""
Write-Host "Choose upload destination:"
Write-Host "1) TestPyPI (recommended for testing)"
Write-Host "2) Real PyPI (production)"
Write-Host ""

$choice = Read-Host "Enter choice (1 or 2)"

$scriptDir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent

if ($choice -eq "1") {
    Write-Host ""
    Write-Host "Uploading to TestPyPI..."
    Write-Host "Get your token from: https://test.pypi.org/manage/account/#api-tokens"
    Write-Host ""
    Write-Host "When prompted:"
    Write-Host "  Username: __token__"
    Write-Host "  Password: (paste your token)"
    Write-Host ""
    
    python -m twine upload --repository testpypi "$scriptDir\dist\*"
    
    Write-Host ""
    Write-Host "✅ Upload to TestPyPI complete!"
    Write-Host ""
    Write-Host "View your package at:"
    Write-Host "https://test.pypi.org/project/pyrewind"
    Write-Host ""
    Write-Host "Test installation:"
    Write-Host "pip install --index-url https://test.pypi.org/simple/ --no-deps pyrewind"
}
elseif ($choice -eq "2") {
    Write-Host ""
    Write-Host "Uploading to Real PyPI..."
    Write-Host "Get your token from: https://pypi.org/manage/account/#api-tokens"
    Write-Host ""
    Write-Host "When prompted:"
    Write-Host "  Username: __token__"
    Write-Host "  Password: (paste your token)"
    Write-Host ""
    
    python -m twine upload "$scriptDir\dist\*"
    
    Write-Host ""
    Write-Host "✅ Upload to PyPI complete!"
    Write-Host ""
    Write-Host "View your package at:"
    Write-Host "https://pypi.org/project/pyrewind"
    Write-Host ""
    Write-Host "Installation:"
    Write-Host "pip install pyrewind"
}
else {
    Write-Host "❌ Invalid choice. Exiting."
}

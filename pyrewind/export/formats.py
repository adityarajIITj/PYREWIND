"""HTML export format for interactive trace viewing."""

from __future__ import annotations

import json
from typing import Any
from pyrewind.storage.formats import TraceFormat


class HTMLTraceFormat(TraceFormat):
    """HTML format for interactive trace visualization.

    Generates a standalone HTML file with:
    - Step navigation
    - Local variables inspection
    - Execution timeline
    - Search and filtering
    """

    @property
    def name(self) -> str:
        return "html"

    @property
    def extension(self) -> str:
        return ".html"

    def serialize(self, data: dict[str, Any]) -> bytes:
        """Generate HTML from trace data."""
        html = self._generate_html(data)
        return html.encode("utf-8")

    def deserialize(self, data: bytes) -> dict[str, Any]:
        """HTML is write-only format."""
        raise NotImplementedError("HTML format is write-only")

    def _generate_html(self, trace_data: dict[str, Any]) -> str:
        """Generate complete HTML document."""
        steps = trace_data.get("steps", [])
        qualname = trace_data.get("qualname", "Unknown")
        result_repr = trace_data.get("result_repr", "N/A")
        exception = trace_data.get("exception")

        # Build step navigation HTML
        steps_html = self._build_steps_html(steps)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyRewind Trace: {qualname}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        header h1 {{
            font-size: 24px;
            margin-bottom: 8px;
        }}

        .header-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            font-size: 12px;
            opacity: 0.9;
        }}

        .container {{
            display: flex;
            height: calc(100vh - 100px);
        }}

        .sidebar {{
            width: 300px;
            background: white;
            border-right: 1px solid #ddd;
            overflow-y: auto;
            padding: 15px;
        }}

        .step-list {{
            list-style: none;
        }}

        .step-item {{
            padding: 8px;
            margin: 4px 0;
            background: #f9f9f9;
            border-left: 3px solid #ddd;
            cursor: pointer;
            font-size: 12px;
            border-radius: 2px;
            transition: all 0.2s;
        }}

        .step-item:hover {{
            background: #f0f0f0;
            border-left-color: #667eea;
        }}

        .step-item.active {{
            background: #e8eaf6;
            border-left-color: #667eea;
            font-weight: bold;
        }}

        .main {{
            flex: 1;
            display: flex;
            flex-direction: column;
            background: white;
        }}

        .step-details {{
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }}

        .step-header {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
            font-size: 13px;
        }}

        .step-header div {{
            background: #f9f9f9;
            padding: 8px;
            border-radius: 4px;
        }}

        .step-header label {{
            color: #666;
            font-weight: bold;
            display: block;
            margin-bottom: 4px;
        }}

        .step-header value {{
            font-family: 'Monaco', 'Courier New', monospace;
            color: #333;
        }}

        .locals-section {{
            margin-top: 20px;
        }}

        .locals-title {{
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
            font-size: 14px;
        }}

        .locals-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            font-family: 'Monaco', 'Courier New', monospace;
        }}

        .locals-table th {{
            background: #f5f5f5;
            border-bottom: 2px solid #ddd;
            padding: 8px;
            text-align: left;
            font-weight: bold;
        }}

        .locals-table td {{
            border-bottom: 1px solid #eee;
            padding: 8px;
            word-break: break-all;
        }}

        .locals-table tr:hover {{
            background: #f9f9f9;
        }}

        .result-section {{
            margin-top: 20px;
            padding: 15px;
            background: #f0f8f0;
            border-left: 4px solid #4caf50;
            border-radius: 4px;
        }}

        .exception-section {{
            margin-top: 20px;
            padding: 15px;
            background: #fef0f0;
            border-left: 4px solid #f44336;
            border-radius: 4px;
        }}

        .search-box {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
            margin-bottom: 10px;
        }}

        .search-box input {{
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 12px;
        }}

        footer {{
            background: #f9f9f9;
            border-top: 1px solid #ddd;
            padding: 10px 20px;
            font-size: 11px;
            color: #666;
        }}

        .code-block {{
            background: #f4f4f4;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
    </style>
</head>
<body>
    <header>
        <h1>🔄 PyRewind Trace Viewer</h1>
        <div class="header-info">
            <div>
                <strong>Function:</strong> {qualname}
            </div>
            <div>
                <strong>Total Steps:</strong> {len(steps)}
            </div>
            <div>
                <strong>Result:</strong> {result_repr[:50]}{"..." if len(str(result_repr)) > 50 else ""}
            </div>
            <div>
                <strong>Exception:</strong> {exception["type_name"] if exception else "None"}
            </div>
        </div>
    </header>

    <div class="container">
        <div class="sidebar">
            <div class="search-box">
                <input type="text" id="search" placeholder="Search steps..." />
            </div>
            <ul class="step-list" id="stepList">
                {steps_html}
            </ul>
        </div>

        <div class="main">
            <div class="step-details" id="stepDetails">
                <p style="text-align: center; color: #999; margin-top: 40px;">
                    Select a step to view details
                </p>
            </div>
            <footer>
                PyRewind v2 • Generated on execution trace
            </footer>
        </div>
    </div>

    <script>
        const stepsData = {json.dumps(steps, default=str)};
        const exceptionData = {json.dumps(exception, default=str)};
        const resultRepr = {json.dumps(result_repr)};

        function formatLocals(locals) {{
            let html = '<table class="locals-table"><tr><th>Variable</th><th>Value</th></tr>';
            for (const [key, value] of Object.entries(locals)) {{
                const valueRepr = JSON.stringify(value);
                html += `<tr><td>${{key}}</td><td class="code-block">${{valueRepr}}</td></tr>`;
            }}
            html += '</table>';
            return html;
        }}

        function showStep(index) {{
            const step = stepsData[index];
            if (!step) return;

            let html = `
                <div class="step-header">
                    <div>
                        <label>Step ID</label>
                        <value>${{step.step_id}}</value>
                    </div>
                    <div>
                        <label>File</label>
                        <value>${{step.filename.split('\\\\').pop()}}</value>
                    </div>
                    <div>
                        <label>Function</label>
                        <value>${{step.function}}</value>
                    </div>
                    <div>
                        <label>Line</label>
                        <value>${{step.line_no}}</value>
                    </div>
                </div>
            `;

            if (step.locals_snapshot && Object.keys(step.locals_snapshot).length > 0) {{
                html += '<div class="locals-section">';
                html += '<div class="locals-title">📦 Local Variables</div>';
                html += formatLocals(step.locals_snapshot);
                html += '</div>';
            }}

            if (index === stepsData.length - 1) {{
                html += '<div class="result-section">';
                html += '<strong>✓ Function Result</strong>';
                html += `<div class="code-block">${{resultRepr}}</div>`;
                html += '</div>';
            }}

            if (exceptionData && index === stepsData.length - 1) {{
                html += '<div class="exception-section">';
                html += '<strong>✗ Exception</strong>';
                html += `<div class="code-block">${{exceptionData.type_name}}: ${{exceptionData.message}}</div>`;
                html += '</div>';
            }}

            document.getElementById('stepDetails').innerHTML = html;

            // Update active step in sidebar
            document.querySelectorAll('.step-item').forEach((el, i) => {{
                el.classList.toggle('active', i === index);
            }});
        }}

        function initializeSteps() {{
            const stepList = document.getElementById('stepList');
            stepList.innerHTML = '';

            stepsData.forEach((step, index) => {{
                const li = document.createElement('li');
                li.className = 'step-item';
                li.innerHTML = `<strong>Step ${{step.step_id}}</strong><br/>${{step.function}} @ ${{step.line_no}}`;
                li.onclick = () => showStep(index);
                stepList.appendChild(li);
            }});

            // Show first step
            if (stepsData.length > 0) {{
                showStep(0);
            }}
        }}

        document.getElementById('search').addEventListener('keyup', (e) => {{
            const query = e.target.value.toLowerCase();
            document.querySelectorAll('.step-item').forEach((el, i) => {{
                const text = el.textContent.toLowerCase();
                el.style.display = text.includes(query) ? '' : 'none';
            }});
        }});

        // Initialize on load
        initializeSteps();
    </script>
</body>
</html>
"""
        return html

    def _build_steps_html(self, steps: list[dict[str, Any]]) -> str:
        """Build HTML for step list."""
        html = ""
        for i, step in enumerate(steps):
            func = step.get("function", "unknown")
            line = step.get("line_no", 0)
            html += f"""<li class="step-item" onclick="showStep({i})">
                <strong>Step {step.get('step_id', i)}</strong><br/>
                <span style="color: #666; font-size: 11px;">{func} @ {line}</span>
            </li>
"""
        return html

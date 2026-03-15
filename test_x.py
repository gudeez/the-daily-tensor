#!/usr/bin/env python3
"""Test X scraping in isolation. Outputs results to localhost:8888"""
import http.server
import json
from sources.x import fetch_x_posts

print("Fetching X posts...\n")
posts = fetch_x_posts()

# Build a simple HTML report
rows = ""
for i, p in enumerate(posts, 1):
    spam_class = ""
    rows += f"""
    <tr>
        <td>{i}</td>
        <td><a href="{p['url']}" target="_blank">@{p['author']}</a></td>
        <td>{p['summary'][:200]}</td>
        <td>{p['engagement']}</td>
        <td>{p['velocity']:.0f}</td>
        <td>{p['hours_old']}h</td>
        <td>{p.get('likes',0)} / {p.get('retweets',0)} / {p.get('replies',0)}</td>
    </tr>"""

html = f"""<!DOCTYPE html>
<html>
<head>
<title>X Scraper Test</title>
<style>
    body {{ font-family: monospace; background: #1a1a1a; color: #e0e0e0; padding: 20px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #333; padding: 8px; text-align: left; font-size: 13px; }}
    th {{ background: #2a2a2a; color: #00ff88; }}
    tr:hover {{ background: #222; }}
    a {{ color: #4a9eff; }}
    h1 {{ color: #00ff88; }}
    .stats {{ color: #888; margin-bottom: 20px; }}
</style>
</head>
<body>
<h1>X Scraper Test Results</h1>
<div class="stats">{len(posts)} posts found | Min engagement: 50 | Spam filtered</div>
<table>
<tr><th>#</th><th>Author</th><th>Content</th><th>Engagement</th><th>Velocity</th><th>Age</th><th>L/RT/R</th></tr>
{rows}
</table>
</body>
</html>"""

# Serve it
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())
    def log_message(self, *args):
        pass

server = http.server.HTTPServer(("0.0.0.0", 8888), Handler)
print(f"\nResults at http://localhost:8888")
print("Ctrl+C to stop\n")
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.shutdown()

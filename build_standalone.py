#!/usr/bin/env python3
# 将 index.html / styles.css / app.js 合并为单文件 index-standalone.html
# 使用普通字符串替换（避免 re.sub 把代码中的反斜杠当成转义）
import pathlib

base = pathlib.Path(__file__).parent
html = (base / "index.html").read_text(encoding="utf-8")
css = (base / "styles.css").read_text(encoding="utf-8")
js = (base / "app.js").read_text(encoding="utf-8")

# 注入样式
html = html.replace(
    '<link rel="stylesheet" href="styles.css" />',
    f"<style>\n{css}\n</style>",
    1,
)

# 注入脚本
html = html.replace(
    '<script src="app.js"></script>',
    f"<script>\n{js}\n</script>",
    1,
)

out = base / "index-standalone.html"
out.write_text(html, encoding="utf-8")
print(f"standalone written: {out.stat().st_size} bytes")

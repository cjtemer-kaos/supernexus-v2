#!/bin/bash
# Quick test for Chinese translation

echo "🇨🇳 Building Chinese version..."
cd /Users/shgao/logs/25.05.28tooluniverse/ToolUniverse/docs

# Build Chinese
make -e SPHINXOPTS="-D language='zh_CN'" html

echo ""
echo "✅ Chinese version built!"
echo "📂 Location: _build/html/index.html"
echo ""
echo "🌍 To switch back to English, run: make html"
echo "💡 To see translations in action, check:"
echo "   - Navigation sections (🚀 快速开始, 🤖 构建 AI 科学家, etc.)"
echo ""

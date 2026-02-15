#!/bin/bash

# Script to convert all markdown files to HTML with preserved links
# Links to .md files will automatically become .html links
#
# Usage: Run from the repository root or from scripts/ directory
#   ./scripts/convert_to_html.sh
#   OR
#   cd scripts && ./convert_to_html.sh

# Detect repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Directory paths
DOCS_DIR="docs"
HTML_DIR="html"

echo "Repository root: $REPO_ROOT"
echo "Converting markdown from: $DOCS_DIR/"
echo "Output HTML to: $HTML_DIR/"
echo ""

# Create output directory for HTML files
mkdir -p "$HTML_DIR"

# CSS styling
cat > "$HTML_DIR/style.css" << 'EOF'
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.6;
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem;
    color: #24292e;
    background-color: #ffffff;
}

h1, h2, h3, h4, h5, h6 {
    margin-top: 24px;
    margin-bottom: 16px;
    font-weight: 600;
    line-height: 1.25;
}

h1 { font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
h3 { font-size: 1.25em; }

code {
    background-color: #f6f8fa;
    border-radius: 3px;
    font-size: 85%;
    margin: 0;
    padding: 0.2em 0.4em;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
}

pre {
    background-color: #f6f8fa;
    border-radius: 3px;
    font-size: 85%;
    line-height: 1.45;
    overflow: auto;
    padding: 16px;
}

pre code {
    background-color: transparent;
    border: 0;
    display: inline;
    line-height: inherit;
    margin: 0;
    overflow: visible;
    padding: 0;
    word-wrap: normal;
}

table {
    border-collapse: collapse;
    border-spacing: 0;
    margin-bottom: 16px;
}

table th, table td {
    border: 1px solid #dfe2e5;
    padding: 6px 13px;
}

table tr {
    background-color: #fff;
    border-top: 1px solid #c6cbd1;
}

table tr:nth-child(2n) {
    background-color: #f6f8fa;
}

a {
    color: #0366d6;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

blockquote {
    border-left: 4px solid #dfe2e5;
    color: #6a737d;
    padding: 0 1em;
    margin: 0 0 16px 0;
}

hr {
    border: 0;
    border-top: 1px solid #eaecef;
    margin: 24px 0;
}
EOF

echo "Converting markdown files to HTML..."
echo "========================================================================"

# Counter
total=0
success=0

# Function to get relative CSS path based on directory depth
get_css_path() {
    local file_path="$1"
    local depth=$(echo "$file_path" | tr -cd '/' | wc -c)
    local css_path=""
    for ((i=0; i<depth; i++)); do
        css_path="../$css_path"
    done
    echo "${css_path}style.css"
}

# Convert each markdown file recursively from docs/
find "$DOCS_DIR" -name "*.md" -type f | while read mdfile; do
    # Remove docs/ prefix for relative path
    relative_path="${mdfile#$DOCS_DIR/}"

    total=$((total + 1))

    # Preserve directory structure in output
    htmlfile="$HTML_DIR/${relative_path%.md}.html"
    htmldir="$(dirname "$htmlfile")"

    # Create directory if it doesn't exist
    mkdir -p "$htmldir"

    echo "Converting: $mdfile -> $htmlfile"

    # Get appropriate CSS path based on depth
    css_path=$(get_css_path "$relative_path")

    # Use pandoc to convert, with automatic link conversion
    pandoc "$mdfile" \
        -f gfm \
        -t html \
        --standalone \
        --css "$css_path" \
        --metadata pagetitle="${relative_path%.md}" \
        -o "$htmlfile"

    if [ $? -eq 0 ]; then
        # Post-process: Convert all .md links to .html links
        sed -i 's/href="\([^"]*\)\.md"/href="\1.html"/g' "$htmlfile"
        sed -i 's/href="\([^"]*\)\.md#/href="\1.html#/g' "$htmlfile"
        success=$((success + 1))
    else
        echo "  ERROR: Failed to convert $mdfile"
    fi
done

echo ""
echo "========================================================================"
echo "Conversion complete!"
echo "Successfully converted markdown files to HTML"
echo "Output directory: $REPO_ROOT/$HTML_DIR/"
echo ""
echo "To start browsing:"
echo "  Open: $HTML_DIR/00_START_HERE.html"
echo ""
echo "Or use:"
echo "  xdg-open $HTML_DIR/00_START_HERE.html"
echo ""
echo "Directory structure:"
echo "  - Main entry: $HTML_DIR/00_START_HERE.html"
echo "  - Quick starts: $HTML_DIR/quick_start_*.html"
echo "  - Foundations: $HTML_DIR/01_foundations/"
echo "  - Intermediate: $HTML_DIR/02_intermediate/"
echo "  - Specialized: $HTML_DIR/03_specialized/"
echo "  - Reference: $HTML_DIR/04_reference/"
echo ""
echo "All links between documents have been automatically updated from .md to .html"

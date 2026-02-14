#!/bin/bash

# Script to convert all markdown files to HTML with preserved links
# Links to .md files will automatically become .html links

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create output directory for HTML files
mkdir -p html_output

# CSS styling
cat > html_output/style.css << 'EOF'
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
echo "======================================"

# Counter
total=0
success=0

# Convert each markdown file
for mdfile in *.md; do
    if [ -f "$mdfile" ]; then
        total=$((total + 1))
        htmlfile="html_output/${mdfile%.md}.html"

        echo "Converting: $mdfile -> $htmlfile"

        # Use pandoc to convert, with automatic link conversion
        # The -f gfm enables GitHub Flavored Markdown
        # The -t html enables HTML output
        # --standalone creates a complete HTML document
        # --css links to our stylesheet
        # --metadata pagetitle sets the page title
        # --toc adds table of contents for files with headers

        pandoc "$mdfile" \
            -f gfm \
            -t html \
            --standalone \
            --css style.css \
            --metadata pagetitle="${mdfile%.md}" \
            --toc \
            --toc-depth=3 \
            -o "$htmlfile"

        if [ $? -eq 0 ]; then
            # Post-process: Convert all .md links to .html links
            sed -i 's/href="\([^"]*\)\.md"/href="\1.html"/g' "$htmlfile"
            sed -i 's/href="\([^"]*\)\.md#/href="\1.html#/g' "$htmlfile"
            success=$((success + 1))
        else
            echo "  ERROR: Failed to convert $mdfile"
        fi
    fi
done

echo ""
echo "======================================"
echo "Conversion complete!"
echo "Successfully converted: $success/$total files"
echo "Output directory: $SCRIPT_DIR/html_output/"
echo ""
echo "To view, open: html_output/00_MASTER_INDEX.html"
echo "All links between documents have been automatically updated from .md to .html"

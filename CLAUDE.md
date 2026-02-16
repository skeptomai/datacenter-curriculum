# Project Context for Claude

## Project Overview

This is a comprehensive datacenter infrastructure curriculum covering virtualization, networking, storage, and containers.

## Repository Structure

```
docs/
├── 00_START_HERE.md           # Entry point for learners
├── 01_foundations/            # Foundational concepts
│   ├── 01_virtualization_basics/
│   └── 02_networking_basics/
├── 02_intermediate/           # Intermediate topics
├── 03_advanced/              # Advanced topics
├── 04_containers/            # Container technology
│   ├── 01_fundamentals/
│   │   ├── 01_cgroups_namespaces.md
│   │   ├── 02_union_filesystems.md
│   │   ├── 03_container_vs_vm.md
│   │   └── 04_container_storage.md
│   └── 02_runtimes/
└── 05_advanced_topics/

html/                         # Auto-generated HTML documentation
scripts/
├── convert_to_html.sh       # Markdown → HTML conversion
└── generate_pdf.sh          # Complete curriculum PDF generation
```

## GitHub Actions & Publishing

**⚠️ IMPORTANT:** This repository has GitHub Actions configured for automatic publishing.

### Auto-Publishing Workflow

- **Workflow file:** `.github/workflows/deploy-pages.yml`
- **Trigger:** Automatic on every push to `master` branch
- **What it does:**
  1. Converts all markdown files to HTML using `pandoc`
  2. Generates navigation and styling
  3. Deploys to GitHub Pages
  4. Typical run time: 2-3 minutes

**When you commit and push changes to `master`, the documentation will automatically be published to GitHub Pages.**

You can monitor workflow status at:
```
https://github.com/skeptomai/datacenter-curriculum/actions
```

### Manual Triggering

The workflow can also be manually triggered from the GitHub Actions tab using the `workflow_dispatch` event.

## Documentation Standards

### Content Rules

1. **Expand acronyms on first use** - All technical acronyms must be expanded when first introduced (e.g., "VT-x (Intel Virtualization Technology for x86)")

2. **YAML frontmatter required** - Every document must include:
   ```yaml
   ---
   level: foundational|intermediate|advanced
   estimated_time: XX min
   prerequisites:
     - path/to/prerequisite.md
   next_recommended:
     - path/to/next.md
   tags: [tag1, tag2, tag3]
   ---
   ```

3. **Clear learning objectives** - Start each document with concrete learning objectives

4. **Hands-on focus** - Include practical examples, commands, and exercises

5. **Visual aids** - Use ASCII diagrams for architecture and flow illustrations

6. **Comparison tables** - Use markdown tables for feature comparisons

### Document Structure Pattern

```markdown
---
# YAML frontmatter
---

# Title

**Learning Objectives:**
- Understand X
- Explain Y
- Apply Z

---

## Introduction

Context and motivation...

## Part 1: Core Concept

Detailed explanation...

### Subsection

Examples...

---

## Part 2: Next Concept

...

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| ...     | ...     |

---

## What You've Learned

✅ Checklist of concepts covered

---

## Hands-On Resources

> 💡 **Want more?** For comprehensive resources across all topics, see:
> **→ [Complete Resources](../00_RESOURCES.md)** 📚

- Link to external resource
- Another resource

---

## Next Steps

**Continue learning:**
→ [Next Topic](path.md)

**Related topics:**
→ [Related Topic](path.md)
```

## Git Workflow

### Commit Message Style

Based on recent commits, use descriptive multi-line commit messages:

```
Brief summary line (50-70 chars)

Detailed explanation organized by topic area:
- Specific change 1
  - Sub-detail
  - Sub-detail
- Specific change 2
  - Sub-detail

Include line counts for major additions.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### When to Commit

- After completing a coherent unit of work (section, document, or related changes)
- Group related changes together (e.g., all acronym expansions in one commit)
- Don't commit partial/broken work

## Current Focus Areas

### Recent Improvements (Feb 2026)

1. **Acronym Expansion** - Systematically expanded all technical acronyms in virtualization docs
2. **Historical Context** - Added timeline context for VT-x/EPT/NPT introduction
3. **Linux Capabilities** - Added comprehensive section on container privilege control
4. **Container Storage** - Created complete guide to volumes, bind mounts, tmpfs
5. **Unshare Tutorial** - Added hands-on guide to manual container creation

### Active Topics

- Container fundamentals (cgroups, namespaces, capabilities, storage)
- Virtualization hardware (VT-x, EPT, VM exits)
- Practical hands-on examples and tutorials

## Building the Documentation

### Generate HTML

```bash
./scripts/convert_to_html.sh
```

This converts all markdown in `docs/` to HTML in `html/`.

### Generate Complete PDF

```bash
./scripts/generate_pdf.sh
```

This creates `datacenter-curriculum-complete.pdf` with the entire curriculum.

## Tips for Working with This Codebase

1. **Always check existing content** before creating new sections to avoid duplication
2. **Maintain consistent style** - follow existing patterns for headers, code blocks, diagrams
3. **Cross-reference related content** - use relative links between related topics
4. **Test examples** - ensure command examples are accurate and work
5. **Consider the learner's journey** - content should build progressively from fundamentals to advanced
6. **Remember auto-publishing** - changes pushed to master go live automatically!

## Contact & Repository

- **Repository:** https://github.com/skeptomai/datacenter-curriculum
- **GitHub Pages:** (auto-published from master branch)

#!/usr/bin/env python3
"""
Generate a single combined PDF from all curriculum markdown files.
Follows the pedagogical structure from 00_START_HERE.md.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).parent.parent
DOCS_DIR = REPO_ROOT / "docs"
OUTPUT_DIR = REPO_ROOT / "pdf_output"

# Curriculum structure - order matters!
CURRICULUM_ORDER = [
    # Introduction
    ("00_START_HERE.md", "Introduction"),

    # Part I: Foundations
    ("01_foundations/01_virtualization_basics/01_the_ring0_problem.md", "Part I: Foundations"),
    ("01_foundations/01_virtualization_basics/02_hardware_solution.md", None),
    ("01_foundations/01_virtualization_basics/03_vm_exit_basics.md", None),

    ("01_foundations/02_datacenter_topology/01_modern_topology.md", None),
    ("01_foundations/02_datacenter_topology/02_server_hierarchy.md", None),
    ("01_foundations/02_datacenter_topology/03_3tier_vs_spine_leaf.md", None),
    ("01_foundations/02_datacenter_topology/04_ecmp_load_balancing.md", None),

    # Part II: Intermediate
    ("02_intermediate/01_advanced_networking/01_vlan_vs_vxlan.md", "Part II: Intermediate Topics"),
    ("02_intermediate/01_advanced_networking/02_overlay_mechanics.md", None),

    ("02_intermediate/02_rdma/01_rdma_fundamentals.md", None),
    ("02_intermediate/02_rdma/02_protocol_variants.md", None),
    ("02_intermediate/02_rdma/03_converged_ethernet.md", None),
    ("02_intermediate/02_rdma/04_numa_considerations.md", None),

    ("02_intermediate/03_complete_virtualization/01_evolution_complete.md", None),
    ("02_intermediate/03_complete_virtualization/02_exit_minimization.md", None),
    ("02_intermediate/03_complete_virtualization/03_hardware_optimizations.md", None),
    ("02_intermediate/03_complete_virtualization/04_device_passthrough.md", None),

    # Part III: Containers
    ("04_containers/01_fundamentals/01_cgroups_namespaces.md", "Part III: Containers"),
    ("04_containers/01_fundamentals/02_union_filesystems.md", None),
    ("04_containers/01_fundamentals/03_container_vs_vm.md", None),

    ("04_containers/02_runtimes/01_runtime_landscape.md", None),
    ("04_containers/02_runtimes/02_docker_containerd.md", None),
    ("04_containers/02_runtimes/03_kata_gvisor.md", None),
    ("04_containers/02_runtimes/04_runtime_comparison.md", None),

    ("04_containers/03_orchestration/01_kubernetes_architecture.md", None),
    ("04_containers/03_orchestration/02_pods_workloads.md", None),
    ("04_containers/03_orchestration/03_services_networking.md", None),
    ("04_containers/03_orchestration/04_scheduling_resources.md", None),
    ("04_containers/03_orchestration/05_storage_volumes.md", None),
    ("04_containers/03_orchestration/06_production_patterns.md", None),

    ("04_containers/04_networking/01_cni_deep_dive.md", None),
    ("04_containers/04_networking/02_calico_vs_cilium.md", None),
    ("04_containers/04_networking/03_ebpf_networking.md", None),
    ("04_containers/04_networking/04_service_mesh.md", None),
    ("04_containers/04_networking/05_network_policies_advanced.md", None),

    ("04_containers/05_security/01_image_security.md", None),
    ("04_containers/05_security/02_runtime_security.md", None),
    ("04_containers/05_security/03_pod_security.md", None),
    ("04_containers/05_security/04_supply_chain.md", None),

    # Part IV: Specialized Topics
    ("05_specialized/01_storage/01_pfc_dcb_storage.md", "Part IV: Specialized Topics"),

    ("05_specialized/02_overlay_networking/01_vxlan_geneve_bgp.md", None),
    ("05_specialized/02_overlay_networking/02_bgp_communities_rr.md", None),
    ("05_specialized/02_overlay_networking/03_rr_session_cardinality.md", None),
    ("05_specialized/02_overlay_networking/04_ovs_control_data.md", None),
    ("05_specialized/02_overlay_networking/05_ovs_cilium_geneve.md", None),
    ("05_specialized/02_overlay_networking/06_openflow_precompile.md", None),
    ("05_specialized/02_overlay_networking/07_prepopulated_vs_learning.md", None),

    ("05_specialized/03_serverless/01_firecracker_relationship.md", None),
    ("05_specialized/03_serverless/02_firecracker_deep_dive.md", None),
    ("05_specialized/03_serverless/03_firecracker_virtio.md", None),

    ("05_specialized/04_cpu_memory/01_tlb_ept_explained.md", None),
    ("05_specialized/04_cpu_memory/02_tlb_capacity_limits.md", None),

    ("05_specialized/05_compatibility/01_kvm_compat.md", None),
    ("05_specialized/05_compatibility/02_compat_vs_kvm_compat.md", None),
    ("05_specialized/05_compatibility/03_compat_examples.md", None),

    # Part V: Reference Materials
    ("01_foundations/00_VIRTUALIZATION_RESOURCES.md", "Part V: Reference Materials"),
    ("02_intermediate/00_NETWORKING_RESOURCES.md", None),
    ("04_containers/00_LEARNING_RESOURCES.md", None),

    ("06_reference/decision_frameworks/01_virtualization_primer.md", None),
    ("06_reference/learning_resources/01_learning_kvm.md", None),
    ("06_reference/learning_resources/02_networking_acronyms.md", None),
    ("06_reference/setup_guides/01_macos_kernel_setup.md", None),
    ("06_reference/setup_guides/02_external_drive_setup.md", None),
]


def strip_yaml_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from markdown content."""
    if content.startswith('---\n'):
        parts = content.split('---\n', 2)
        if len(parts) >= 3:
            return parts[2]
    return content


def adjust_heading_levels(content: str, increase_by: int = 1) -> str:
    """Increase all heading levels by the specified amount."""
    def replace_heading(match):
        hashes = match.group(1)
        text = match.group(2)
        new_hashes = '#' * (len(hashes) + increase_by)
        return f"{new_hashes} {text}"

    return re.sub(r'^(#{1,6})\s+(.+)$', replace_heading, content, flags=re.MULTILINE)


def strip_unicode_for_latex(content: str) -> str:
    """
    LuaLaTeX handles most Unicode natively, so we keep it minimal.
    Only replace smart quotes and escape special LaTeX characters.
    """
    # Replace smart quotes
    replacements = {
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
    }

    for char, replacement in replacements.items():
        content = content.replace(char, replacement)

    # Escape dollar signs that aren't already part of LaTeX math
    # This is a simple approach - escape all standalone $
    import re
    # Don't touch already escaped dollar signs or those in math blocks
    # Just escape isolated dollar signs
    content = re.sub(r'(?<!\\)\$(?!\$)', r'\\$', content)

    return content


def fix_internal_links(content: str, current_file: str) -> str:
    """
    Convert internal markdown links to work within a single document.
    Transform [text](path/to/file.md) to [text](#heading-anchor)
    """
    # For now, just remove .md extensions and convert to lowercase anchors
    # This is a simplified approach - proper implementation would need link mapping
    def replace_link(match):
        text = match.group(1)
        url = match.group(2)

        # Skip external links
        if url.startswith('http://') or url.startswith('https://'):
            return match.group(0)

        # Skip anchor-only links
        if url.startswith('#'):
            return match.group(0)

        # Convert relative .md links to anchors
        if url.endswith('.md'):
            # Extract filename and create anchor
            filename = Path(url).stem
            anchor = filename.lower().replace('_', '-')
            return f"[{text}](#{anchor})"

        return match.group(0)

    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, content)


def create_title_page() -> str:
    """Generate the title page content."""
    return """---
title: "Datacenter Infrastructure: A Comprehensive Learning Guide"
subtitle: "Virtualization, Networking, and Container Technologies"
author: "The datacenter-curriculum project"
date: "2026-02-15"
toc: true
toc-depth: 3
numbersections: true
documentclass: book
papersize: letter
geometry: margin=1in
fontsize: 11pt
linkcolor: blue
urlcolor: blue
---

\\newpage

"""


def combine_documents() -> str:
    """Combine all curriculum documents in order."""
    combined = create_title_page()
    current_part = None

    for file_path, part_name in CURRICULUM_ORDER:
        full_path = DOCS_DIR / file_path

        if not full_path.exists():
            print(f"Warning: {file_path} not found, skipping")
            continue

        print(f"Adding: {file_path}")

        # Add part header if this starts a new part
        if part_name:
            if current_part is not None:
                combined += "\n\\newpage\n\n"
            combined += f"# {part_name}\n\n"
            current_part = part_name

        # Read and process the document
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Strip YAML frontmatter
        content = strip_yaml_frontmatter(content)

        # Strip Unicode characters LaTeX can't handle
        content = strip_unicode_for_latex(content)

        # Increase heading levels (# becomes ##, etc.)
        content = adjust_heading_levels(content, increase_by=1)

        # Fix internal links
        content = fix_internal_links(content, file_path)

        # Add to combined document
        combined += content
        combined += "\n\n\\newpage\n\n"

    return combined


def generate_pdf():
    """Generate the final PDF using pandoc."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    combined_md = OUTPUT_DIR / "combined.md"
    output_pdf = OUTPUT_DIR / "datacenter-infrastructure-curriculum.pdf"

    print("Combining documents...")
    combined_content = combine_documents()

    print(f"Writing combined markdown to {combined_md}")
    with open(combined_md, 'w', encoding='utf-8') as f:
        f.write(combined_content)

    print(f"Generating PDF with pandoc + LuaLaTeX...")
    import subprocess

    # Use LuaLaTeX with proper Unicode support
    pdf_cmd = [
        'pandoc',
        str(combined_md),
        '-o', str(output_pdf),
        '--pdf-engine=lualatex',
        '--pdf-engine-opt=--shell-escape',
        '--toc',
        '--toc-depth=3',
        '--number-sections',
        '-V', 'geometry:margin=1in',
        '-V', 'fontsize=11pt',
        '-V', 'documentclass=book',
        '-V', 'linkcolor=blue',
        '-V', 'urlcolor=blue',
        '-V', 'mainfont=Liberation Serif',
        '-V', 'sansfont=Liberation Sans',
        '-V', 'monofont=Liberation Mono',
        '--highlight-style=tango',
    ]

    try:
        print("Running pandoc (this may take a few minutes)...")
        result = subprocess.run(pdf_cmd, check=True, capture_output=True, text=True)
        print(f"✅ Success! PDF generated at: {output_pdf}")
        print(f"   File size: {output_pdf.stat().st_size / 1024 / 1024:.1f} MB")
        return output_pdf
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating PDF:")
        print(e.stderr)

        # Fallback: try without custom fonts
        print("\nRetrying without custom fonts...")
        pdf_cmd_simple = [
            'pandoc',
            str(combined_md),
            '-o', str(output_pdf),
            '--pdf-engine=lualatex',
            '--toc',
            '--toc-depth=3',
            '--number-sections',
            '-V', 'geometry:margin=1in',
            '-V', 'fontsize=11pt',
            '--highlight-style=tango',
        ]
        try:
            result = subprocess.run(pdf_cmd_simple, check=True, capture_output=True, text=True)
            print(f"✅ Success! PDF generated at: {output_pdf}")
            print(f"   File size: {output_pdf.stat().st_size / 1024 / 1024:.1f} MB")
            return output_pdf
        except subprocess.CalledProcessError as e2:
            print(f"❌ Error:")
            print(e2.stderr)
            return None


if __name__ == '__main__':
    print("Datacenter Infrastructure Curriculum - PDF Generator")
    print("=" * 60)
    generate_pdf()

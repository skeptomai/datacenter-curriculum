# Container & Orchestration Curriculum: Execution Plan

**Status:** Planning Phase
**Target Completion:** 8-12 weeks (part-time) or 3-4 weeks (full-time)
**Estimated Content:** 22 documents, 20-25 hours learning time
**Created:** 2026-02-14

---

## 📋 Executive Summary

This plan outlines the complete workflow for researching, analyzing, designing, and creating a comprehensive container and orchestration curriculum to add to the datacenter-curriculum repository. The goal is to maintain the same pedagogical quality and structure as existing content while covering the full container stack from Linux primitives through Kubernetes production deployments.

---

## Phase 1: Research & Source Identification (Week 1)

### Objective
Identify authoritative, technically accurate sources across all container topics.

### 1.1 Official Documentation Review

**Primary Sources:**
- [ ] **OCI Specifications**
  - Runtime spec (runc)
  - Image spec (container images)
  - Distribution spec (registries)
  - Source: https://opencontainers.org/

- [ ] **Kubernetes Official Docs**
  - Concepts documentation
  - Reference documentation
  - Design proposals (KEPs)
  - Source: https://kubernetes.io/docs/

- [ ] **Container Runtime Documentation**
  - containerd: https://containerd.io/docs/
  - CRI-O: https://cri-o.io/
  - Docker: https://docs.docker.com/
  - runc: https://github.com/opencontainers/runc

- [ ] **Linux Kernel Documentation**
  - cgroups v1/v2: https://docs.kernel.org/admin-guide/cgroup-v2.html
  - Namespaces: https://man7.org/linux/man-pages/man7/namespaces.7.html
  - Capabilities: https://man7.org/linux/man-pages/man7/capabilities.7.html

- [ ] **CNI & Networking**
  - CNI spec: https://github.com/containernetworking/cni
  - Cilium docs: https://docs.cilium.io/
  - Calico docs: https://docs.tigera.io/calico/latest/about/
  - Istio docs: https://istio.io/latest/docs/

- [ ] **Secure Runtimes**
  - Kata Containers: https://katacontainers.io/docs/
  - gVisor: https://gvisor.dev/docs/

### 1.2 Technical Books & Deep Dives

**Recommended Reading:**
- [ ] **"Kubernetes in Action" (2nd Edition)** - Marko Lukša
  - Comprehensive K8s coverage
  - Practical examples
  - Good for understanding pod patterns

- [ ] **"Container Security"** - Liz Rice
  - Security fundamentals
  - Linux primitives deep dive
  - Runtime security practices

- [ ] **"Kubernetes Patterns"** - Bilgin Ibryam & Roland Huß
  - Production patterns
  - Design principles
  - Best practices

- [ ] **"Docker Deep Dive"** - Nigel Poulton
  - Container fundamentals
  - Image building
  - Networking basics

- [ ] **"Programming Kubernetes"** - Michael Hausenblas & Stefan Schimanski
  - API internals
  - Controller patterns
  - Extension mechanisms

### 1.3 Academic & Research Papers

**Key Papers:**
- [ ] **"My VM is Lighter (and Safer) than your Container"** - Kata Containers whitepaper
- [ ] **"gVisor: Building and Battle Testing a Userspace OS in Go"** - Google
- [ ] **"Borg, Omega, and Kubernetes"** - Google (CACM 2016)
- [ ] **"Large-scale cluster management at Google with Borg"** - EuroSys 2015
- [ ] **Performance studies**:
  - Container networking performance comparisons
  - Storage overhead studies
  - Security isolation benchmarks

### 1.4 Industry Blogs & Engineering Posts

**Authoritative Sources:**
- [ ] **CNCF Blog** - Cloud Native Computing Foundation
- [ ] **Kubernetes Blog** - Official K8s engineering posts
- [ ] **Google Cloud Blog** - GKE, container internals
- [ ] **Red Hat Blog** - OpenShift, container security
- [ ] **Cilium Blog** - eBPF networking deep dives
- [ ] **Isovalent Blog** - eBPF, service mesh
- [ ] **Aqua Security Blog** - Container security research

### 1.5 Source Code Review (When Needed)

**Critical Codebases:**
- [ ] runc - https://github.com/opencontainers/runc
- [ ] containerd - https://github.com/containerd/containerd
- [ ] kubernetes - https://github.com/kubernetes/kubernetes (specific components)
- [ ] CNI plugins - https://github.com/containernetworking/plugins
- [ ] Cilium - https://github.com/cilium/cilium

**Focus:** Understanding implementation details for deep-dive sections, not general explanations.

---

## Phase 2: Content Analysis & Gap Mapping (Week 2)

### Objective
Analyze existing curriculum, identify integration points, and map out precise content requirements.

### 2.1 Existing Content Audit

**Task:** Review all existing documents for container-related content

- [ ] **Search existing docs** for container mentions
- [ ] **Identify integration points**:
  - Virtualization fundamentals (isolation comparison)
  - Networking overlays (CNI integration)
  - RDMA (storage backends)
  - Firecracker (Kata Containers connection)
- [ ] **Document cross-reference opportunities**
- [ ] **Identify content to avoid duplicating**

### 2.2 Learning Objectives Definition

**For Each Subsection, Define:**

**01_fundamentals/**
- [ ] After reading, learner should understand:
  - How cgroups limit resources (CPU, memory, I/O)
  - How namespaces provide isolation (6+ types)
  - How union filesystems enable layering
  - Difference between container and VM isolation
  - Security boundaries and limitations

**02_runtimes/**
- [ ] After reading, learner should understand:
  - Runtime hierarchy (CRI → high-level → low-level)
  - When to use which runtime
  - How Kata/gVisor provide stronger isolation
  - Performance vs security tradeoffs
  - Integration with orchestrators

**03_orchestration/**
- [ ] After reading, learner should understand:
  - K8s architecture and component roles
  - Pod design patterns and lifecycle
  - How services provide stable networking
  - Scheduling decisions and constraints
  - Storage provisioning and persistence
  - Production deployment patterns

**04_networking/**
- [ ] After reading, learner should understand:
  - CNI plugin architecture
  - How eBPF accelerates networking
  - Service mesh value proposition
  - Network policy enforcement
  - Integration with underlay (VXLAN, BGP)

**05_security/**
- [ ] After reading, learner should understand:
  - Image security pipeline
  - Runtime security controls
  - Pod security standards
  - RBAC and least privilege
  - Supply chain security

### 2.3 Prerequisites Mapping

**Create dependency graph:**

```
Container Fundamentals
  ← Prerequisites: 01_foundations/01_virtualization_basics (isolation concepts)
  ← Prerequisites: Basic Linux knowledge (assumed)
      ↓
Container Runtimes
  ← Prerequisites: Container Fundamentals
      ↓
Kubernetes Orchestration
  ← Prerequisites: Container Runtimes
  ← Prerequisites: 01_foundations/02_datacenter_topology (networking basics)
      ↓
Container Networking
  ← Prerequisites: Kubernetes Orchestration
  ← Prerequisites: 02_intermediate/01_advanced_networking (VXLAN, overlays)
      ↓
Container Security
  ← Prerequisites: Container Fundamentals
  ← Prerequisites: Kubernetes Orchestration
  ← Can be read in parallel with Container Networking
```

### 2.4 Time Estimates & Complexity Grading

**Assign to each document:**
- [ ] Estimated reading time (20-90 min)
- [ ] Difficulty level (foundational/intermediate/specialized)
- [ ] Prerequisites list
- [ ] Next recommended reading
- [ ] Relevant tags

---

## Phase 3: Curriculum Design & Structuring (Week 3)

### Objective
Design pedagogical structure, create outlines, and plan document flow.

### 3.1 Structural Decision

**DECISION POINT:** Choose structure option:

**Option A: Specialized Section** (03_specialized/06_containers/)
- Pros: Aligns with current "specialized topics" pattern
- Cons: Implies containers are "advanced" when they're now fundamental

**Option B: Top-Level Section** (04_containers/, renumber existing)
- Pros: Recognizes containers as major infrastructure category
- Cons: Requires renumbering 03_specialized → 05_specialized, 04_reference → 06_reference

**RECOMMENDATION: Option B** - Containers are too fundamental and widely-used to be buried in "specialized."

### 3.2 Document Outlines

**For each of 22 documents, create:**

- [ ] **Working title**
- [ ] **Learning objectives** (3-5 bullet points)
- [ ] **Section outline** (H2/H3 structure)
- [ ] **Key diagrams needed** (ASCII art placeholders)
- [ ] **Integration points** (links to other docs)
- [ ] **Examples to include**
- [ ] **Common pitfalls to address**
- [ ] **Estimated word count** (3000-6000 words per doc)

**Example Outline Template:**
```markdown
# [Document Title]

## Learning Objectives
- Understand X
- Explain Y
- Compare Z vs W
- Apply pattern P

## Section 1: Introduction
- What problem does this solve?
- Historical context (brief)

## Section 2: Fundamental Concepts
- Core mechanism
- How it works (step-by-step)
- Diagram

## Section 3: Deep Dive
- Implementation details
- Performance considerations
- Tradeoffs

## Section 4: Practical Usage
- Common patterns
- Anti-patterns
- Examples

## Section 5: Integration & Context
- How it fits in the stack
- Related technologies
- Cross-references

## Quick Reference
- Key commands
- Configuration examples
- Decision matrix

## What You've Learned
- Summary checklist

## Next Steps
- Next recommended reading
```

### 3.3 Learning Path Integration

**Update 00_START_HERE.md outline:**

- [ ] Add "Path 5: Container Platform Engineer (20-25 hours)"
- [ ] Define entry points for different backgrounds:
  - Complete beginners → Start with virtualization foundations first
  - Developers familiar with Docker → Skip fundamentals, start with orchestration
  - Network engineers → Focus on container networking
  - Security engineers → Focus on container security
- [ ] Create "hybrid paths":
  - Full Stack + Containers (complete datacenter + cloud native)
  - Network Engineer + Container Networking
  - Security Engineer + Container Security

### 3.4 Quick Start Guide

- [ ] **Create: quick_start_containers.md** (2-3 hours)
  - Container fundamentals (30 min)
  - Docker/containerd basics (20 min)
  - Kubernetes essentials (60 min)
  - Networking overview (20 min)
  - Security basics (20 min)

---

## Phase 4: Content Creation Workflow (Weeks 4-10)

### Objective
Write high-quality, pedagogically-structured content following established patterns.

### 4.1 Writing Methodology

**For Each Document:**

1. **Research & Notes** (2-3 hours)
   - Review all sources
   - Take structured notes
   - Identify gaps in understanding
   - Research specific edge cases

2. **First Draft** (4-6 hours)
   - Follow outline structure
   - Focus on clarity over completeness
   - Include diagrams (ASCII art)
   - Add examples and code snippets
   - Write naturally, edit later

3. **Technical Review** (1-2 hours)
   - Verify technical accuracy
   - Test code examples
   - Check for outdated information
   - Validate against official docs

4. **Pedagogical Edit** (1-2 hours)
   - Ensure progressive complexity
   - Check for assumed knowledge
   - Verify prerequisites are clear
   - Improve explanations
   - Add analogies where helpful

5. **Integration** (1 hour)
   - Add YAML frontmatter
   - Create cross-references
   - Update directory README
   - Add to learning paths

6. **Final Polish** (1 hour)
   - Grammar and style
   - Formatting consistency
   - Link validation
   - Generate HTML test

**Total per document: 10-15 hours** × 22 documents = **220-330 hours**

### 4.2 Content Creation Order

**PHASE 4A: Fundamentals (Week 4-5)**
- [ ] 01_cgroups_namespaces.md
- [ ] 02_union_filesystems.md
- [ ] 03_container_vs_vm.md
- Update: 01_fundamentals/README.md

**PHASE 4B: Runtimes (Week 5-6)**
- [ ] 01_runtime_landscape.md
- [ ] 02_docker_containerd.md
- [ ] 03_kata_gvisor.md
- [ ] 04_runtime_comparison.md
- Update: 02_runtimes/README.md

**PHASE 4C: Orchestration Part 1 (Week 6-7)**
- [ ] 01_kubernetes_architecture.md
- [ ] 02_pods_workloads.md
- [ ] 03_services_networking.md

**PHASE 4D: Orchestration Part 2 (Week 7-8)**
- [ ] 04_scheduling_resources.md
- [ ] 05_storage_volumes.md
- [ ] 06_production_patterns.md
- Update: 03_orchestration/README.md

**PHASE 4E: Networking (Week 8-9)**
- [ ] 01_cni_overview.md
- [ ] 02_calico_vs_cilium.md
- [ ] 03_ebpf_networking.md
- [ ] 04_service_mesh.md
- [ ] 05_network_policies.md
- Update: 04_networking/README.md

**PHASE 4F: Security (Week 9-10)**
- [ ] 01_image_security.md
- [ ] 02_runtime_security.md
- [ ] 03_pod_security.md
- [ ] 04_supply_chain.md
- Update: 05_security/README.md

**PHASE 4G: Top-level Integration (Week 10)**
- [ ] Create: docs/04_containers/README.md
- [ ] Create: quick_start_containers.md
- [ ] Update: 00_START_HERE.md (add Path 5)
- [ ] Update: README.md (mention container content)

### 4.3 Quality Standards Checklist

**Every document must have:**
- [ ] YAML frontmatter (level, time, prerequisites, next_recommended, tags)
- [ ] Clear learning objectives at top
- [ ] Progressive complexity (simple → complex)
- [ ] At least 2 diagrams (ASCII art minimum)
- [ ] Practical examples
- [ ] "What You've Learned" summary at end
- [ ] "Next Steps" with cross-references
- [ ] Quick reference section
- [ ] No assumptions of prior knowledge beyond prerequisites
- [ ] Gender-neutral language
- [ ] Consistent terminology with existing docs

### 4.4 Example Code & Diagrams

**Standards:**
- [ ] All code examples must be tested
- [ ] Use recent versions (K8s 1.29+, containerd 1.7+)
- [ ] Include comments explaining non-obvious parts
- [ ] Provide context (what this achieves)
- [ ] ASCII diagrams for architecture
- [ ] Consider SVG for complex flows (optional enhancement)

---

## Phase 5: Review & Integration (Week 11)

### Objective
Ensure quality, consistency, and proper integration with existing content.

### 5.1 Technical Review

- [ ] **Self-review checklist** (all 22 documents)
  - Technical accuracy verified
  - Code examples tested
  - No broken links
  - Consistent with official docs

- [ ] **Cross-reference validation**
  - All prerequisites exist
  - All "next recommended" links valid
  - Integration points with existing content work

- [ ] **Terminology consistency**
  - Consistent with existing docs
  - Glossary terms aligned
  - Acronyms expanded on first use

### 5.2 Pedagogical Review

- [ ] **Learning flow validation**
  - Can a beginner follow Path 5 successfully?
  - Are prerequisites actually sufficient?
  - Is complexity progression smooth?

- [ ] **Time estimate validation**
  - Read each document, time it
  - Adjust estimates if needed
  - Total path time reasonable?

- [ ] **Compare to existing content quality**
  - Same depth and clarity?
  - Similar structure and style?
  - Matching pedagogical approach?

### 5.3 Integration Testing

- [ ] **Generate HTML** for all new documents
  - Run scripts/convert_to_html.sh
  - Check formatting
  - Validate all links work in HTML

- [ ] **Test all learning paths**
  - Follow Path 5 start to finish (reading key sections)
  - Test hybrid paths
  - Verify cross-references to existing content

- [ ] **Update master documents**
  - 00_START_HERE.md updated
  - README.md mentions container content
  - REORGANIZATION_SUMMARY.md updated with new stats

---

## Phase 6: Publication & Refinement (Week 12)

### Objective
Publish content and gather initial feedback for improvements.

### 6.1 Git Workflow

- [ ] **Create feature branch**
  ```bash
  git checkout -b feature/container-curriculum
  ```

- [ ] **Commit structure changes**
  - Renumber existing directories (03→05, 04→06)
  - Create 04_containers/ structure
  - Commit: "Prepare structure for container curriculum"

- [ ] **Commit content in logical chunks**
  - Commit: "Add container fundamentals (3 docs)"
  - Commit: "Add container runtimes (4 docs)"
  - Commit: "Add Kubernetes orchestration (6 docs)"
  - Commit: "Add container networking (5 docs)"
  - Commit: "Add container security (4 docs)"
  - Commit: "Add container learning path and quick start"

- [ ] **Test full build**
  ```bash
  ./scripts/convert_to_html.sh
  xdg-open html/00_START_HERE.html
  ```

- [ ] **Push to GitHub**
  ```bash
  git push -u origin feature/container-curriculum
  ```

- [ ] **Create pull request**
  - Comprehensive description
  - Document count and hours added
  - Links to key new documents
  - Request feedback

### 6.2 Documentation Updates

- [ ] **Update ONGOING_TASKS.md**
  - Mark container curriculum as [x] Completed
  - Add any new ideas that emerged

- [ ] **Update README.md**
  - Add container topics to "Topics Covered"
  - Update stats (49→71 documents, +20-25 hours)
  - Mention Path 5 in learning paths

- [ ] **Create CONTAINER_CURRICULUM_SUMMARY.md**
  - Similar to REORGANIZATION_SUMMARY.md
  - Document the addition process
  - List all new files
  - Provide usage examples

### 6.3 Announcement & Feedback

- [ ] **Merge pull request** (after review)
- [ ] **Tag release** (optional)
  ```bash
  git tag -a v2.0.0 -m "Added comprehensive container & orchestration curriculum"
  git push origin v2.0.0
  ```

- [ ] **Update GitHub repo description**
  - Add "containers" and "kubernetes" to topics

- [ ] **Solicit feedback**
  - GitHub Discussions post
  - Share with relevant communities
  - Gather improvement suggestions

### 6.4 Iterative Improvements

- [ ] **Monitor for issues**
  - Technical errors
  - Unclear explanations
  - Missing prerequisites

- [ ] **Rapid iteration** (first 2 weeks post-launch)
  - Fix any critical issues immediately
  - Improve clarity based on feedback
  - Add missing examples

- [ ] **Schedule review** (3 months post-launch)
  - Check for outdated information
  - Update K8s versions
  - Refresh examples

---

## Success Metrics

**Quantitative:**
- [ ] 22 documents created (20-25 hours content)
- [ ] All documents have YAML frontmatter
- [ ] 100% of internal links work
- [ ] 0 broken links in HTML generation
- [ ] Path 5 completable in stated time (±20%)

**Qualitative:**
- [ ] Content quality matches existing curriculum
- [ ] Pedagogical structure maintained
- [ ] Positive community feedback
- [ ] Used as learning resource by others
- [ ] Contributions from community

---

## Risk Management

### Risk 1: Scope Creep
**Mitigation:** Strict outline adherence, time-box each document to 10-15 hours max

### Risk 2: Outdated Information
**Mitigation:** Use official docs as source of truth, document K8s version (1.29+), plan quarterly updates

### Risk 3: Inconsistent Quality
**Mitigation:** Use checklist for every document, maintain same structure, self-review before committing

### Risk 4: Poor Integration
**Mitigation:** Plan integration points upfront, test cross-references thoroughly, update master index

### Risk 5: Time Overrun
**Mitigation:** Track time per document, adjust scope if needed, prioritize core content over edge cases

---

## Resource Requirements

**Time Investment:**
- Research: 40 hours
- Analysis: 20 hours
- Design: 30 hours
- Writing: 220-330 hours
- Review: 30 hours
- **Total: 340-450 hours** (8-12 weeks part-time, 3-4 weeks full-time)

**Tools Needed:**
- [ ] Access to Kubernetes cluster (for testing examples) - minikube/kind/k3s sufficient
- [ ] Container runtime (Docker Desktop or containerd+nerdctl)
- [ ] Text editor with markdown support
- [ ] pandoc (already required for HTML generation)
- [ ] Git / GitHub account (already have)

**Optional:**
- [ ] Draw.io or Excalidraw (for complex diagrams)
- [ ] Kubernetes books (listed in Phase 1)
- [ ] CNCF landscape familiarity

---

## Timeline Summary

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1 | Research | Source list, reading notes |
| 2 | Analysis | Gap map, prerequisites graph, learning objectives |
| 3 | Design | 22 document outlines, learning path design |
| 4-5 | Writing | Fundamentals (3 docs) + Runtimes (4 docs) |
| 6-7 | Writing | Orchestration Part 1 (3 docs) |
| 7-8 | Writing | Orchestration Part 2 (3 docs) |
| 8-9 | Writing | Networking (5 docs) |
| 9-10 | Writing | Security (4 docs) + Integration docs |
| 11 | Review | Quality checks, integration testing |
| 12 | Publication | Git workflow, PR, announcement |

**TOTAL: 12 weeks part-time (15-20 hours/week) OR 3-4 weeks full-time**

---

## Next Immediate Steps

1. [ ] **Decide on structure** (Option A vs B) - RECOMMENDED: Option B
2. [ ] **Begin Phase 1 research** - Start with OCI and K8s official docs
3. [ ] **Set up test environment** - Install minikube or kind for examples
4. [ ] **Create tracking system** - Use GitHub project or simple checklist
5. [ ] **Block calendar time** - Schedule dedicated writing sessions

---

**Ready to proceed?** Start with Phase 1: Research & Source Identification.

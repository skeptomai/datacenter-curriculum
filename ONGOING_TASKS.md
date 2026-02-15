# Ongoing Tasks & Future Enhancements

**Repository:** https://github.com/skeptomai/datacenter-curriculum
**Live Site:** https://skeptomai.github.io/datacenter-curriculum/
**Last Updated:** 2026-02-15

---

## ✅ Recent Session Accomplishments (2026-02-15)

### Major Features Completed
- [x] **Container curriculum fully implemented** (22 documents, Path 5)
  - Container fundamentals (cgroups, namespaces, union filesystems)
  - Container runtimes (Docker, containerd, Kata, gVisor)
  - Kubernetes orchestration (6 documents)
  - Container networking (CNI, Calico, Cilium, eBPF, service mesh)
  - Container security (image scanning, runtime security, Pod Security, supply chain)
  - Quick start guide for containers

- [x] **Learning paths restructured** (containers-first approach)
  - Path 1: Container Platform Engineer (most common use case)
  - Path 2: Virtualization Engineer
  - Path 3: Network Engineer
  - Path 4: Storage Engineer
  - Path 5: Full Stack Platform Engineer (includes all topics)

- [x] **Replaced time estimates with depth indicators**
  - 📖 Foundational → 📚 Intermediate → 🔬 Specialized → 📋 Reference
  - More honest approach (no false precision)
  - Aligns with document-level metadata

- [x] **GitHub Pages automated deployment**
  - GitHub Actions workflow for automatic HTML generation
  - Deploys on every push to master branch
  - Site live at: https://skeptomai.github.io/datacenter-curriculum/

- [x] **Documentation improvements**
  - Updated README.md with new paths and depth indicators
  - Updated 00_START_HERE.md with complete container curriculum
  - Cleaner introduction text (removed "high-quality", reordered topics)
  - Expanded all acronyms at first use across 22 container documents (33 unique acronyms)
  - Enhanced veth pair explanations with TAP/TUN comparisons and namespace boundary diagrams

---

## 🎯 Immediate Next Steps

### 1. GitHub Repository Configuration
- [ ] **Add repository topics/tags** for discoverability:
  - containers
  - kubernetes
  - virtualization
  - networking
  - datacenter
  - rdma
  - kvm
  - learning-resources
  - infrastructure
  - curriculum
  - educational

### 2. Contributing Guidelines
- [ ] **Create CONTRIBUTING.md** with:
  - How to propose new content
  - Style guidelines for documentation
  - YAML frontmatter requirements
  - Pull request process
  - Code of conduct

### 3. Issue Templates
- [ ] **Create GitHub issue templates** for:
  - Content corrections/updates
  - New topic requests
  - Translation proposals
  - General questions

### 4. Quality Assurance
- [ ] **Add link checker** to GitHub Actions
  - Validate all cross-references work
  - Check external links
  - Report broken links in CI

---

## 📚 Content Enhancements

### Interactive Features
- [ ] **Interactive HTML Navigation**
  - Add progress tracking to HTML version
  - Create interactive curriculum map
  - Add search functionality
  - Implement bookmarking system

### Learning Path Badges
- [ ] **Visual Progress Indicators**
  - Visual progress indicators
  - Completion certificates
  - Milestone achievements

### Content Updates
- [ ] **Keep Technology Info Current**
  - Update link speeds as standards evolve (25G → 100G → 400G)
  - Add examples as technology evolves
  - Update protocol versions (RDMA, VXLAN, etc.)
  - Refresh performance benchmarks

### Expand Specialized Topics
- [ ] **Add New Specialization Areas**
  - Security (encryption, attestation, isolation)
  - Observability (monitoring, tracing, metrics)
  - GPU virtualization and passthrough
  - Disaggregated infrastructure
  - Edge computing and 5G integration

### Translation
- [ ] **Multi-language Support**
  - Translate to other languages
  - Maintain same structure across languages
  - Add language switcher to HTML version

---

## 🛠️ Technical Improvements

### Build System
- [ ] **Enhance Build Scripts**
  - Add makefile for common operations
  - Create dev container for consistent environment
  - Add validation scripts (YAML validator, markdown linter)

### Documentation Quality
- [ ] **Add More Diagrams**
  - Convert ASCII art to SVG/PNG where helpful
  - Add architecture diagrams
  - Create flowcharts for decision trees

### Testing & Validation
- [ ] **Automated Testing**
  - Validate all cross-references work
  - Check YAML frontmatter consistency
  - Verify depth indicators are appropriate
  - Test HTML generation on all platforms

---

## 🎓 Educational Features

### Hands-on Labs
- [ ] **Create Practical Exercises**
  - Lab environments (KVM setup, network simulation, K8s clusters)
  - Step-by-step tutorials
  - Quiz questions at end of sections
  - Practice problems

### Video Content
- [ ] **Companion Videos** (if desired)
  - Record walkthroughs of complex topics
  - Create visual explanations of diagrams
  - Interview experts

### Community
- [ ] **Build Learning Community**
  - Set up discussion board (GitHub Discussions)
  - Create study group template
  - Office hours or Q&A sessions

---

## 📊 Analytics & Feedback

### Tracking
- [ ] **Add Analytics** (optional)
  - Track which paths are most popular
  - Monitor completion rates
  - Identify difficult sections

### Feedback Mechanism
- [ ] **Collect User Feedback**
  - Add feedback forms
  - Create user survey
  - Track issue patterns

---

## 🔄 Maintenance

### Regular Updates
- [ ] **Quarterly Review**
  - Check for outdated information
  - Update link speeds and standards
  - Refresh examples
  - Review container/K8s version updates

### Community Contributions
- [ ] **Review and Merge PRs**
  - Monitor pull requests
  - Review contributed content
  - Update acknowledgments

---

## 💡 Future Ideas (Brainstorming)

- **Mobile-friendly version** with app
- **Spaced repetition system** for key concepts
- **Integration with learning platforms** (Coursera, edX)
- **Certification program** (unofficial)
- **Podcast series** covering each learning path
- **Jupyter notebooks** for interactive exploration
- **Docker-based lab environment** for hands-on practice
- **AI chatbot** to answer questions about content
- **Comparison tables** for technology selection
- **Real-world case studies** from production environments
- **Integration with LLM tools** for personalized learning paths

---

## 📝 Notes

### Principles to Maintain
- Keep pedagogical structure (foundations → intermediate → specialized)
- Maintain explicit prerequisites
- Use depth indicators (not time estimates)
- Follow YAML frontmatter conventions
- Keep all original content in archive/
- No bragging or self-promotion in documentation

### When Adding New Content
1. Determine appropriate level (foundational/intermediate/specialized/reference)
2. Add YAML frontmatter with all required fields
3. Update relevant learning paths in 00_START_HERE.md
4. Add to appropriate directory README
5. Test HTML generation
6. Update REORGANIZATION_SUMMARY.md if structure changes

---

## 📈 Current State Summary

**Total Documents:** 66 (59 learning documents + 7 quick starts/guides)
**Learning Paths:** 5 complete paths
**GitHub Pages:** ✅ Live and auto-deploying
**Structure:** ✅ Complete and pedagogically organized
**Container Coverage:** ✅ Comprehensive (22 documents)
**Status:** ✅ Production-ready

---

**Status Key:**
- [x] Completed
- [ ] Not started
- [~] In progress
- [-] Blocked/Deferred

# Ongoing Tasks & Future Enhancements

**Repository:** https://github.com/skeptomai/datacenter-curriculum
**Last Updated:** 2026-02-14

---

## 🎯 Immediate Next Steps

### 1. GitHub Repository Configuration
- [ ] **Add repository topics/tags** for discoverability:
  - virtualization
  - networking
  - datacenter
  - rdma
  - kvm
  - learning-resources
  - infrastructure
  - curriculum
  - educational

### 2. GitHub Pages Setup
- [ ] **Enable GitHub Pages** to host HTML documentation
  - Configure to serve from `/docs` or use GitHub Actions to build
  - Add custom domain (optional)
  - Enable HTTPS

### 3. Contributing Guidelines
- [ ] **Create CONTRIBUTING.md** with:
  - How to propose new content
  - Style guidelines for documentation
  - YAML frontmatter requirements
  - Pull request process
  - Code of conduct

### 4. Issue Templates
- [ ] **Create GitHub issue templates** for:
  - Content corrections/updates
  - New topic requests
  - Translation proposals
  - General questions

### 5. Automation
- [ ] **Add GitHub Actions workflow** to:
  - Auto-generate HTML on push
  - Validate YAML frontmatter
  - Check for broken links
  - Deploy to GitHub Pages

---

## 📚 Content Enhancements (From Original Plan)

### Interactive Features
- [ ] **Interactive HTML Navigation**
  - Add progress tracking to HTML version
  - Create interactive curriculum map
  - Add search functionality
  - Implement bookmarking system

### Learning Path Badges
- [ ] **Visual Progress Indicators**
  - Add visual progress indicators
  - Create completion certificates
  - Track time investment
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
  - Container networking (CNI, service mesh)
  - GPU virtualization and passthrough
  - Disaggregated infrastructure

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
  - Add validation scripts (link checker, YAML validator)

### Documentation Quality
- [ ] **Add More Diagrams**
  - Convert ASCII art to SVG/PNG where helpful
  - Add architecture diagrams
  - Create flowcharts for decision trees

### Testing & Validation
- [ ] **Create Test Suite**
  - Validate all cross-references work
  - Check YAML frontmatter consistency
  - Verify time estimates are reasonable
  - Test HTML generation on all platforms

---

## 🎓 Educational Features

### Hands-on Labs
- [ ] **Create Practical Exercises**
  - Lab environments (KVM setup, network simulation)
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

---

## 📝 Notes

### Principles to Maintain
- Keep pedagogical structure (foundations → intermediate → specialized)
- Maintain explicit prerequisites
- Preserve time estimates
- Follow YAML frontmatter conventions
- Keep all original content in archive/

### When Adding New Content
1. Determine appropriate level (foundational/intermediate/specialized/reference)
2. Add YAML frontmatter with all required fields
3. Update relevant learning paths in 00_START_HERE.md
4. Add to appropriate directory README
5. Test HTML generation
6. Update REORGANIZATION_SUMMARY.md if structure changes

---

**Status Key:**
- [ ] Not started
- [x] Completed
- [~] In progress
- [-] Blocked/Deferred

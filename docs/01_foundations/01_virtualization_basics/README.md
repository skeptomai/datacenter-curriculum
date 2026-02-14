# Virtualization Fundamentals

**The essential trilogy - read in order (1.5 hours total)**

These three documents form a cohesive introduction to modern virtualization. Each builds on the previous one.

---

## The Learning Sequence

### 1. [The Ring-0 Problem](01_the_ring0_problem.md) 🎯 START HERE
**Time:** 20 minutes

**The Question:** How do you run TWO operating systems, both wanting Ring-0 access, on ONE CPU?

**What you'll learn:**
- CPU privilege rings (Ring 0 vs Ring 3)
- Why x86 wasn't designed for virtualization
- The fundamental dilemma of isolation vs privileges

**Outcome:** Understand the core problem virtualization must solve

---

### 2. [Hardware Solution (VT-x/AMD-V)](02_hardware_solution.md)
**Time:** 30 minutes | **Prerequisites:** Document #1

**The Answer:** Create TWO separate Ring-0 environments with hardware support

**What you'll learn:**
- VMX Root Mode vs VMX Non-Root Mode
- VMCS (Virtual Machine Control Structure)
- EPT/NPT (hardware two-level page tables)
- Why EPT eliminates 95% of VM exits
- 5 hardware mechanisms that make virtualization fast

**Outcome:** Understand how VT-x enables virtualization

---

### 3. [VM Exit Basics](03_vm_exit_basics.md)
**Time:** 25 minutes | **Prerequisites:** Document #2

**The Mechanism:** The 6-step cycle that makes virtualization work

**What you'll learn:**
- What triggers VM exits (10 common reasons)
- Step-by-step hardware mechanics
- VMCS structure and control fields
- Why exits cost ~2400 cycles
- Example: I/O port exit walkthrough

**Outcome:** Understand the fundamental virtualization mechanism

---

## After Completing This Track

**You'll understand:**
✅ Why virtualization needs hardware support
✅ How VT-x creates isolated environments
✅ How guest code transitions to hypervisor and back

**Next steps:**

**Continue Virtualization Path:**
→ [Complete Virtualization Evolution](../../02_intermediate/03_complete_virtualization/01_evolution_complete.md)
- See the full historical journey from VMware to SR-IOV

**Or Switch to Networking:**
→ [Datacenter Topology](../02_datacenter_topology/)
- Understand the physical infrastructure

**Or See Performance Details:**
→ [Exit Minimization](../../02_intermediate/03_complete_virtualization/02_exit_minimization.md)
- Why reducing exits matters and how

---

**📊 Completion:** Virtualization fundamentals complete!

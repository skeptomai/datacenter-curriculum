---
level: specialized
estimated_time: 90 min
prerequisites:
  - 02_intermediate/03_complete_virtualization/03_hardware_optimizations.md
next_recommended:
  - 05_specialized/04_cpu_memory/02_tlb_capacity_limits.md
tags: [virtualization, tlb, ept, npt, vpid, memory, performance]
---

# TLB and Page Walk Caching with EPT/NPT

## The Core Question

With two-level translation (guest page tables + EPT), how does the TLB cache work? Does it get flushed constantly?

**Short answer:** The TLB caches the **final result** (GVA → HPA), and with **VPID tagging**, no flush is needed on VM switches!

---

## Understanding the Translation Chain

### Without Virtualization (Normal)

```
Virtual Address → Physical Address

Example:
  VA: 0x401000
    ↓ TLB lookup
  PA: 0x8234000
  
TLB caches: VA 0x401000 → PA 0x8234000

Simple, one-level translation
```

---

### With EPT/NPT (Nested)

```
Guest Virtual Address (GVA)
    ↓ Guest Page Tables (4 levels)
Guest Physical Address (GPA)
    ↓ EPT/NPT (4 levels)
Host Physical Address (HPA)

Example:
  GVA: 0x401000
    ↓ Walk guest PT (4 levels)
  GPA: 0x10234000
    ↓ Walk EPT (4 levels)
  HPA: 0x8234000
  
Question: What does TLB cache?
```

---

## What the TLB Actually Caches

**The TLB caches the FINAL translation: GVA → HPA**

```
TLB Entry:
┌─────────────────────────────────────────┐
│ Virtual Address: 0x401000               │
│ Physical Address: 0x8234000 (HPA!)      │
│ Permissions: R/W/X                      │
│ Page Size: 4KB                          │
│ Tags: VPID, ASID, etc.                  │
└─────────────────────────────────────────┘

NOT cached: The intermediate GPA!

Why? Because what matters for memory access
is the final HPA. GPA is just an intermediate step.
```

---

## The Translation Process (Detailed)

### On TLB Miss

```
CPU needs to access GVA 0x401000:

Step 1: Check TLB
───────────────────
TLB lookup for 0x401000
  → Miss! Not in cache

Step 2: Hardware Page Walk (MMU does this automatically)
────────────────────────────────────────────────────────

Walk Guest Page Tables:
  1. Read guest CR3 → guest PML4 base (GPA)
     
  2. GPA of PML4 table → Need to translate to HPA!
     → Walk EPT to get HPA of guest PML4
     → Read guest PML4 entry → Get guest PDPT GPA
     
  3. GPA of PDPT → Need to translate to HPA!
     → Walk EPT to get HPA of guest PDPT
     → Read guest PDPT entry → Get guest PD GPA
     
  4. GPA of PD → Need to translate to HPA!
     → Walk EPT to get HPA of guest PD
     → Read guest PD entry → Get guest PT GPA
     
  5. GPA of PT → Need to translate to HPA!
     → Walk EPT to get HPA of guest PT
     → Read guest PT entry → Get GPA of actual page!
     
  6. GPA of data page (0x10234000) → Translate to HPA!
     → Walk EPT one more time
     → Get final HPA: 0x8234000

Worst case: 4 guest levels × 5 memory accesses each (EPT walk)
           = 20-24 memory accesses!

Step 3: Cache in TLB
────────────────────
TLB entry created:
  GVA 0x401000 → HPA 0x8234000
  
Next access to 0x401000:
  → TLB hit! Direct access
  → No page walk needed
  → 1 cycle instead of 24 memory accesses
```

---

## The Problem: TLB Invalidation

### Without VPID - Constant Flushing

```
Scenario: Two VMs running

VM1 TLB entries:
  GVA 0x1000 → HPA 0x5000 (VM1's memory)
  GVA 0x2000 → HPA 0x6000
  
VM2 TLB entries:
  GVA 0x1000 → HPA 0x9000 (VM2's memory)
  GVA 0x2000 → HPA 0xA000

Problem: Same GVA, different HPA!

Without tagging:
───────────────
1. VM1 running:
   - TLB has: 0x1000 → 0x5000
   
2. VM Exit (switch to VM2):
   - Must flush entire TLB!
   - Otherwise VM2 might use VM1's translations
   - Security issue: VM2 accessing VM1's memory!
   
3. VM2 running:
   - TLB empty (just flushed)
   - Every memory access = TLB miss
   - Expensive page walks
   
4. VM Exit (switch back to VM1):
   - Must flush entire TLB again!
   
Result: Constant TLB flushes
        Performance killer!
```

**Performance impact:**

```
Benchmark: VM switches (1000 times)

Without VPID:
  - Every switch: TLB flush
  - First 100 instructions after switch: All TLB misses
  - 100 × 24 memory accesses = 2400 memory accesses
  - 2400 × 100ns = 240μs overhead per switch
  - 1000 switches = 240ms overhead
  
With warm TLB (no flush):
  - Most accesses: TLB hit
  - Negligible overhead
  
TLB flush = 20-30% performance loss!
```

---

## The Solution: VPID (Virtual Processor ID)

### VPID Tagging

```
Extended TLB Entry Format:
┌─────────────────────────────────────────┐
│ VPID: 1                                 │ ← NEW!
│ Virtual Address: 0x1000                 │
│ Physical Address: 0x5000                │
│ Permissions: R/W/X                      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ VPID: 2                                 │ ← Different VPID!
│ Virtual Address: 0x1000                 │ ← Same VA!
│ Physical Address: 0x9000                │ ← Different PA!
│ Permissions: R/W/X                      │
└─────────────────────────────────────────┘

Both entries can coexist in TLB!
```

---

### How VPID Works

```
Setup:
──────
Hypervisor assigns VPIDs:
  VM1 → VPID 1
  VM2 → VPID 2
  Host → VPID 0

Each VMCS contains VPID field:
  VM1's VMCS: VPID = 1
  VM2's VMCS: VPID = 2

CPU tracks current VPID in hardware register
```

**VM Switch with VPID:**

```
1. VM1 running (VPID=1):
   ────────────────────
   TLB lookups filter by VPID=1:
     Access 0x1000:
       → Check TLB for (VPID=1, VA=0x1000)
       → Hit: 0x5000
       → Use 0x5000
   
2. VM Exit → VM2 Entry (switch to VPID=2):
   ──────────────────────────────────────
   VMRESUME instruction:
     - Load VPID=2 from VMCS
     - Update CPU's current VPID register
     - NO TLB FLUSH!
   
3. VM2 running (VPID=2):
   ────────────────────
   TLB lookups filter by VPID=2:
     Access 0x1000:
       → Check TLB for (VPID=2, VA=0x1000)
       → Hit: 0x9000
       → Use 0x9000
   
   TLB entry (VPID=1, VA=0x1000) still exists!
   But filtered out because current VPID != 1
   
4. VM Exit → VM1 Entry (switch back to VPID=1):
   ──────────────────────────────────────────
   VMRESUME:
     - Load VPID=1
     - NO TLB FLUSH!
   
   TLB still has (VPID=1, VA=0x1000) → 0x5000
   Immediate TLB hit!
```

---

### VPID Benefits

```
┌───────────────────────┬────────────┬─────────────┐
│ Scenario              │ Without    │ With VPID   │
│                       │ VPID       │             │
├───────────────────────┼────────────┼─────────────┤
│ VM switch overhead    │ ~500 cycles│ ~200 cycles │
│ TLB flush?            │ Yes        │ No          │
│ TLB misses after      │ 100%       │ ~5%         │
│ switch                │            │             │
│ Performance impact    │ 20-30%     │ 2-5%        │
└───────────────────────┴────────────┴─────────────┘

VPID enables:
✓ Different VMs can have overlapping GVA ranges
✓ TLB stays warm across VM switches
✓ Hypervisor can have its own VPID (host mode)
✓ Massive performance improvement (15-30%)
```

---

## Additional Page Walk Caches

**TLB is not the only cache!**

### The Page Walk Cache Hierarchy

```
1. TLB (Translation Lookaside Buffer)
   ────────────────────────────────
   Caches: Complete translations (GVA → HPA)
   Size: ~64-1024 entries per core
   Tagged: VPID, PCID, Global bit
   
2. Page Walk Cache (PWC) / Paging Structure Cache
   ─────────────────────────────────────────────
   Caches: Intermediate page table entries
   
   For guest page tables:
     GVA of PML4 entry → HPA of PML4 entry
     GVA of PDPT entry → HPA of PDPT entry
     GVA of PD entry → HPA of PD entry
     GVA of PT entry → HPA of PT entry
   
   Size: ~16-32 entries per level per core
   
3. EPT Page Walk Cache
   ───────────────────
   Caches: EPT intermediate translations
   
   For EPT:
     GPA of EPT PML4 → HPA of EPT PML4
     GPA of EPT PDPT → HPA of EPT PDPT
     ...
   
   Size: ~16-32 entries per level per core
```

---

### Why Multiple Caches Matter

**Scenario: TLB miss but PWC hit**

```
CPU accesses GVA 0x401000:

Step 1: Check TLB
  → Miss!
  
Step 2: Start page walk
  Need guest PML4 entry:
    Check PWC: (guest CR3, offset 0) → HPA of PML4 entry
    → Hit! Skip guest PML4 EPT walk (saved 5 memory accesses)
    
  Need guest PDPT entry:
    Check PWC: (PML4 GPA, offset 8) → HPA of PDPT entry  
    → Hit! Skip EPT walk (saved 5 more memory accesses)
    
  Need guest PD entry:
    Check PWC: (PDPT GPA, offset 16) → HPA of PD entry
    → Hit! Skip EPT walk (saved 5 more memory accesses)
    
  Need guest PT entry:
    Check PWC: (PD GPA, offset 24) → HPA of PT entry
    → Hit! Skip EPT walk (saved 5 more memory accesses)
    
  Need final page:
    Must walk EPT (no cache)
    → 5 memory accesses

Total: 5 memory accesses (vs 24 without PWC)

Update TLB with final translation
```

---

### Cache Invalidation

**When are these caches flushed?**

```
TLB flush triggers:
──────────────────
1. CR3 write (without PCID)
   → Flush all non-global TLB entries
   
2. INVLPG instruction
   → Flush specific page
   
3. INVPCID instruction
   → Selective invalidation by PCID/VPID
   
4. VM entry/exit (without VPID)
   → Full flush
   
5. EPT modifications
   → INVEPT instruction flushes EPT caches

With VPID:
  VM switches DON'T flush TLB!
  Only explicit invalidation instructions

Page Walk Cache flush:
─────────────────────
Typically flushed together with TLB
But sometimes preserved (implementation-specific)

EPT Page Walk Cache flush:
─────────────────────────
INVEPT instruction:
  - INVEPT type 1: Single-context invalidation
  - INVEPT type 2: All-context invalidation
```

---

## Real-World Example: Context Switch

### Without VPID

```
Timeline:
────────
T=0: VM1 running, TLB warm
     Access 0x1000 → TLB hit → 1 cycle
     
T=1: VM Exit (interrupt)
     - Save VM1 state
     - Flush TLB (security!)
     - Load host state
     
T=2: Host (KVM) running, TLB cold
     Access 0x401000 → TLB miss → Page walk → 24 accesses
     Access 0x402000 → TLB miss → Page walk → 24 accesses
     ...
     TLB gradually warms up
     
T=3: VM Entry (VM2)
     - Flush TLB (security!)
     - Load VM2 state
     
T=4: VM2 running, TLB cold
     Access 0x1000 → TLB miss → Page walk → 24 accesses
     Access 0x2000 → TLB miss → Page walk → 24 accesses
     ...
     TLB gradually warms up
     
T=5: VM Exit
     - Flush TLB
     
T=6: VM Entry (VM1)
     - Flush TLB
     
T=7: VM1 running, TLB cold AGAIN
     Access 0x1000 → TLB miss → Page walk → 24 accesses
     
Every VM switch: Cold TLB, massive overhead
```

---

### With VPID

```
Timeline:
────────
T=0: VM1 (VPID=1) running, TLB warm
     Access 0x1000 → TLB hit (VPID=1) → 1 cycle
     
T=1: VM Exit (interrupt)
     - Save VM1 state
     - NO TLB FLUSH!
     - Switch to VPID=0 (host)
     
T=2: Host (VPID=0) running
     Access 0x401000:
       → Check TLB (VPID=0, VA=0x401000)
       → Miss (first time)
       → Page walk, cache result
     
     Access 0x401000 again:
       → TLB hit (VPID=0) → 1 cycle
     
     VM1's entries still in TLB (VPID=1)!
     
T=3: VM Entry (VM2, VPID=2)
     - NO TLB FLUSH!
     - Switch to VPID=2
     
T=4: VM2 (VPID=2) running
     Access 0x1000:
       → Check TLB (VPID=2, VA=0x1000)
       → Miss (first time for VM2)
       → Page walk, cache result
     
     Access 0x1000 again:
       → TLB hit (VPID=2) → 1 cycle
     
     VM1's and Host's entries still in TLB!
     
T=5: VM Exit, VM Entry (VM1, VPID=1)
     - NO TLB FLUSH!
     - Switch to VPID=1
     
T=6: VM1 (VPID=1) running
     Access 0x1000:
       → Check TLB (VPID=1, VA=0x1000)
       → HIT! Entry from T=0 still there!
       → 1 cycle
     
TLB stays warm across switches!
All three contexts coexist in TLB!
```

---

## Performance Impact

**Benchmark: Rapid context switches**

```
Test: Switch between 4 VMs, 1000 switches each

Without VPID:
─────────────
Time: 850ms
Breakdown:
  - Context switch overhead: 100ms
  - TLB misses after switch: 750ms
  
TLB miss rate after switch: 95%

With VPID:
──────────
Time: 180ms
Breakdown:
  - Context switch overhead: 100ms
  - TLB misses after switch: 80ms
  
TLB miss rate after switch: 8%

Speedup: 4.7x improvement!
```

---

## Modern Enhancements

### PCID (Process-Context Identifier)

**Similar to VPID, but for processes within guest:**

```
Without PCID:
  Process switch within guest → CR3 write → TLB flush
  
With PCID:
  TLB entries tagged by PCID
  Multiple processes' TLB entries coexist
  No flush on process switch
  
Combined with VPID:
  TLB entry tagged: (VPID=1, PCID=5, VA=0x1000)
  Allows:
    - Multiple VMs
    - Multiple processes per VM
    - All with warm TLBs!
```

---

### Huge Pages

**Reduce TLB pressure:**

```
4KB pages:
  TLB entry covers: 4KB
  1GB memory: Needs 262,144 TLB entries
  TLB size: ~64-1024 entries
  TLB miss rate: High
  
2MB huge pages:
  TLB entry covers: 2MB
  1GB memory: Needs 512 TLB entries
  TLB miss rate: Much lower
  
1GB huge pages:
  TLB entry covers: 1GB
  1GB memory: Needs 1 TLB entry!
  TLB miss rate: Minimal
  
With EPT huge pages:
  Guest can use huge pages
  AND EPT can map with huge pages
  Double benefit!
```

---

## Summary

**Does TLB get flushed with EPT/NPT?**

**Without VPID: YES**
- Every VM switch → TLB flush
- 20-30% performance penalty
- TLB constantly cold

**With VPID: NO**
- TLB entries tagged by VPID
- Different VMs' entries coexist
- TLB stays warm
- 15-30% performance improvement

**What does TLB cache?**
- Final translation: GVA → HPA
- NOT the intermediate GPA
- Tagged with VPID (and PCID)

**Additional caching:**
- Page Walk Cache: Intermediate page table entries
- EPT Page Walk Cache: EPT intermediate entries
- Both reduce page walk overhead

**The innovation:** VPID allows multiple virtual address spaces (different VMs) to have TLB entries simultaneously, eliminating the need for flushes on context switches. This is critical for virtualization performance!

---

## Hands-On Resources

> 💡 **Want more?** This section shows the most essential resources for this topic.
> For a comprehensive list of tutorials, code repositories, and tools across all virtualization topics, see:
> **→ [Complete Virtualization Learning Resources](../../../01_foundations/00_VIRTUALIZATION_RESOURCES.md)** 📚

**Focused resources for TLB, EPT, and memory virtualization:**

- **[Intel SDM on EPT and TLB](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)** - Chapters 28-29: EPT and TLB management in virtualization
- **[KVM MMU Documentation](https://www.kernel.org/doc/html/latest/virt/kvm/mmu.html)** - Linux KVM memory management unit implementation details

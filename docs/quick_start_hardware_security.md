# Quick Start: Hardware Security & Trusted Boot

**⏱️ Time: 2 hours | 🎯 Goal: Rapid understanding of TPMs, measured boot, and Secure Boot**

This fast-track guide covers hardware roots of trust without the full depth of each
topic. For comprehensive understanding, follow the
[full hardware security specialization](05_specialized/06_hardware_security/).

---

## The Core Problem (15 minutes)

### Why a Dedicated Chip Instead of Just Better Encryption?

Read: [TPM Fundamentals](05_specialized/06_hardware_security/01_tpm_fundamentals.md)
**Sections 1-2 only**

**Key Takeaway:**
```
A TPM isn't "encrypted storage" — encryption just moves the secret-storage
problem to a different secret. A TPM's command set has NO "export the
private key" operation at all for keys marked fixedTPM.

Non-exportability is enforced by the protocol's design, not by policy.
```

---

## Key Hierarchy: EK, SRK, and Where the Attestation Key Comes From (20 minutes)

Read: [Key Hierarchy and Provisioning](05_specialized/06_hardware_security/02_key_hierarchy_and_provisioning.md)
**Focus on:**
- Section 2 (the four hierarchies)
- Section 3 (factory provisioning — the EK)
- Section 4 (why the Attestation Key is never the EK itself — the most commonly
  misunderstood part of this whole topic)

**Key Takeaways:**
```
Only ONE key is truly factory-provisioned: the Endorsement Key (EK).
Everything else is created later, by you or your OS, under the Storage hierarchy.

The Attestation Key (AK) is a SEPARATE, disposable signing key — never the EK:
- Privacy: signing everything with a permanent EK would make every device
  trackable forever
- Forgery prevention: a "restricted" key can only sign TPM-internal structures

Credential activation proves an AK is co-resident with a real EK, WITHOUT the
EK ever signing anything directly.
```

---

## Proving Boot State: Sealing, PCRs, and Quoting (20 minutes)

Read: [Sealing, Attestation, and PCRs](05_specialized/06_hardware_security/03_sealing_attestation_pcrs.md)
**Sections 1-3**

**Key Takeaway:**
```
PCR_new = Hash(PCR_old || measurement)   ← the ONLY write operation (extend)

Seal:   "release this secret only if PCRs match"   (local guarantee)
Unseal: hard refusal on mismatch, not garbage output
Quote:  signed PCR snapshot, sent to a REMOTE verifier, bound to a nonce

Extend-only = can't rewind to a more favorable value later.
```

---

## Not All TPMs Are Equal (15 minutes)

Read: [TPM Vendor Landscape](05_specialized/06_hardware_security/04_vendor_landscape_dtpm_vs_ftpm.md)
**Sections 2, 3, 5**

**Key Takeaway:**
```
Two independent axes of variance:
1. Form factor — discrete chip (Infineon, Nuvoton) vs. firmware TPM
   (Intel PTT, AMD fTPM) vs. die-integrated (Microsoft Pluton)
2. Spec/capability — TPM 1.2 vs. 2.0 is a fundamental model change, and even
   compliant 2.0 chips vary in algorithm support, NVRAM budget, certification

dTPM: strongest isolation, but exposes a bus that's been sniffed in practice
fTPM: no bus to sniff, but trust now includes CPU management firmware (ME/PSP)
Neither wins categorically — it depends on your threat model.
```

---

## Why Measurements Can't Be Faked (20 minutes)

Read: [Measured Boot](05_specialized/06_hardware_security/06_measured_boot.md)
**Sections 1-3**

**Key Takeaway:**
```
The TPM does NOT verify that a measurement is honest — it can't.

What actually prevents forged measurements: "measure before execute."
Malicious code never gets to run before it has already been measured by
something earlier — all the way back to the CRTM, which is anchored in
hardware immutability (or factory-fused signatures like Intel Boot Guard),
not in any earlier software's word.

Break this chain → you need to defeat hardware fuses, not exploit a bug.
```

---

## Secure Boot vs. Measured Boot (15 minutes)

Read: [Secure Boot](05_specialized/06_hardware_security/07_secure_boot.md)
**Sections 1 and 4**

**Key Takeaway:**
```
Measured Boot = detection  (record what ran; a verifier judges it LATER)
Secure Boot   = prevention (refuse to run anything unsigned, RIGHT NOW)

Why you need both: a validly-signed-but-OLD-and-vulnerable bootloader
PASSES Secure Boot (the signature is genuinely valid) but shows up as a
PCR mismatch in measured boot/attestation. Neither mechanism alone catches
everything.
```

---

## Optional: Seeing It in Production (15 minutes)

Skim: [Case Study: TPM-Backed Node Identity with SPIRE/SPIFFE](05_specialized/06_hardware_security/08_case_study_spire_tpm_devid.md)
**Sections 3 and 5**

**Key Takeaway:**
```
Credential activation isn't only for boot-state quoting — this real cluster
reuses it to prove DEVICE identity (via a DevID key) instead.

Real mixed-vendor hardware produced a real ~24-second-per-call performance
bug (on-chip RSA key generation), confirmed by watching the actual blocking
syscall — vendor variance is operational reality, not a spec-sheet footnote.
```

---

## Quick Reference: The Big Picture

```
┌─────────────────────────────────────────────────────┐
│ Q: What makes a TPM key "safe"?                      │
│ A: No command exists to export it — not policy,      │
│    the protocol itself has no such operation          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Q: Which key is factory-provisioned?                 │
│ A: Only the EK. The AK is created later and           │
│    certified against the EK via credential activation│
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Q: Why can't boot measurements be forged?             │
│ A: Measure-before-execute, anchored in an immutable   │
│    CRTM — not the TPM policing truthfulness            │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Q: Secure Boot vs. measured boot — why both?          │
│ A: Prevention catches unsigned code; detection catches│
│    validly-signed-but-outdated/vulnerable code        │
└─────────────────────────────────────────────────────┘
```

---

## What You've Learned

✅ **The Problem:** Keys that can be used but never read out, enforced by protocol design
✅ **The Hierarchy:** EK (factory) vs. AK (disposable, certified) vs. everyday application keys
✅ **The Mechanism:** PCR extend, seal/unseal, quote — all built on one irreversible hash-chain primitive
✅ **The Variance:** Form factor and spec/capability are two separate axes; neither dTPM nor fTPM wins categorically
✅ **The Trust Chain:** Measure-before-execute, anchored in hardware, is what actually stops forged measurements
✅ **The Complement:** Secure Boot (prevention) and measured boot (detection) catch different failure modes

---

## Next Steps

**Go Deeper:**
- Complete the [Hardware Security & Trusted Boot specialization](05_specialized/06_hardware_security/) (all 8 documents)
- See it applied to a real cluster: [Case Study: SPIRE/SPIFFE TPM DevID](05_specialized/06_hardware_security/08_case_study_spire_tpm_devid.md)

**Switch Topics:**
- [Quick Start: Virtualization](quick_start_virtualization.md) for the CPU/memory side of hardware-assisted security
- [Quick Start: Full Stack](quick_start_full_stack.md) for the complete datacenter picture

**Start Implementing:**
- [tpm2-tools](https://github.com/tpm2-software/tpm2-tools) for hands-on commands against real or simulated TPM hardware

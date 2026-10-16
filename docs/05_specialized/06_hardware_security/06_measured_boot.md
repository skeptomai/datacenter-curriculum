---
level: specialized
estimated_time: 50 min
prerequisites:
  - 05_specialized/06_hardware_security/03_sealing_attestation_pcrs.md
next_recommended:
  - 05_specialized/06_hardware_security/07_secure_boot.md
tags: [measured-boot, crtm, srtm, drtm, chain-of-trust, pcr, boot-guard]
---

# Measured Boot: Why the Measurements Can't Be Faked

## Learning Objectives

After reading this document, you will understand:
- Who measures the very first thing in the boot chain, and why that act itself is trustworthy
- The "measure before execute" principle and why it, not TPM policing, is what prevents forged measurements
- The full Static Root of Trust for Measurement (SRTM) boot chain, stage by stage
- How Dynamic Root of Trust for Measurement (DRTM) differs, and why it exists
- Why firmware updates routinely break sealed secrets, and what that implies in practice

## Prerequisites

Before reading this, you should understand:
- [Sealing, Attestation, and PCRs](03_sealing_attestation_pcrs.md) — PCR extend mechanics and why they can't be rewound

---

## 1. The Question This Document Actually Answers

The prior document established that PCRs are extend-only, so a *given sequence*
of measurements can't be rewound to an earlier value. But that leaves an open
question: **what stops someone from feeding the TPM a dishonest measurement in
the first place** — i.e., calling `PCR_Extend` with a hash claiming "I just ran
trusted bootloader X" while actually running malicious code Y?

The direct, slightly uncomfortable answer: **if you have code-execution access
at a given boot stage, you absolutely can call `TPM2_PCR_Extend` with any value
you want.** The TPM has no independent way to verify that the hash you hand it
actually corresponds to the code really running. The TPM does not — cannot —
police truthfulness of its inputs.

What makes measured boot trustworthy isn't the TPM checking your homework.
It's a structural rule enforced **outside** the TPM, by the sequencing of boot
itself:

> **Measure before execute, every single stage, with no exceptions — and
> make the very first measurer immutable.**

---

## 2. Measure Before Execute

Each stage of the boot chain, before handing control to the *next* stage,
measures that next stage and extends a PCR with the result — and only then
executes it:

```
Stage N (currently trusted, already measured by Stage N-1)
   │
   ├─ 1. Read Stage N+1's code/config into memory
   ├─ 2. Hash it
   ├─ 3. Extend the appropriate PCR with that hash
   └─ 4. ONLY THEN transfer control to Stage N+1
```

This ordering is the whole trick. Stage N+1 never gets to run *before* it has
been measured, so Stage N+1 — even if it's malicious — never has an
opportunity to extend the PCR itself claiming to be something else. By the
time malicious code could act, the true measurement of it is already
irreversibly folded into the PCR (recall: extend-only, can't rewind).

This pushes the trust question back one level: **can Stage N, the measurer, be
trusted to measure honestly?** Which pushes back to Stage N-1, and so on — all
the way to the very first stage, which cannot appeal to any earlier software
for its own trustworthiness.

---

## 3. The Core Root of Trust for Measurement (CRTM)

The first measurer is called the **CRTM** — typically a small piece of
boot firmware baked into the chipset/motherboard, often physically immutable
or cryptographically locked down so that **not even an attacker with full
software/OS access can modify it**:

```
┌───────────────────────────────────────────────┐
│ CRTM (Core Root of Trust for Measurement)      │
│ - First code to run, before anything else      │
│ - Immutable (ROM) or fused/signature-locked     │
│   (e.g., Intel Boot Guard burns a public key    │
│    into one-time programmable chipset fuses     │
│    at the factory — only firmware signed by      │
│    the matching private key is allowed to run    │
│    at all, not just measured)                   │
└──────────────────┬──────────────────────────────┘
                    │ measures, then executes
                    ▼
         Rest of UEFI firmware (PEI/DXE)
```

This is the actual anchor. You can't forge the CRTM's first measurement
because there is no earlier software layer an attacker could compromise to
tamper with it — the CRTM's trustworthiness comes from **hardware
immutability or factory-fused cryptographic enforcement**, not from a chain of
software vouching for it. Defeating this requires defeating the hardware
itself (an entirely different, far harder class of attack than exploiting a
software bug), which is precisely the point.

---

## 4. The Full SRTM Boot Chain

Putting it together, a typical **Static Root of Trust for Measurement (SRTM)**
chain — "static" because it starts at power-on and runs the entire sequence
every single boot, measuring everything along the way:

```
Power on
  │
  ▼
CRTM (immutable/fused) ──measures──▶ UEFI firmware volumes (PEI/DXE)
                                            │
                                            ▼ measures
                              Bootloader (shim → GRUB, or Windows Boot Manager)
                                            │
                                            ▼ measures
                                   OS loader / initrd
                                            │
                                            ▼ measures
                                      Kernel + modules
                                            │
                                            ▼ (optionally continues)
                                   Application-level attestation
```

Each arrow is a real `PCR_Extend` call, typically into specific, standardized
PCR indices (PCR 0 for CRTM/BIOS, PCR 2 for option ROMs, PCR 4 for the
bootloader, PCR 7 for Secure Boot state, and so on — defined by the TCG PC
Client Platform Firmware Profile). By the time the kernel is running, the full
final PCR values are a tamper-evident fingerprint of every stage that ran,
built one irreversible extend at a time, starting from an immutable root.

---

## 5. Static vs. Dynamic RTM

SRTM has a real practical downside: it measures *everything* from power-on,
including a lot of early, messy pre-boot firmware behavior that has nothing to
do with the actual workload you care about protecting (e.g., launching a
hypervisor). Any firmware update anywhere in that long chain changes the final
PCR values, even if the thing you actually cared about (say, the hypervisor
itself) didn't change at all.

**Dynamic Root of Trust for Measurement (DRTM)** — Intel TXT's "late launch"
and AMD's SKINIT — takes a different approach: instead of measuring from
power-on, it performs a special CPU instruction *later*, mid-boot, that resets
a dedicated set of PCRs and establishes a fresh, narrower trust baseline right
before launching the thing that actually matters (typically a hypervisor).

| | SRTM | DRTM |
|---|---|---|
| Starts measuring | At power-on | Mid-boot, via a dedicated CPU instruction |
| Scope | Everything, including early messy firmware | A deliberately narrow, surgical baseline |
| Stability across firmware updates | Fragile — any upstream change shifts PCRs | More stable for the specific launch target |
| Typical use | General OS/disk-encryption sealing | Hypervisor/VMM launch integrity |

Both are legitimate; they answer slightly different questions ("what did this
whole machine boot through" vs. "what exact state was the hypervisor launched
in").

---

## 6. The Practical Pain Point

Because SRTM measures the *entire* chain, a routine UEFI firmware update, a
GRUB version bump, or even a BIOS setting change can shift PCR values —
breaking anything sealed against the old values, even though nothing
malicious happened. This is a known, recurring operational headache, not a
bug: the system is correctly refusing to unseal because the measured state
genuinely changed. The standard mitigation is re-sealing secrets after any
intentional, verified firmware/bootloader update — which is also exactly the
moment you'd want to double-check *why* the PCR values changed, since a
legitimate update and a tampering attempt look identical from the TPM's point
of view until you check.

---

## Quick Reference

| Question | Answer |
|---|---|
| Can software feed the TPM a dishonest `PCR_Extend` value? | Yes, technically — the TPM doesn't verify measurement truthfulness |
| So why can't boot measurements be faked in practice? | Measure-before-execute: malicious code never runs before it's already measured, all the way back to an immutable CRTM |
| What makes the CRTM itself trustworthy? | Hardware immutability or factory-fused signature enforcement (e.g., Intel Boot Guard) — not software vouching |
| Why does a firmware update break sealed secrets? | SRTM measures the entire chain from power-on; any change anywhere in it changes the final PCR values |
| How do you avoid re-measuring the whole chain for a narrow launch target? | DRTM (Intel TXT / AMD SKINIT) resets to a smaller baseline mid-boot |

---

## What You've Learned

✅ The TPM does not verify measurement truthfulness — "measure before execute" is what actually prevents forged measurements
✅ The CRTM is the one link that can't appeal to earlier software for its trustworthiness — it's anchored in hardware immutability or fused signatures
✅ The full SRTM chain (CRTM → firmware → bootloader → OS loader → kernel) builds one irreversible PCR extend at a time
✅ DRTM (Intel TXT/AMD SKINIT) offers a narrower, more stable alternative baseline for a specific launch target
✅ Firmware/bootloader updates legitimately shift PCR values — re-sealing after a verified update is expected operational practice, not a workaround for a bug

---

## Hands-On Resources

- **[TCG PC Client Platform Firmware Profile](https://trustedcomputinggroup.org/resource/pc-client-specific-platform-firmware-profile-specification/)** — the standard PCR index assignments referenced above
- **[Intel Trusted Execution Technology (TXT) overview](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-trusted-execution-technology.html)** — the DRTM mechanism in detail
- **[Intel Boot Guard technical overview](https://www.intel.com/content/www/us/en/developer/articles/technical/hardware-security-overview.html)** — how the CRTM's own trustworthiness is fused in at the factory

---

## Next Steps

**Continue learning:**
→ [Secure Boot](07_secure_boot.md) — the complementary, prevention-based mechanism that stops unsigned code from running at all

**Related topics:**
→ [Sealing, Attestation, and PCRs](03_sealing_attestation_pcrs.md)

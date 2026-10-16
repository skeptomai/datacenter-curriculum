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
- What "measuring" a piece of code actually means — and the crucial fact that it is
  about a binary's *identity*, never about what it *does* when it runs
- Concretely, which piece of software performs the read-hash-extend sequence, and
  how it knows where to find the next stage in the first place
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

## 3. What Actually Gets Measured, and Who Does It

Section 2 described the four-step sequence in the abstract. Two questions are
easy to gloss over there and worth answering explicitly: **what does "measure
the code" actually mean**, and **who performs that read-hash-extend sequence,
and how do they know what to read in the first place?**

### Measuring is about identity, not behavior

"Measuring" a piece of code means computing a cryptographic hash of its raw
bytes — the compiled binary, exactly as it sits on disk — *before* that code
ever runs. It is not "run this code and record what it decided." The measurer
never executes the thing it's measuring, never inspects its logic, and never
asks it to self-report anything. It treats the artifact as an opaque blob of
bytes and hashes those bytes, full stop.

This distinction matters more than it looks. Suppose Stage N+1 is boot logic
that includes a kernel-version check — code that inspects a kernel image and
decides whether to proceed. There are two very different things "measuring"
could mean here, and only one of them is what actually happens:

```
NOT this:                                  ACTUALLY this:
Run the version-check code,                Hash Stage N+1's binary — the raw
ask it "did the kernel pass?",             bytes containing the version-check
and record the answer (PASS/FAIL)          logic — BEFORE running any of it,
as the measurement.                        then extend a PCR with that hash,
                                            THEN execute it.

Problem: this trusts the code to           Why this is better: the measurer
self-report honestly. A compromised        never has to trust anything the
version-check could lie about its          code says about itself. A tampered
own outcome while doing something          version of the code — even one
different underneath.                      patched to always report "PASS" —
                                            is a DIFFERENT set of bytes, which
                                            produces a DIFFERENT hash. The
                                            tampering is caught by the
                                            fingerprint changing, not by
                                            catching the code in a lie.
```

Whatever Stage N+1's kernel-version-check logic actually decides when it
runs — approve, reject, panic, print a cat ASCII-art banner — is ordinary
program execution that happens *after* measurement is already done and
irreversible. None of that behavior is, or could be, part of the measurement.
The measurement only ever answers "is this the exact same code that was there
before," never "did this code behave correctly."

This is also why boot-relevant *data*, not just executable code, gets
measured in practice — a bootloader configuration file, a kernel command-line
string, the recorded state of UEFI Secure Boot variables. None of that is
"code" in the sense of CPU instructions, but all of it influences what happens
next, so the same rule applies: hash the bytes, before acting on them, every
time.

### Who performs the read-hash-extend sequence

There is no external supervisor watching the boot process and independently
deciding to measure things. **The current stage's own code does the
measuring, because its developers built it to, following a published
specification.** Concretely:

- UEFI firmware, before it calls the standard `LoadImage`/`StartImage`
  routines to hand control to the next executable, is specified by the TCG PC
  Client Platform Firmware Profile to first call a defined measurement
  routine (historically `TCG2_HashLogExtendEvent` in the UEFI TCG2 protocol)
  against that executable's bytes. The order — measure, *then* load and run —
  is mandated by the spec, not left to firmware authors' discretion.
- GRUB, Shim, and Windows Boot Manager each carry their own equivalent calls
  into the platform's TPM measurement interface, invoked right before their
  respective `chainloader`/`linux`/boot-image-launch operations.

So "who tells it to go read this code and hash it" has a plain answer: **the
spec tells the stage's implementers to put that call there, and they did.**
It's self-discipline, encoded directly into the stage's own program logic,
immediately before the point where it would otherwise just jump to the next
thing.

### How does it know *where* the next stage even is?

Separately from *that* it measures, each stage also needs to know *what file,
at what location*, counts as "the next stage" — and that's answered by
ordinary, non-cryptographic boot configuration: UEFI firmware reads boot
variables from NVRAM (`BootOrder`, `Boot0001`, etc.) pointing at a specific
file on a specific disk partition; GRUB reads its own `grub.cfg`, which names
a specific kernel file and path.

This location information is not itself trusted or protected — and it
doesn't need to be, which is the elegant part. Whatever ends up getting
loaded, from wherever the configuration pointed, is exactly what gets read
and hashed. If an attacker tampered with a boot variable or a config file to
redirect "the next stage" at a malicious substitute, the measuring stage
doesn't know or care that a redirection happened — it simply measures
whatever bytes it was handed. The result is a hash of the *attacker's*
substituted artifact, which does not match the trusted reference value that a
seal or a remote quote checks against later. Misdirecting *where* the
measurement reads from doesn't evade measurement; it just guarantees the
measurement will faithfully record the substitution, and the mismatch is
caught downstream.

### The recursive question this leaves open

One gap remains, and it's the one this whole document exists to close: **what
stops Stage N itself from simply skipping its measurement call, or calling it
with a fabricated hash instead of a real one?** Nothing *inherent* to the
command itself — as Section 1 already established, the TPM accepts whatever
`PCR_Extend` value it's handed. The guarantee instead comes from exactly the
same recursive argument as before: Stage N can only skip or falsify its own
measurement duty if Stage N's *own code* has been tampered with to remove
that duty — and whether Stage N's code has been tampered with is precisely
what Stage N-1 already measured, before Stage N was ever allowed to run.

That recursion has to end somewhere, with a measurer that has no earlier
stage to vouch for *its* integrity. That's the CRTM, covered next.

---

## 4. The Core Root of Trust for Measurement (CRTM)

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

## 5. The Full SRTM Boot Chain

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

## 6. Static vs. Dynamic RTM

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

## 7. The Practical Pain Point

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
| What does "measuring code" actually mean? | Hashing its raw bytes before it runs — never executing it, never recording what it decides |
| Who performs the read-hash-extend sequence? | The current stage's own code, calling a platform measurement API, because its spec says to do so right before loading the next stage |
| How does a stage know where the next stage even is? | Ordinary boot configuration (UEFI boot variables, a bootloader's config file) — not itself trusted, because whatever gets loaded is exactly what gets measured, substitution included |
| Can software feed the TPM a dishonest `PCR_Extend` value? | Yes, technically — the TPM doesn't verify measurement truthfulness |
| So why can't boot measurements be faked in practice? | Measure-before-execute: malicious code never runs before it's already measured, all the way back to an immutable CRTM |
| What makes the CRTM itself trustworthy? | Hardware immutability or factory-fused signature enforcement (e.g., Intel Boot Guard) — not software vouching |
| Why does a firmware update break sealed secrets? | SRTM measures the entire chain from power-on; any change anywhere in it changes the final PCR values |
| How do you avoid re-measuring the whole chain for a narrow launch target? | DRTM (Intel TXT / AMD SKINIT) resets to a smaller baseline mid-boot |

---

## What You've Learned

✅ Measuring code means hashing its bytes before it runs — never executing it, never recording its decisions or behavior
✅ Each stage's own code does the measuring itself, via a platform API call its spec mandates right before loading the next stage
✅ The next stage's location comes from ordinary, untrusted boot configuration — safe because whatever gets loaded is exactly what gets measured, substitutions included
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

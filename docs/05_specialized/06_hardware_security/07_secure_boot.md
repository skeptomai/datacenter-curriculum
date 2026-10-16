---
level: specialized
estimated_time: 40 min
prerequisites:
  - 05_specialized/06_hardware_security/06_measured_boot.md
next_recommended:
  - 04_containers/05_security/04_supply_chain.md
tags: [secure-boot, uefi, shim, mok, pk, kek, db, dbx, chain-of-trust]
---

# Secure Boot: Prevention, Not Just Detection

## Learning Objectives

After reading this document, you will understand:
- The UEFI Secure Boot key hierarchy (PK, KEK, db, dbx) and what each controls
- Why Secure Boot is a prevention mechanism, fundamentally different from measured boot's detection
- How Linux handles third-party kernel modules and custom kernels under Secure Boot (shim + MOK)
- Why real systems need both Secure Boot and measured boot, using a concrete rollback-attack example

## Prerequisites

Before reading this, you should understand:
- [Measured Boot](06_measured_boot.md) — the detection-based mechanism this document contrasts with

---

## 1. A Different Mechanism, Often Confused with Measured Boot

Secure Boot and measured boot are frequently conflated because they both
happen during boot and both involve cryptography. They solve different
problems:

| | Measured Boot | Secure Boot |
|---|---|---|
| **Model** | Detection — record what ran, let something else decide later | Prevention — refuse to run anything unauthorized, immediately |
| **Mechanism** | Hash + extend into PCRs (TPM) | Signature verification against trusted keys (UEFI firmware) |
| **Trust root** | CRTM (immutable/fused firmware) | UEFI's own key database (PK/KEK/db/dbx) |
| **What a failure looks like** | Boot continues; PCR values just reflect reality, verified later | Boot *refuses to continue* at the point of the unsigned/untrusted binary |

Secure Boot does not require a TPM at all — it's a UEFI firmware feature with
its own, independent key hierarchy.

---

## 2. The UEFI Secure Boot Key Hierarchy

```
PK  (Platform Key)         — one key, owned by the OEM/platform owner;
                              controls who can update the KEK
  │
  ▼
KEK (Key Exchange Key)     — one or more keys; controls who can update db/dbx
  │
  ▼
db  (Signature Database)   — trusted signing certificates AND/OR specific
                              trusted binary hashes; anything signed by (or
                              matching) an entry here is allowed to execute
dbx (Forbidden Signatures) — explicitly REVOKED certificates/hashes, even if
                              they'd otherwise match something in db
```

At boot, UEFI firmware checks each stage's signature against `db`, rejecting
anything that doesn't verify, or that matches an entry in `dbx` even if it
would otherwise pass. This is a straightforward pass/fail gate, evaluated
fresh at every boot — no accumulation, no PCR chain, just "is this binary's
signature trusted right now."

---

## 3. Linux and Third-Party Modules: shim + MOK

Most Linux distributions don't ship a key in Microsoft's (or the OEM's)
default `db` — getting there would mean every distro's every kernel build
needs OEM sign-off. Instead:

```
UEFI db trusts → shim (a small, Microsoft-signed first-stage loader)
                     │
                     ▼ shim trusts its own embedded distro key, PLUS
                       anything in the Machine Owner Key (MOK) list
                     │
                     ▼
                GRUB / kernel (signed by the distro key, or by a key
                               the machine owner personally enrolled
                               into MOK — e.g., for a custom-built
                               out-of-tree kernel module)
```

`shim` is the one component that actually needs OEM/Microsoft signing; it
then delegates trust to the distro and to the **Machine Owner Key (MOK)** —
a separate, locally-managed trust list the machine's owner can add their own
keys to (`mokutil --import`), without needing to touch the firmware's own
`db`/`KEK`/`PK` at all. This is how a self-signed out-of-tree kernel module
(e.g., a GPU or VPN driver) can still load under Secure Boot.

---

## 4. Why You Need Both, Concretely: The Rollback Attack

Here's the scenario that shows why Secure Boot alone isn't sufficient, and why
pairing it with measured boot/attestation matters:

```
1. A bootloader version has a known vulnerability, discovered and patched.
2. The vulnerable OLD version was, at the time it shipped, VALIDLY SIGNED
   by the real distro key — it's still a perfectly legitimate signature.
3. An attacker with brief physical/local access swaps in that OLD,
   vulnerable-but-validly-signed bootloader.
4. Secure Boot checks the signature: VALID. Boot proceeds normally.
   Secure Boot has no concept of "this signature is valid but this is an
   OLD, known-bad VERSION" — unless that specific binary was explicitly
   revoked via dbx.
5. Measured boot/attestation, however, DOES notice: the PCR value for the
   bootloader stage is different from the known-good reference, because a
   different (older) binary was measured. A remote attestation check
   comparing against expected PCR values catches exactly what Secure Boot's
   pass/fail signature check missed.
```

In practice, both mechanisms are layered: `dbx` revocation lists are the
Secure Boot answer to known-bad versions (when maintained diligently), and
measured boot/attestation is the defense-in-depth answer for anything `dbx`
hasn't caught up to yet, or for detecting state a pure "valid signature"
check was never designed to notice in the first place.

---

## Quick Reference

| Term | What it is |
|---|---|
| **PK** | Root platform key; controls KEK updates |
| **KEK** | Controls db/dbx updates |
| **db** | Trusted signatures/hashes allowed to execute |
| **dbx** | Explicitly revoked signatures/hashes, even if otherwise trusted |
| **shim** | Microsoft/OEM-signed first-stage loader that bridges to distro + MOK trust |
| **MOK** | Machine Owner Key — locally managed trust list for custom kernels/modules |

---

## What You've Learned

✅ Secure Boot is prevention (refuse to run) via signature checks; measured boot is detection (record, verify later) via PCR hashes
✅ The PK → KEK → db/dbx hierarchy governs what UEFI firmware will execute, evaluated fresh at every boot
✅ shim + MOK let Linux support distro kernels and custom out-of-tree modules without touching OEM firmware keys
✅ A validly-signed-but-outdated-and-vulnerable bootloader passes Secure Boot but shows up as a mismatch in measured boot/attestation — which is exactly why production systems use both

---

## Hands-On Resources

- **[UEFI Secure Boot specification](https://uefi.org/specifications)** — the authoritative PK/KEK/db/dbx definitions
- **[mokutil](https://github.com/lcp/mokutil)** — enroll a custom key into the Machine Owner Key list on Linux
- **[Rod Smith's "Making UEFI Secure Boot Work With Open Source Software"](http://www.rodsbooks.com/efi-bootloaders/secureboot.html)** — a detailed, practitioner-level walkthrough of shim/MOK in practice

---

## Next Steps

**Continue learning:**
→ [Supply Chain Security](../../04_containers/05_security/04_supply_chain.md) — how signature-based trust and provenance verification extend beyond the boot chain into container images

**Related topics:**
→ [Measured Boot](06_measured_boot.md)
→ [TPM in Practice](05_tpm_in_practice.md)
→ [Case Study: TPM-Backed Node Identity with SPIRE/SPIFFE](08_case_study_spire_tpm_devid.md) — a real cluster applying these primitives to a different problem (device identity, not boot verification)

---
level: specialized
estimated_time: 30 min
prerequisites: []
next_recommended:
  - 05_specialized/06_hardware_security/02_key_hierarchy_and_provisioning.md
tags: [tpm, hardware-security, trusted-computing, root-of-trust]
---

# TPM Fundamentals: Why a Separate Security Chip?

## Learning Objectives

After reading this document, you will understand:
- The specific problem a TPM (Trusted Platform Module) solves that software-only
  security cannot
- What a TPM physically is and how it differs from a general-purpose CPU
- The narrow, fixed command interface that defines what a TPM can and cannot do
- Why the TPM boundary (not encryption alone) is the source of its guarantees

## Prerequisites

Before reading this, you should understand:
- Basic symmetric/asymmetric cryptography (public/private keys, hashing)
- What a "root of trust" means informally (something you trust because it's the
  first link in a chain, not because something else vouches for it)

---

## 1. The Problem: Secrets Need a Place to Live

Any system that encrypts a disk, authenticates a device, or proves "this machine
booted unmodified software" needs a secret key somewhere. Without special hardware,
that key has to live in one of these places:

```
Option                        Who can read it?
─────────────────────────    ──────────────────────────────────────
A file on disk                 Anyone with disk access (stolen drive,
                                another OS, an attacker with root)
In RAM while running           Anyone who can dump memory (cold boot
                                attack, debugger, compromised kernel)
Derived from a password         Only as strong as the password + whatever
                                guesses the attacker gets
```

A TPM exists to create a fourth option: **a key that can be used (sign, decrypt,
seal/unseal) without ever existing anywhere a general-purpose CPU or OS can read
it as plaintext** — not even for the machine's own administrator, and not even
across an OS reinstall.

This is a stronger claim than "encrypted storage." Encryption just moves the
secret-storage problem to a different secret (the encryption key). A TPM is
trying to end the chain: at some point, a key exists only *inside* a boundary
that has no "read out the private key" operation at all.

---

## 2. What a TPM Physically Is

A TPM is a small, dedicated security *processor* — not a software module, not a
general CPU core running security code. It contains:

```
┌─────────────────────────────────────────────┐
│                  TPM                         │
│                                               │
│  ┌──────────────┐  ┌───────────────────┐    │
│  │ Crypto engine │  │ True random number │    │
│  │ RSA/ECC/SHA/  │  │ generator (RNG)    │    │
│  │ AES/HMAC      │  └───────────────────┘    │
│  └──────────────┘                            │
│                                               │
│  ┌──────────────┐  ┌───────────────────┐    │
│  │ Tiny NVRAM    │  │ Monotonic counters │    │
│  │ (KB, not GB)  │  │ and lockout state   │    │
│  └──────────────┘  └───────────────────┘    │
│                                               │
│  Fixed firmware — speaks ONLY the TPM 2.0    │
│  command protocol. No general code execution │
│  exposed to the host.                        │
└─────────────────────┬─────────────────────────┘
                       │ bus (SPI / I2C / LPC, or
                       │ CPU-internal for firmware TPMs)
                       ▼
                  Host CPU / OS
```

Two properties matter more than any other:

1. **It has no "export the private key" command.** The command set (standardized
   by the Trusted Computing Group, TCG) is a fixed menu: create a key, seal data,
   unseal data, sign, quote, extend a PCR, and a few dozen more. There is no
   operation that returns a `fixedTPM`-marked private key to the caller, because
   that operation was never defined into the protocol.
2. **It sits behind a narrow interface.** You don't run code on a TPM. You send
   one of a small set of well-defined commands and get a well-defined response.
   This is what makes a TPM auditable and certifiable — the entire attack
   surface is a short, published command list, not "whatever this chip's
   firmware happens to allow."

---

## 3. Discrete vs. On-CPU — a Preview

A TPM doesn't have to be a separate chip on a bus. Some run as protected firmware
inside the CPU package itself (Intel PTT, AMD fTPM) or fused directly onto the
CPU die (Microsoft Pluton). All of them expose the *same* TPM 2.0 command
interface — the difference is where the trust boundary physically sits, which
changes what attacks are possible. That's substantial enough to deserve its own
document: see [TPM Vendor Landscape](04_vendor_landscape_dtpm_vs_ftpm.md).

---

## Quick Reference

| Question | Answer |
|---|---|
| Is a TPM a general-purpose chip? | No — fixed firmware, fixed command set, no user code execution |
| Can you ever read out a `fixedTPM` private key? | No — there is no such command in the protocol |
| What makes a TPM trustworthy vs. a software vault? | The non-exportability is enforced by the absence of an export command, not by policy |
| Does a TPM need to be a separate chip? | No — firmware TPMs (Intel PTT, AMD fTPM) and die-integrated TPMs (Pluton) exist too |

---

## What You've Learned

✅ The specific gap a TPM fills: a key usable without ever being readable as plaintext by the host
✅ A TPM is dedicated silicon with a fixed, narrow command protocol — not software
✅ Non-exportability comes from the command set's design, not from encryption alone
✅ Form factor (discrete chip vs. firmware vs. die-integrated) is a separate axis, covered later

---

## Hands-On Resources

- **[TCG TPM 2.0 Library Specification](https://trustedcomputinggroup.org/resource/tpm-library-specification/)** — the authoritative command-level spec
- **[tpm2-tools](https://github.com/tpm2-software/tpm2-tools)** — command-line tools to talk to a real or simulated TPM 2.0
- **[IBM's TPM 2.0 software simulator](https://sourceforge.net/projects/ibmswtpm2/)** — run and experiment with a TPM without hardware

---

## Next Steps

**Continue learning:**
→ [Key Hierarchy and Provisioning](02_key_hierarchy_and_provisioning.md) — where the Endorsement Key comes from and how the TPM's key tree is structured

**Related topics:**
→ [TPM Vendor Landscape](04_vendor_landscape_dtpm_vs_ftpm.md) — discrete vs. firmware vs. integrated TPMs

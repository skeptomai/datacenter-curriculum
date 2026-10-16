---
level: specialized
estimated_time: 45 min
prerequisites:
  - 05_specialized/06_hardware_security/02_key_hierarchy_and_provisioning.md
next_recommended:
  - 05_specialized/06_hardware_security/06_measured_boot.md
tags: [tpm, pcr, sealing, attestation, quote, nvram, dictionary-attack]
---

# Sealing, Attestation, and PCRs

## Learning Objectives

After reading this document, you will understand:
- What PCRs (Platform Configuration Registers) are and the one operation they support
- Why that single operation (extend) is what makes a PCR's final value trustworthy
- How sealing ties a secret's release to a specific platform state
- How a quote lets a remote party verify that state using the Attestation Key
- What else lives in TPM NVRAM: counters, small data slots, and lockout state

## Prerequisites

Before reading this, you should understand:
- [Key Hierarchy and Provisioning](02_key_hierarchy_and_provisioning.md) — the AK, and why it isn't the EK

---

## 1. PCRs: One Register, One Operation

A TPM has a bank of **Platform Configuration Registers** — typically 24, each
holding a hash value, duplicated per supported hash algorithm (a SHA-1 bank and
a SHA-256 bank commonly coexist for legacy compatibility). PCRs support exactly
one write operation:

```
PCR_new = Hash( PCR_old || measurement )
```

This is called **extending** a PCR. There is deliberately no "set this PCR to a
specific value" command. You can only fold a new measurement into whatever is
already there.

**Why this matters:** because cryptographic hashes are one-way, you cannot work
backward from a target final value to find an input that produces it (short of
breaking the hash function). That means you can't "rewind" a PCR to a prior,
more favorable value, and you can't jump straight to a desired final value
without actually having extended it through every real measurement step along
the way.

```
Example (toy, not real hash output):
  PCR starts at 0x00000...000 (reset value)
  Extend with measurement of firmware:  PCR = Hash(0x000... || fw_hash)
  Extend with measurement of bootloader: PCR = Hash(prev || loader_hash)
  Extend with measurement of kernel:     PCR = Hash(prev || kernel_hash)

  Final PCR value is a fingerprint of the ENTIRE sequence, not just the
  last thing measured.
```

This is the raw mechanism behind "you can't fake a PCR value." It is *not*,
by itself, the whole story — a PCR only tells you something trustworthy if
whatever is doing the measuring can itself be trusted, and if it measures
*before* handing control to the thing it measured. That chain-of-trust
argument — covering who measures first, and why that first measurer can't
simply lie — is covered in full in
[Measured Boot](06_measured_boot.md). This document covers what the TPM does
with PCR values once they exist.

---

## 2. Sealing and Unsealing

**Sealing** encrypts data such that the TPM will only decrypt it again
(**unseal**) if the live PCR values match the values recorded at seal time
(plus any other configured authorization, such as a password or policy).

```
Seal time (e.g., during OS setup):
  secret = disk encryption key
  seal(secret, PCR[0..7] = current values) → sealed_blob (safe to store on disk)

Later, at every boot:
  unseal(sealed_blob)
    → TPM checks: do current PCR[0..7] match what was sealed against?
    → Match:    returns the secret
    → No match: refuses outright (not "garbage," a hard refusal)
```

This is the mechanism behind "the disk only auto-unlocks if the boot chain is
unmodified" (BitLocker, LUKS+clevis-tpm2, etc.) — covered with worked examples
in [TPM in Practice](05_tpm_in_practice.md).

---

## 3. Quoting: Proving State to Someone Else

Sealing is a *local* guarantee — the TPM enforces it against itself. **Quoting**
is how a *remote* party gets the same assurance without trusting the machine's
own OS to self-report honestly.

```
Verifier                              TPM (on the machine being checked)
────────                              ───────────────────────────────────
1. Send a nonce (random challenge,
   prevents replay of an old quote)
                                  →   2. TPM2_Quote:
                                         - read current PCR[0..23]
                                         - sign (PCR values || nonce)
                                           using the AK (restricted,
                                           sign-only — see prior doc)
3. Receive signed quote            ←
4. Verify AK certificate chains
   back to a genuine EK
5. Verify signature over
   (PCR values || nonce)
6. Compare PCR values against
   known-good reference values
```

Because the AK is `restricted`, it can only sign data the TPM itself assembled
internally — it cannot be tricked into signing an arbitrary attacker-supplied
blob that merely *looks like* a quote. This closes the forgery path that would
otherwise undermine the whole scheme.

---

## 4. Binding

A less commonly used sibling operation: **binding** encrypts data to a
specific TPM's public key with no PCR condition at all — only that TPM's
private key can decrypt it, regardless of boot state. Useful for "only this
specific physical machine should ever be able to read this," without caring
what it's currently running.

---

## 5. Other TPM NVRAM Contents

PCRs aren't the only thing in a TPM's small non-volatile memory:

| Item | Purpose | Typical size |
|---|---|---|
| **NV indexes** | General-purpose small data slots, each with its own auth/policy | A few hundred bytes to a few KB each; total budget often 6–16 KB |
| **Monotonic counters** | Values that can only increase — anti-rollback protection | A few bytes, but semantically unlimited increments |
| **Persistent object handles** | Keys kept loaded across reboots without re-deriving | Often only a dozen or so slots on commodity chips |
| **Dictionary-attack lockout state** | Failure counters + exponential lockout timers | A few bytes, but persists across reboot so the clock can't be reset by power-cycling |

The lockout mechanism is worth calling out specifically: the TPM — not the
OS — counts failed authorization attempts against its keys and NV indexes,
and locks out further attempts with increasing delay after too many failures.
An attacker who has the encrypted disk but not the TPM cannot brute-force a
PCR-sealed or password-protected key by simply trying forever, because the
rate limiting lives inside the chip itself and survives a reboot.

---

## Quick Reference

| Operation | What it proves | To whom |
|---|---|---|
| **Extend** | Folds a new measurement into a PCR; one-way, can't rewind | N/A — it's the write primitive |
| **Seal / Unseal** | "Release this secret only if boot state matches" | The TPM, to itself, locally |
| **Quote** | "Here is the current boot state, signed" | A remote verifier |
| **Bind** | "Only this specific TPM can read this" | N/A — device-specific encryption |

---

## What You've Learned

✅ PCRs support exactly one write operation (extend), which is why their final value can't be rewound or faked by a later step
✅ Sealing ties secret release to live PCR state; unsealing fails hard (not silently) on mismatch
✅ Quoting lets a remote verifier check boot state via a signed, nonce-bound PCR snapshot from the AK
✅ TPM NVRAM also holds anti-rollback counters, small app-data slots, and dictionary-attack lockout state — all enforced inside the chip

---

## Hands-On Resources

- **[tpm2_pcrread / tpm2_pcrextend (tpm2-tools)](https://github.com/tpm2-software/tpm2-tools)** — read and extend real PCR values
- **[tpm2_quote](https://github.com/tpm2-software/tpm2-tools/blob/master/man/tpm2_quote.1.md)** — generate a signed PCR quote against an AK
- **[TCG PC Client Platform Firmware Profile](https://trustedcomputinggroup.org/resource/pc-client-specific-platform-firmware-profile-specification/)** — defines which firmware events extend which PCR index

---

## Next Steps

**Continue learning:**
→ [Measured Boot](06_measured_boot.md) — the full chain-of-trust argument for why the measurements themselves can't be forged

**Related topics:**
→ [TPM Vendor Landscape](04_vendor_landscape_dtpm_vs_ftpm.md)
→ [TPM in Practice](05_tpm_in_practice.md)

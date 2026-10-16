---
level: specialized
estimated_time: 45 min
prerequisites:
  - 05_specialized/06_hardware_security/01_tpm_fundamentals.md
next_recommended:
  - 05_specialized/06_hardware_security/03_sealing_attestation_pcrs.md
tags: [tpm, key-hierarchy, endorsement-key, attestation-key, provisioning, privacy-ca]
---

# TPM Key Hierarchy and Provisioning

## Learning Objectives

After reading this document, you will understand:
- Why TPM 2.0 derives most keys from seeds instead of storing them
- The four key hierarchies and what each one is for
- What gets provisioned at the factory, and why only the Endorsement Key is special-cased
- Where an Attestation Key actually comes from, and why it is never the Endorsement Key itself
- How a TPM proves a freshly-created Attestation Key genuinely belongs to it, without
  exposing its permanent identity key directly

## Prerequisites

Before reading this, you should understand:
- [TPM Fundamentals](01_tpm_fundamentals.md) — what a TPM is and why non-exportability matters

---

## 1. Seeds, Not a Key Vault

TPM 1.2 worked like a small encrypted filesystem: each key you created was a
persistent blob, stored (encrypted) in the TPM's limited NVRAM or spooled out to
disk wrapped by a parent key. TPM 2.0 changed the model.

Instead of storing most keys, a TPM 2.0 chip stores a small number of **primary
seeds** — random values generated once and kept secret inside the chip — and
**deterministically regenerates** keys from a seed plus a fixed derivation path
whenever they're needed:

```
Seed (never leaves the TPM) + Fixed derivation template
        │
        ▼
   Primary key regenerated on demand
        │
        ▼
   Used for the operation, then discarded from TPM RAM
```

This matters for two reasons: it means the TPM's tiny NVRAM budget doesn't have
to hold every key you'll ever use, and it means a factory reset ("clear") that
wipes the seeds instantly and irrecoverably destroys every key ever derived from
them — there's no backup copy sitting anywhere to recover.

---

## 2. The Four Hierarchies

Each primary seed roots its own **hierarchy** — a namespace of keys with its own
owner and its own authorization policy:

| Hierarchy | Seed | Controlled by | Typical use |
|---|---|---|---|
| **Endorsement** | Endorsement Primary Seed | Platform/TPM manufacturer | TPM identity (the EK), the anchor for attestation |
| **Platform** | Platform Primary Seed | Firmware/OEM (BIOS/UEFI) | Platform-level measurements and policy, mostly pre-boot |
| **Owner / Storage** | Storage Primary Seed | OS/end user | General-purpose keys: disk encryption, app secrets, the SRK |
| **Null** | Regenerated every power cycle | Nobody persistently | Ephemeral, session-scoped keys that must never survive a reboot |

Only the Owner/Storage hierarchy is normally meant for everyday application use.
The Endorsement and Platform hierarchies are deliberately kept separate from
general-purpose key creation — this separation is what lets a verifier trust an
EK-rooted identity claim without worrying that the OS or an app could have
silently generated a lookalike key under the same seed.

---

## 3. What Gets Provisioned at the Factory

Of everything described above, **one key is special-cased and actually persisted**
rather than regenerated on demand: the **Endorsement Key (EK)**.

```
At manufacturing time:
  1. TPM generates its Endorsement Primary Seed internally (never leaves the chip)
  2. TPM derives the EK key pair from that seed
  3. Manufacturer's certification process signs an EK CERTIFICATE binding:
       "this EK public key belongs to a genuine TPM, model X, from vendor Y,
        with capability set Z"
  4. EK certificate is stored (often in TPM NVRAM, or supplied by the OEM)
```

The EK certificate is issued by the TPM vendor's own certificate authority (or an
OEM CA chaining up to the vendor). This is the **hardware root of the entire
attestation story**: a remote verifier who trusts that CA can trust that any
quote eventually traced back to this EK really did come from silicon the vendor
built, not from a software TPM emulator pretending to be one.

Everything else — your disk-encryption key, an SSH host key, a signing key for an
application — is created later, by you or your OS, under the Owner/Storage
hierarchy. None of that is "factory provisioned"; only the EK (and sometimes an
OEM-specific Platform key) is.

---

## 4. Why the Attestation Key Is *Not* the Endorsement Key

This is the detail that's easy to skip past: you never use the EK directly to
sign anything in day-to-day attestation. There are two separate reasons.

**Reason 1 — privacy.** The EK is a permanent, unique, factory-issued identity.
If every attestation a device ever performed were signed directly by the EK, any
two services could compare notes and realize they were talking to the *same*
physical machine every time — a permanent tracking identifier baked into
hardware. TCG designed TPM 2.0 specifically to avoid forcing that trade-off.

**Reason 2 — restricted signing.** The EK (and any "restricted" signing key) is
only allowed to sign data structures the TPM itself generated internally — never
arbitrary attacker-supplied bytes. This closes a forgery hole: without this
restriction, an attacker could ask the TPM to "sign this blob" where the blob is
crafted to look exactly like a PCR quote, and get a valid-looking forged
attestation for free. A restricted key can only sign TPM-internal structures that
carry a recognizable tag identifying them as TPM-generated.

So instead, you create a separate **Attestation Key (AK)** — a new key pair,
generated inside the TPM, marked `restricted` + `sign-only`, typically parented
under the Endorsement hierarchy. The AK is what actually signs PCR quotes in
day-to-day remote attestation. The remaining problem: how does a verifier trust
that *this* newly minted AK genuinely lives inside the same chip that holds the
one true EK, without the EK ever being used to sign anything itself?

```
TPM                                  Privacy CA / Verifier
───                                  ─────────────────────
1. Generate AK (new key pair,
   restricted, sign-only)
                                 →    2. Send AK public key + EK certificate
                                      3. Verifier generates a random secret,
                                         encrypts it so ONLY a TPM holding the
                                         matching EK private key can recover it
                                         (TPM2_MakeCredential)
4. TPM2_ActivateCredential:
   decrypt the credential —
   only possible if this TPM
   really holds the EK private
   key AND the AK really is
   resident in it
                                 →    5. TPM proves it recovered the secret
                                      6. Verifier issues an AK CERTIFICATE:
                                         "this AK is genuinely co-resident
                                         with a real EK" — without the EK
                                         ever signing anything directly
```

This challenge-response step is called **credential activation**. In its fuller
historical form this role is played by a dedicated **Privacy CA**; some modern
deployments (several cloud and enterprise attestation services) simplify this by
having the verifier perform the EK-certificate check and AK certification
directly, trading some of the anonymity benefit for a simpler pipeline. TPM 2.0
also defines **ECDAA (Elliptic Curve Direct Anonymous Attestation)** as an
alternative that lets a TPM prove AK authenticity without even a Privacy CA
in the loop, at the cost of more complex cryptography — covered here for
completeness, not commonly deployed outside specific identity schemes.

**The upshot:** the AK you see used to sign a quote is a disposable, app- or
session-scoped identity, cryptographically vouched for by the one permanent EK
without ever directly exposing or overusing that EK.

---

## Quick Reference

| Term | What it is | Persisted or derived? |
|---|---|---|
| Primary seed | Random root value per hierarchy | Persisted (only these, really) |
| EK (Endorsement Key) | Permanent chip identity | Persisted, factory-issued, certified |
| SRK (Storage Root Key) | Root of your general-purpose key tree | Derived on demand from the Storage seed |
| AK (Attestation Key) | Restricted signing key for quotes | Created later, certified via EK once |
| Null hierarchy keys | Session-scoped | Regenerated every power cycle, never persisted |

---

## What You've Learned

✅ TPM 2.0 derives most keys from seeds rather than storing them — only the EK is truly factory-persisted
✅ Four hierarchies (Endorsement, Platform, Owner/Storage, Null) separate identity, firmware, user keys, and ephemeral state
✅ The Attestation Key is a separate, disposable, restricted signing key — never the EK itself
✅ Credential activation (`TPM2_MakeCredential` / `TPM2_ActivateCredential`) proves an AK is genuinely co-resident with a real EK, without the EK signing anything directly

---

## Hands-On Resources

- **[TCG TPM 2.0 Keys and Hierarchies spec section](https://trustedcomputinggroup.org/resource/tpm-library-specification/)** — authoritative hierarchy and seed definitions
- **[tpm2_createek / tpm2_createak (tpm2-tools)](https://github.com/tpm2-software/tpm2-tools)** — create and certify an AK against a real TPM's EK
- **[NIST SP 800-155](https://csrc.nist.gov/publications/detail/sp/800-155/draft)** — BIOS integrity measurement guidelines referencing TPM attestation roles

---

## Next Steps

**Continue learning:**
→ [Sealing, Attestation, and PCRs](03_sealing_attestation_pcrs.md) — how the AK actually gets used to prove boot state

**Related topics:**
→ [TPM Fundamentals](01_tpm_fundamentals.md)

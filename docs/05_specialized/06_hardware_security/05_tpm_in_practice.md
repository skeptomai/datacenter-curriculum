---
level: specialized
estimated_time: 40 min
prerequisites:
  - 05_specialized/06_hardware_security/03_sealing_attestation_pcrs.md
  - 05_specialized/06_hardware_security/04_vendor_landscape_dtpm_vs_ftpm.md
next_recommended:
  - 05_specialized/06_hardware_security/06_measured_boot.md
tags: [tpm, bitlocker, luks, clevis, ssh, confidential-computing, tpm2-tools]
---

# TPM in Practice

## Learning Objectives

After reading this document, you will understand:
- How disk encryption tools use sealing to auto-unlock only on an unmodified boot
- How TPM-backed keys protect SSH/device identity without exposing private key material
- The end-to-end flow of a real remote attestation check
- Hands-on `tpm2-tools` commands that map directly to the concepts in prior documents

## Prerequisites

Before reading this, you should understand:
- [Sealing, Attestation, and PCRs](03_sealing_attestation_pcrs.md)
- [TPM Vendor Landscape](04_vendor_landscape_dtpm_vs_ftpm.md)

---

## 1. Disk Encryption: Seal the Key, Not the Disk

Full-disk encryption tools don't ask the TPM to encrypt the disk itself — far
too slow, and not the TPM's job. Instead, they seal the *disk's own* encryption
key to boot-state PCRs:

```
Windows BitLocker:
  Volume Master Key (VMK) is sealed to PCR[0,2,4,8,9,11] (boot measurements)
  At boot: TPM unseals VMK only if those PCRs match → OS proceeds to unlock volume
  If firmware/bootloader changed: unseal fails → falls back to recovery key prompt

Linux LUKS + clevis + tpm2:
  clevis luks bind -d /dev/sdX tpm2 '{"pcr_ids":"0,7"}'
  Seals the LUKS passphrase to the TPM, gated on PCR 0 (firmware) and 7 (Secure
  Boot state). `clevis luks unlock` retrieves it automatically at boot if PCRs
  match; otherwise prompts for the manual passphrase.
```

This is exactly the seal/unseal mechanism from the prior document, applied to
the specific problem of "don't require typing a password on every boot, but
still refuse automatic unlock if the boot chain has been tampered with."

---

## 2. TPM-Backed SSH and Device Identity Keys

A key created with `fixedTPM` set can be used to sign SSH authentication
challenges or TLS client certificates without its private half ever existing
outside the chip:

```
ssh-keygen (TPM-backed, via a PKCS#11 or TPM2 OpenSSH provider):
  Private key: lives only inside the TPM, under the Owner hierarchy
  Public key:  distributed normally (authorized_keys, CA-signed cert, etc.)

Effect: stealing the laptop's disk image does NOT give you the private key —
it's not on the disk. Without the physical TPM, the stolen image is useless
for impersonating that device.
```

This is the practical payoff of non-exportability from
[TPM Fundamentals](01_tpm_fundamentals.md): the guarantee isn't abstract, it
directly defeats a very common real-world attack (stolen laptop → stolen
credentials).

---

## 3. A Full Remote Attestation Walkthrough

Putting the whole pipeline together, end to end:

```
1. Provisioning (once):
   - Verify EK certificate chains to a trusted TPM vendor CA
   - Create an AK, certify it via credential activation (see Key Hierarchy doc)
   - Record "known-good" PCR reference values for this machine's approved
     firmware/bootloader/kernel combination

2. Every attestation check (e.g., before granting access to a secret service):
   - Verifier sends a fresh nonce
   - Machine's TPM produces TPM2_Quote(PCR[0..23], nonce) signed by the AK
   - Verifier checks:
       a. AK certificate is still the one certified in step 1
       b. Signature over (PCR values || nonce) is valid
       c. PCR values match the recorded known-good reference
   - Pass  → grant access / unseal a service-specific secret
   - Fail  → deny; something changed in the boot chain since provisioning
```

This is the mechanism behind confidential-computing attestation services and
"device health attestation" checks used by some zero-trust/endpoint security
products — same primitives, different branding.

---

## 4. Command-Line Tour (`tpm2-tools`)

A few commands that map directly onto earlier concepts, useful for actually
poking at a TPM (real hardware or `swtpm`):

```bash
# Read current PCR values (the extend-only registers from the prior doc)
tpm2_pcrread sha256:0,1,2,7

# Create a primary key under the Owner/Storage hierarchy (the SRK)
tpm2_createprimary -C o -c primary.ctx

# Create an Endorsement Key object (normally already provisioned at factory)
tpm2_createek -c ek.ctx -G rsa -u ek.pub

# Create and certify an Attestation Key against that EK
tpm2_createak -C ek.ctx -c ak.ctx -u ak.pub

# Seal a secret to current PCR state
tpm2_createpolicy --policy-pcr -l sha256:0,7 -L policy.dat
tpm2_create -C primary.ctx -u seal.pub -r seal.priv -i secret.txt -L policy.dat

# Generate a signed quote over PCRs, bound to a fresh nonce
tpm2_quote -c ak.ctx -l sha256:0,1,2,7 -q nonce.bin -m quote.msg -s quote.sig
```

---

## 5. The Bus-Sniffing Attack, Concretely

Tying back to the dTPM/fTPM trade-off: on a bare discrete TPM over LPC/SPI
without parameter encryption enabled, the plaintext VMK returned during
`unseal` crosses the physical bus between the TPM chip and the CPU. With
physical access, this traffic has been captured with inexpensive hardware to
defeat disk encryption that relied on the TPM alone with no additional PIN or
passphrase. Mitigations in practice:

- Enable **parameter/session encryption** (salted authorization sessions) so
  bus traffic itself is encrypted, not just the data at rest.
- Require an additional factor (PIN, passphrase) so sealing alone isn't the
  only gate — this is why many BitLocker deployments pair TPM auto-unlock
  with a PIN requirement on sensitive devices.
- Prefer fTPM/die-integrated form factors where physical bus exposure isn't
  possible at all (see [Vendor Landscape](04_vendor_landscape_dtpm_vs_ftpm.md)).

---

## Quick Reference

| Use case | Mechanism | Tool example |
|---|---|---|
| Auto-unlock disk on unmodified boot | Seal passphrase/VMK to PCR state | BitLocker, `clevis luks bind ... tpm2` |
| Non-exportable device identity | `fixedTPM` signing key | TPM-backed SSH/TLS client cert |
| Prove boot state to a remote party | Quote signed by AK | Confidential computing attestation services |
| Inspect/experiment directly | `tpm2-tools` against real or `swtpm` | `tpm2_pcrread`, `tpm2_quote`, etc. |

---

## What You've Learned

✅ Disk encryption tools seal the volume key to PCR state, not the whole disk, to the TPM
✅ `fixedTPM` keys give non-exportable device identity with direct real-world payoff (stolen-disk resistance)
✅ The full remote attestation flow combines EK trust, AK certification, and PCR quoting end to end
✅ `tpm2-tools` commands map directly onto the concepts from the prior three documents
✅ Bus-sniffing is a real, historically exploited dTPM weakness with concrete mitigations

---

## Hands-On Resources

- **[clevis + tpm2 PIN](https://github.com/latchset/clevis)** — practical LUKS-to-TPM binding on Linux
- **[tpm2-tools man pages](https://github.com/tpm2-software/tpm2-tools/tree/master/man)** — every command used above, documented in full
- **[Keylime](https://keylime.dev/)** — open-source TPM-based remote attestation framework, a good reference implementation of the full flow

---

## Next Steps

**Continue learning:**
→ [Measured Boot](06_measured_boot.md) — the full chain-of-trust argument behind the PCR values used throughout this document

**Related topics:**
→ [TPM Vendor Landscape](04_vendor_landscape_dtpm_vs_ftpm.md)

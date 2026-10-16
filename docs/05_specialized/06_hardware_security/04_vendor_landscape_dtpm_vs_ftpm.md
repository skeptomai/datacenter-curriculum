---
level: specialized
estimated_time: 40 min
prerequisites:
  - 05_specialized/06_hardware_security/01_tpm_fundamentals.md
next_recommended:
  - 05_specialized/06_hardware_security/05_tpm_in_practice.md
tags: [tpm, vendors, dtpm, ftpm, pluton, comparison, certification]
---

# TPM Vendor Landscape: dTPM vs. fTPM vs. Integrated

## Learning Objectives

After reading this document, you will understand:
- Why "TPM" is not one-size-fits-all — two separate axes of variance
- The real security trade-offs between discrete, firmware, and die-integrated TPMs
- Why TPM 1.2 vs. 2.0 is a much bigger difference than a version number suggests
- How algorithm support, NVRAM budget, and certification level vary even among
  compliant TPM 2.0 chips
- When you actually get to choose, and when the form factor is fixed by your hardware

## Prerequisites

Before reading this, you should understand:
- [TPM Fundamentals](01_tpm_fundamentals.md)

---

## 1. Two Separate Axes of Variance

People often ask "which TPM is better" as if it's one spectrum. It's really two
independent questions:

1. **Where does the trust boundary physically live?** (form factor)
2. **What does this specific chip/firmware actually implement?** (spec version,
   algorithms, capacity, certification)

---

## 2. Form Factor

| Type | Examples | Trust boundary | Key trade-off |
|---|---|---|---|
| **Discrete (dTPM)** | Infineon, STMicroelectronics, Nuvoton chips | Separate silicon, own tamper protections | Strongest isolation from the CPU/OS, but exposes an external bus that historically could be sniffed |
| **Firmware TPM (fTPM)** | Intel PTT (Platform Trust Technology), AMD fTPM | Code running inside a CPU-side trusted execution environment (Intel ME, AMD PSP) | No external bus to sniff, but the trusted computing base now includes CPU management firmware, which has its own CVE history |
| **Die-integrated** | Microsoft Pluton (shipping in some AMD, Intel, Qualcomm chips) | Fused directly into the CPU die | Designed specifically to remove the external-bus attack class; newer, less field history |
| **Software/virtual (vTPM)** | swtpm, cloud VM "virtual TPM" devices | Pure software, no hardware root at all | Useful for development/testing or cloud VM exposure; provides none of the real non-extractability guarantees — it's a simulator, not a root of trust |

**The bus-sniffing problem, concretely:** a discrete TPM typically talks to the
CPU over LPC or SPI. Traffic on that bus — including secrets like a disk
encryption key being handed back after a successful unseal — is not
automatically encrypted. With physical access and inexpensive hardware (a
logic analyzer, or in well-publicized cases a sub-$10 microcontroller), that
traffic has been captured in the real world to defeat BitLocker on systems
using a bare dTPM without additional protections. TPM 2.0 defines optional
**parameter encryption** (salted authorization sessions) specifically to close
this, but it isn't universally enabled by every OS integration — worth
checking rather than assuming. Firmware and die-integrated TPMs sidestep this
specific attack class entirely because there's no external bus to tap.

---

## 3. Spec Version: 1.2 vs. 2.0 Is Not a Minor Bump

| Capability | TPM 1.2 | TPM 2.0 |
|---|---|---|
| Algorithms | SHA-1, RSA only | Crypto-agile — SHA-256/384, RSA, ECC, pluggable algorithm sets |
| Key model | Persisted key blobs | Seed-derived hierarchies (see [Key Hierarchy](02_key_hierarchy_and_provisioning.md)) |
| Authorization | Simple passwords | Rich policy language (PCR state, counters, multi-factor OR/AND composition) |
| Hierarchies | Single owner model | Four separate hierarchies (Endorsement/Platform/Owner/Null) |

Windows 11's TPM requirement specifically means **2.0** — a 1.2 chip, even a
genuine one, doesn't qualify. If you're evaluating hardware for anything
security-sensitive, spec version is the first thing to check, not an
afterthought.

---

## 4. Capability Variance *Within* TPM 2.0

Even among chips that are all legitimately "TPM 2.0 compliant," real variance
shows up in:

- **Algorithm support.** Some budget dTPMs implement only RSA-2048 + SHA-256.
  Others add ECC (P-256/P-384), SHA-384, or region-specific algorithms like
  SM2/SM3 for markets requiring them. If your use case needs ECC-backed keys,
  this is worth confirming per part number, not assumed from "TPM 2.0" alone.
- **NVRAM budget and object capacity.** Cheap embedded dTPMs may offer only a
  few KB of NV storage and a handful of persistent-object slots; higher-end
  parts offer meaningfully more. This caps how many sealed secrets or
  persistent keys you can realistically keep resident at once.
- **Certification level.** FIPS 140-2/3 validation and Common Criteria EAL
  ratings (EAL4+ is typical; some parts reach higher) vary by vendor and even
  by specific firmware revision of the same part number. This matters heavily
  for regulated environments (FedRAMP, PCI-DSS) and is largely invisible to a
  typical consumer deployment or a homelab Kubernetes node.

---

## 5. fTPM vs. dTPM: An Honest, Unsettled Trade-off

This is a live debate, not a solved question:

- **fTPM removes the bus-sniffing attack class** by never putting the secret
  on an external, physically accessible bus.
- **fTPM reintroduces a different question:** is the CPU's hidden management
  firmware (Intel ME, AMD PSP) itself trustworthy and bug-free? Both have real
  CVE histories, including issues that specifically affected their TPM
  functionality.
- **dTPM's isolation is real** — a compromised OS or even a compromised CPU
  microcode update can't reach into a genuinely separate chip's internal
  state — but that isolation is undermined if the bus between them isn't
  protected (parameter encryption) and an attacker has physical access.

Neither option is categorically "more secure" in the abstract; which one wins
depends on your threat model (remote software compromise vs. physical access
to the device).

---

## 6. When You Actually Get to Choose

In practice, choice is often limited:

- **Laptops/desktops:** usually ship with whatever the CPU vendor's fTPM
  provides (Intel PTT/AMD fTPM) by default; a discrete TPM header exists on
  some motherboards for enthusiasts/enterprise buyers who want to add one.
  Server-class and bare-metal hardware is more likely to ship a real dTPM
  by default.
- **Cloud VMs:** you typically get a vTPM exposed by the hypervisor — fine for
  measured-boot-style workflows the cloud provider also controls end-to-end,
  but it is **not** a hardware root of trust in the sense this whole topic
  describes. Treat vendor claims about "TPM support" in a VM context
  accordingly.
- **Confidential computing platforms** (e.g., some SEV-SNP/TDX-backed cloud
  offerings) go further and attest the actual hardware trust boundary itself,
  not just a vTPM layered on top — a topic adjacent to, but beyond, this
  curriculum section.

---

## Quick Reference

| If you need... | Look for |
|---|---|
| Strongest physical-access resistance | A certified discrete TPM (dTPM) with parameter encryption enabled |
| No extra hardware, decent default security | fTPM (Intel PTT / AMD fTPM) — standard on nearly all modern CPUs |
| Newest bus-sniffing-resistant design | Die-integrated TPM (Microsoft Pluton), where available |
| Dev/test only, no real security guarantee | Software TPM (swtpm) or a cloud vTPM |
| Regulatory compliance (FIPS/CC) | Check the *specific part number and firmware revision's* certification, not just "TPM 2.0" |

---

## What You've Learned

✅ Form factor (dTPM/fTPM/integrated/vTPM) and spec/capability (1.2 vs 2.0, algorithms, certification) are two independent axes
✅ TPM 1.2 and 2.0 differ fundamentally in key model, algorithm agility, and authorization — not just version number
✅ Even compliant TPM 2.0 chips vary in algorithm support, NVRAM budget, and certification level by vendor and part
✅ dTPM vs. fTPM is a genuine, unresolved trade-off between bus-exposure risk and CPU-firmware-TCB risk
✅ Your actual choice is usually constrained by the hardware you already have, not a free pick

---

## Hands-On Resources

- **[TCG TPM 2.0 Library Specification](https://trustedcomputinggroup.org/resource/tpm-library-specification/)** — the baseline every compliant chip must meet
- **["TPM Genie" / TPM bus-sniffing research](https://www.usenix.org/conference/woot19/presentation/han)** — the class of attack that motivated parameter encryption
- **[Microsoft Pluton overview](https://www.microsoft.com/en-us/security/blog/2020/11/17/meet-the-microsoft-pluton-processor-the-security-chip-designed-for-the-future-of-windows-pcs/)** — the die-integrated approach

---

## Next Steps

**Continue learning:**
→ [TPM in Practice](05_tpm_in_practice.md) — BitLocker, LUKS, SSH keys, and remote attestation using everything covered so far

**Related topics:**
→ [TPM Fundamentals](01_tpm_fundamentals.md)

# Secure PQC Gateway for IoT and Side-Channel Analysis Demo

This project demonstrates two complementary cybersecurity topics in a single repository:

1. A lightweight post-quantum-inspired key exchange and encrypted telemetry flow for an IoT gateway node.
2. A side-channel analysis benchmark showing why unprotected cryptographic hardware can leak sensitive keys via power traces.

## Repository layout

- `pqc_gateway/pqc_node_gateway.py` — gateway and client script that performs a simplified PQC-style key exchange and AES-GCM telemetry transmission.
- `hardware_sca/cpa_attack_masking.py` — simulated CPA attack on masked and unmasked AES S-box execution.
- `tests/` — smoke tests for the demo flows.

## Requirements

```bash
python -m pip install -r requirements.txt
```

## Quick start

Run the gateway demo:

```bash
python -m pqc_gateway
```

Run the side-channel benchmark:

```bash
python hardware_sca/cpa_attack_masking.py
```

Run the verification tests:

```bash
pytest -q
```

## Expected behavior

### Gateway demo

The script starts a local TCP server and a client node. The gateway sends a public lattice parameter and receives a ciphertext from the client. The gateway decapsulates the shared secret, decrypts the telemetry packet, and prints the recovered sensor data.

### Side-channel benchmark

The script simulates power traces for:

- unmasked AES S-box execution, which is vulnerable to CPA;
- first-order boolean masking, which significantly reduces correlation and hides the key.

The output confirms the key recovery on the unmasked implementation and shows the masked implementation remains resilient under the simulated attack.

## Notes

This implementation is explicitly a proof-of-concept and educational demo. It is designed to be understandable and easy to run, not a production-grade post-quantum cryptography implementation or a hardware-validated side-channel platform.

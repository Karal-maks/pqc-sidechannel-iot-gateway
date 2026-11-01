import argparse
import json
import os
import socket
import threading
import time

import numpy as np
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# --- RING-LWE POLYNOMIAL LATTICE PARAMETERS (Kyber-Inspired) ---
# Polynomial Ring: R_q = Z_q[X] / (X^n + 1)
N = 16          # Polynomial degree (dimension)
Q = 3329        # Modulus (standard Kyber modulus)


def poly_add(a, b):
    return (a + b) % Q


def poly_mul(a, b):
    """Multiplies two polynomials in Z_q[X] / (X^N + 1)."""
    res = np.zeros(2 * N - 1, dtype=np.int64)
    for i in range(N):
        for j in range(N):
            res[i + j] = (res[i + j] + int(a[i]) * int(b[j])) % Q
    # Reduce modulo X^N + 1: X^N = -1
    for i in range(N - 1):
        res[i] = (res[i] - res[i + N]) % Q
    return (res[:N] % Q).astype(np.int64)


def sample_noise():
    """Centered Binomial noise distribution."""
    return np.random.randint(-1, 2, size=N, dtype=np.int64)


# --- POST-QUANTUM KEY ENCAPSULATION MECHANISM (ML-KEM) ---
def pqc_keygen():
    """Generate a simplified ML-KEM-style keypair."""
    rng = np.random.default_rng(101)
    a_param = rng.integers(0, Q, size=N, dtype=np.int64)
    s = sample_noise()
    e = sample_noise()
    t = poly_add(poly_mul(a_param, s), e)
    return s, (a_param, t)


def pqc_encapsulate(public_key):
    a_param, t = public_key
    r = sample_noise()
    e1 = sample_noise()
    e2 = sample_noise()

    u = poly_add(poly_mul(a_param, r), e1)
    m = np.random.randint(0, 2, size=N, dtype=np.int64)
    m_scaled = m * (Q // 2)
    v = poly_add(poly_add(poly_mul(t, r), e2), m_scaled)

    digest = hashes.Hash(hashes.SHA256())
    digest.update(m.tobytes())
    shared_key = digest.finalize()
    return (u, v), shared_key


def pqc_decapsulate(ciphertext, private_key):
    u, v = ciphertext
    s = private_key
    mn = (v - poly_mul(u, s)) % Q
    m_rec = np.zeros(N, dtype=np.int64)
    for i in range(N):
        val = mn[i]
        diff_to_zero = min(val, Q - val)
        diff_to_half = abs(val - (Q // 2))
        m_rec[i] = 0 if diff_to_zero < diff_to_half else 1

    digest = hashes.Hash(hashes.SHA256())
    digest.update(m_rec.tobytes())
    return digest.finalize()


# --- NETWORK IOT GATEWAY & CLIENT NODE IMPLEMENTATION ---
HOST = "127.0.0.1"
PORT = 9555


def run_pqc_gateway_server(host=HOST, port=PORT):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(1)
    conn, _ = server.accept()

    private_key, public_key = pqc_keygen()
    a_p, t_p = public_key
    pk_payload = json.dumps({"a": a_p.tolist(), "t": t_p.tolist()}).encode()
    conn.sendall(pk_payload)

    raw_ct = conn.recv(4096).decode()
    ct_data = json.loads(raw_ct)
    u = np.array(ct_data["u"], dtype=np.int64)
    v = np.array(ct_data["v"], dtype=np.int64)

    server_session_key = pqc_decapsulate((u, v), private_key)

    encrypted_packet = conn.recv(4096)
    nonce = encrypted_packet[:12]
    tag_and_ciphertext = encrypted_packet[12:]

    aesgcm = AESGCM(server_session_key)
    decrypted_bytes = aesgcm.decrypt(nonce, tag_and_ciphertext, None)
    telemetry = json.loads(decrypted_bytes.decode())

    print("\n[GATEWAY SERVER RECEIVED & VERIFIED]")
    print(f"  -> Quantum-Resistant Session Key: {server_session_key.hex()[:32]}...")
    print(f"  -> Decrypted Node Telemetry: {telemetry}")
    conn.close()
    server.close()
    return telemetry


def run_iot_node_client(host=HOST, port=PORT, startup_delay=0.5):
    time.sleep(startup_delay)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))

    raw_pk = client.recv(4096).decode()
    pk_data = json.loads(raw_pk)
    public_key = (np.array(pk_data["a"], dtype=np.int64), np.array(pk_data["t"], dtype=np.int64))

    (u, v), client_session_key = pqc_encapsulate(public_key)
    ct_payload = json.dumps({"u": u.tolist(), "v": v.tolist()}).encode()
    client.sendall(ct_payload)

    telemetry_data = {
        "sensor_id": "STM32_MOTOR_NODE_01",
        "rpm": 1750,
        "vibration_rms": 0.72,
        "iq_current": 2.00,
        "status": "HEALTHY",
    }
    nonce = os.urandom(12)
    aesgcm = AESGCM(client_session_key)
    ciphertext = aesgcm.encrypt(nonce, json.dumps(telemetry_data).encode(), None)

    client.sendall(nonce + ciphertext)
    print("\n[IOT CLIENT NODE TRANSMITTED]")
    print(f"  -> Quantum-Resistant Session Key: {client_session_key.hex()[:32]}...")
    print(f"  -> Encrypted Payload Length: {len(ciphertext)} bytes")
    client.close()
    return telemetry_data


def run_demo(host=HOST, port=PORT, startup_delay=0.5):
    server_thread = threading.Thread(target=run_pqc_gateway_server, args=(host, port))
    client_thread = threading.Thread(target=run_iot_node_client, args=(host, port, startup_delay))

    server_thread.start()
    client_thread.start()

    server_thread.join()
    client_thread.join()


def main():
    parser = argparse.ArgumentParser(description="Run the PQC gateway demo.")
    parser.add_argument("--host", default=HOST, help="Gateway bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=PORT, help=f"Gateway port (default: {PORT})")
    parser.add_argument("--delay", type=float, default=0.5, help="Startup delay before the client connects.")
    args = parser.parse_args()
    run_demo(args.host, args.port, args.delay)


if __name__ == "__main__":
    main()
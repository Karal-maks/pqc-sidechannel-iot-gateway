from hardware_sca.cpa_attack_masking import (
    perform_cpa_attack,
    simulate_traces,
)


def test_cpa_recovers_unmasked_key():
    plaintexts, traces = simulate_traces(num_traces=600, secret_key=0x5D, masked=False)
    recovered_key, corr, _ = perform_cpa_attack(plaintexts, traces)

    assert recovered_key == 0x5D
    assert corr > 0.6


def test_masked_trace_weakens_attack():
    plaintexts_m, traces_m = simulate_traces(num_traces=600, secret_key=0x5D, masked=True)
    recovered_key_m, corr_m, _ = perform_cpa_attack(plaintexts_m, traces_m)

    assert recovered_key_m != 0x5D
    assert corr_m < 0.2

from pqc_gateway.pqc_node_gateway import run_demo


def test_gateway_demo_runs_without_errors():
    run_demo(host="127.0.0.1", port=9566, startup_delay=0.1)

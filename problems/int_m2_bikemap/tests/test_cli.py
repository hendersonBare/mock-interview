import socket

from bikemap.cli import main


def test_health(map_server, capsys):
    assert main(["--base-url", map_server.url, "health"]) == 0
    assert capsys.readouterr().out.strip() == "ok"


def test_health_unreachable(capsys):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    assert main(["--base-url", f"http://127.0.0.1:{port}", "health"]) == 1
    assert "error" in capsys.readouterr().err

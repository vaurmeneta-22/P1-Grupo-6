import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
import threading
import unittest
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location("backend_opensees", os.path.join(ROOT, "scripts", "backend_opensees.py"))
BACKEND = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BACKEND)


class BackendTests(unittest.TestCase):
    def test_validates_the_three_supported_scenarios(self):
        cases = [
            {"case_id": "A", "element_id": 147, "width_cm": 50, "height_cm": 75},
            {"case_id": "B", "node_id": 1, "support_type": "pinned"},
            {"case_id": "C", "element_id": 66, "width_cm": 40, "height_cm": 40},
        ]
        for accepted in cases:
            self.assertEqual(BACKEND.validate_request(accepted), accepted)
        with self.assertRaises(ValueError):
            BACKEND.validate_request({**cases[2], "element_id": 99})
        with self.assertRaises(ValueError):
            BACKEND.validate_request({**cases[0], "width_cm": 40})

    def test_server_can_start_as_a_background_process(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        script = os.path.join(ROOT, "scripts", "backend_opensees.py")
        process = subprocess.Popen([sys.executable, script, "--port", str(port)],
                                   cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.time() + 5
            while time.time() < deadline and process.poll() is None:
                try:
                    with urlopen("http://127.0.0.1:%s/health" % port, timeout=0.5) as response:
                        self.assertEqual(response.status, 200)
                        self.assertTrue(json.load(response)["ready"])
                        return
                except Exception:
                    time.sleep(0.1)
            self.fail("El servidor en segundo plano no respondió al health check")
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)

    def test_health_and_invalid_request_http_responses(self):
        server = HTTPServer(("127.0.0.1", 0), BACKEND.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = "http://127.0.0.1:%s" % server.server_port
        try:
            with urlopen(base + "/health", timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertTrue(json.load(response)["ready"])
            request = Request(base + "/reanalyze", data=b'{"case_id":"A"}',
                              headers={"Content-Type": "application/json"}, method="POST")
            with self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=2)
            self.assertEqual(error.exception.code, 400)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()

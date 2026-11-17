import hashlib
import http.client
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('freeze_inputs', Path(__file__).resolve().parents[1] / 'scientific-workflows/sra-search/scripts/freeze_inputs.py')
inputs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inputs)


class InputDownloadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name) / 'input.gz'
        self.payload = b'complete input bytes'
        self.digest = hashlib.md5(self.payload).hexdigest()

    def download(self, attempts=3):
        inputs.download('https://example.org/input.gz', self.target, self.digest, len(self.payload), attempts=attempts)

    @patch.object(inputs.time, 'sleep')
    @patch.object(inputs.urllib.request, 'urlopen')
    def test_recovers_from_remote_disconnect_and_invalid_download(self, request, sleep):
        request.side_effect = [http.client.RemoteDisconnected('closed'), io.BytesIO(b'truncated'), io.BytesIO(self.payload)]
        self.download()
        self.assertEqual(self.target.read_bytes(), self.payload)
        self.assertFalse(self.target.with_suffix('.partial').exists())
        self.assertEqual(request.call_args.kwargs['timeout'], 60)
        self.assertEqual(sleep.call_count, 2)

    @patch.object(inputs.time, 'sleep')
    @patch.object(inputs.urllib.request, 'urlopen')
    def test_checksum_failure_never_replaces_existing_file(self, request, sleep):
        self.target.write_bytes(b'previous input')
        request.side_effect = lambda *args, **kwargs: io.BytesIO(b'x' * len(self.payload))
        with self.assertRaises(ValueError):
            self.download(attempts=2)
        self.assertEqual(self.target.read_bytes(), b'previous input')
        self.assertFalse(self.target.with_suffix('.partial').exists())
        self.assertEqual(request.call_count, 2)

    @patch.object(inputs.urllib.request, 'urlopen')
    def test_reuses_only_verified_download(self, request):
        self.target.write_bytes(self.payload)
        self.download()
        request.assert_not_called()

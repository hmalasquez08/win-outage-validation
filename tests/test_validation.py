import hashlib, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

from win_validation import cli
from win_validation.integrity import audit

class ValidationTests(unittest.TestCase):
    def test_no_credentials_in_example(self):
        text=(Path.cwd()/'.env.example').read_text()
        self.assertIn('CLOUDFLARE_API_TOKEN=',text)
        self.assertNotRegex(text,r'(?i)(bearer\s+[a-z0-9]|api[_-]?key\s*[:=]\s*[^\s]+)')

    def test_auth_sources_not_in_public_registry(self):
        for source in ('cloudflare_radar','x_official','twexapi_x'):
            self.assertNotIn(source,cli.SOURCES)

    def test_env_secret_store_is_gitignored(self):
        text=(Path.cwd()/'.gitignore').read_text(encoding='utf-8')
        self.assertRegex(text,r'(?m)^\.env$')
        self.assertIn('!.env.example',text)

    def test_generated_evidence_bundle_audits_cleanly(self):
        result=audit(Path.cwd())
        self.assertEqual(result['integrity_errors'],[])

    def test_artifact_manifest_hash(self):
        with tempfile.TemporaryDirectory() as td:
            old=(cli.ROOT,cli.EV,cli.MANIFEST)
            try:
                cli.ROOT=Path(td); cli.EV=cli.ROOT/'evidencias'; cli.MANIFEST=cli.EV/'manifest.jsonl'; cli.mkdirs()
                with patch('urllib.request.urlopen',side_effect=Exception('offline')):
                    item,_=cli.request('test','https://example.invalid/','test')
                raw=(cli.ROOT/item['artifact_path']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),item['sha256'])
                self.assertEqual(json.loads(cli.MANIFEST.read_text())['result_status'],'TRANSIENT_ERROR')
            finally: cli.ROOT,cli.EV,cli.MANIFEST=old

if __name__=='__main__': unittest.main()

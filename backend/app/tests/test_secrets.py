"""Secret detection tests: detection, masking, and the never-leak guarantee."""

from __future__ import annotations

import json

from app.services.secrets_detector import (
    detect_secrets,
    mask_secret,
    redact_evidence,
    scan_files_for_secrets,
    shannon_entropy,
)

RAW_GITHUB = "ghp_16C7e42F292c6912E7710c838347Ae178B4a"
RAW_AWS = "AKIA5K2HJDGF8X3P7QRW"


class TestMasking:
    def test_mask_format(self):
        masked = mask_secret(RAW_GITHUB)
        assert masked.startswith("ghp_")
        assert masked.endswith("8B4a")  # last 4 chars visible
        assert RAW_GITHUB[4:20] not in masked

    def test_mask_never_returns_full_value(self):
        for raw in [RAW_AWS, RAW_GITHUB, "sk_live_" + "a" * 24]:
            m = mask_secret(raw)
            assert len(m) < len(raw)
            assert m != raw

    def test_short_value_fully_hidden(self):
        assert set(mask_secret("abc")) <= {"*"}

    def test_redact_evidence_replaces_value(self):
        ev = 'token = "ghp_secretvalue123"  # prod'
        out = redact_evidence(ev, ["ghp_secretvalue123"])
        assert "ghp_secretvalue123" not in out
        assert "[REDACTED]" in out


class TestDetection:
    def test_github_token_detected_high_confidence(self):
        fs = detect_secrets("cfg.py", f'token = "{RAW_GITHUB}"')
        f = next(f for f in fs if f["rule_id"] == "SEC-GITHUB-TOKEN")
        assert f["severity"] == "CRITICAL"
        assert f["confidence"] == "HIGH"

    def test_aws_key_detected(self):
        fs = detect_secrets("settings.py", f'aws = "{RAW_AWS}"')
        assert any(f["rule_id"] == "SEC-AWS-AKID" for f in fs)

    def test_private_key_block(self):
        fs = detect_secrets("id_rsa.bak", "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----")
        assert any(f["rule_id"] == "SEC-PRIVATE-KEY" for f in fs)

    def test_db_url_credentials(self):
        fs = detect_secrets(
            "db.py",
            "DATABASE_URL='postgresql://admin:S3cretPw@db.internal:5432/prod'")
        assert any(f["rule_id"] == "SEC-DB-URL-CREDS" for f in fs)

    def test_generic_credential_with_entropy_gate(self):
        weak = 'password = "aaaaaaaaaaaaaaaaaa"'          # low entropy → skipped
        strong = 'password = "Xk9$mQ2vLp7#RtZ1"'          # mixed classes → flagged
        fs_weak = detect_secrets("a.py", weak)
        fs_strong = detect_secrets("b.py", strong)
        assert not any(f["rule_id"] == "SEC-GENERIC-CREDENTIAL" for f in fs_weak)
        assert any(f["rule_id"] == "SEC-GENERIC-CREDENTIAL" for f in fs_strong)

    def test_placeholders_not_flagged(self):
        fs = detect_secrets("config.py", 'api_key = "${API_KEY_FROM_ENV}"')
        assert fs == []

    def test_process_env_reference_not_flagged(self):
        code = 'api_key = os.environ["API_KEY"]\ntoken = process.env.GH_TOKEN'
        assert detect_secrets("app.ts", code) == []


class TestNeverLeak:
    def test_no_raw_secret_anywhere_in_serialized_findings(self):
        files = {
            "a.py": f'token = "{RAW_GITHUB}"',
            "b.env": f"AWS_KEY={RAW_AWS}",
        }
        fs = scan_files_for_secrets(files)
        blob = json.dumps(fs)
        assert RAW_GITHUB not in blob
        assert RAW_AWS not in blob

    def test_evidence_is_redacted_but_context_kept(self):
        fs = detect_secrets("a.py", f'GITHUB_TOKEN="{RAW_GITHUB}"')
        f = fs[0]
        assert "[REDACTED]" in f["evidence"]
        assert "GITHUB_TOKEN" in f["evidence"]
        assert f["masked_preview"].endswith("8B4a")

    def test_entropy_helper_sane(self):
        assert shannon_entropy("") == 0
        assert shannon_entropy("aaaa") < shannon_entropy("aB3$xY9#")

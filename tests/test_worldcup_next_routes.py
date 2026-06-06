import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORLDCUP = ROOT / "projects" / "worldcup-ai"


def test_worldcup_next_api_route_tests_pass_without_network():
    env = {
        **os.environ,
        "NEXT_PUBLIC_SUPABASE_URL": "http://localhost",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY": "anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
        "FLW_SECRET_KEY": "secret-key",
        "FLW_SECRET_HASH": "secret-hash",
    }
    result = subprocess.run(
        [
            "npx",
            "vitest",
            "run",
            "app/api/generate/route.test.ts",
            "app/api/webhooks/flutterwave/route.test.ts",
        ],
        cwd=WORLDCUP,
        env=env,
        check=False,
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_worldcup_post_route_only_blocks_twitter_without_connection():
    source = (WORLDCUP / "app/api/post/route.ts").read_text()

    twitter_gate = source.index("if (platform === 'twitter')")
    twitter_block = source[twitter_gate:]
    assert "Connect ${platform} in Settings before posting." in twitter_block
    assert "if (!connection)" in twitter_block
    assert "Connect ${platform} in Settings before posting." not in source[:twitter_gate]

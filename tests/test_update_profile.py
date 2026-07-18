import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import update_profile  # noqa: E402


README = """<header>
<!-- github-bio:start -->
old bio
<!-- github-bio:end -->
<toolbox>keep me</toolbox>
<!-- profile-signals:start -->
old signals
<!-- profile-signals:end -->
"""


def fresh_stats():
    return {
        "human_readable_total": "56 hrs 44 mins",
        "ai_input_tokens": 3_037_704_589,
        "ai_output_tokens": 12_277_502,
        "is_up_to_date": True,
        "percent_calculated": 100,
    }


class FormatTokensTests(unittest.TestCase):
    def test_formats_compact_counts(self):
        cases = {
            0: "0",
            999: "999",
            1_000: "1K",
            1_250_000: "1.25M",
            3_049_982_091: "3.05B",
        }
        for count, expected in cases.items():
            with self.subTest(count=count):
                self.assertEqual(update_profile.format_tokens(count), expected)

    def test_rejects_negative_count(self):
        with self.assertRaises(ValueError):
            update_profile.format_tokens(-1)


class RenderingTests(unittest.TestCase):
    def test_updates_only_marker_blocks(self):
        rendered = update_profile.render_profile(
            README,
            "Researcher & vibe coder",
            fresh_stats(),
        )
        self.assertIn("Researcher &amp; vibe coder", rendered)
        self.assertIn("3.05B WakaTime-tracked AI tokens", rendered)
        self.assertIn("<toolbox>keep me</toolbox>", rendered)

    def test_rejects_missing_or_duplicate_markers(self):
        with self.assertRaises(RuntimeError):
            update_profile.render_profile("no markers", "bio", fresh_stats())
        with self.assertRaises(RuntimeError):
            update_profile.render_profile(
                README.replace(
                    update_profile.GITHUB_BIO_END,
                    update_profile.GITHUB_BIO_END * 2,
                ),
                "bio",
                fresh_stats(),
            )

    def test_rejects_missing_stats_fields(self):
        stats = fresh_stats()
        del stats["ai_output_tokens"]
        with self.assertRaises(RuntimeError):
            update_profile.render_profile(README, "bio", stats)


class FetchTests(unittest.TestCase):
    def test_normalizes_github_bio(self):
        with mock.patch.object(
            update_profile,
            "_fetch_json",
            return_value=(200, {"bio": "Researcher  &\n vibe coder"}),
        ):
            bio = update_profile.fetch_github_bio("MarioZZJ", "token")
        self.assertEqual(bio, "Researcher & vibe coder")

    def test_retries_stale_wakatime_stats(self):
        stale = {"data": {"is_up_to_date": False, "percent_calculated": 60}}
        fresh = {"data": fresh_stats()}
        with (
            mock.patch.object(
                update_profile,
                "_fetch_json",
                side_effect=[(202, stale), (200, fresh)],
            ) as fetch,
            mock.patch.object(update_profile.time, "sleep") as sleep,
        ):
            result = update_profile.fetch_wakatime_stats("waka_secret")
        self.assertEqual(result, fresh_stats())
        self.assertEqual(fetch.call_count, 2)
        sleep.assert_called_once_with(update_profile.WAKATIME_RETRY_SECONDS)

    def test_fails_when_wakatime_stats_never_refresh(self):
        stale = {"data": {"is_up_to_date": False, "percent_calculated": 60}}
        with (
            mock.patch.object(update_profile, "_fetch_json", return_value=(202, stale)),
            mock.patch.object(update_profile.time, "sleep"),
        ):
            with self.assertRaises(RuntimeError):
                update_profile.fetch_wakatime_stats("waka_secret")


class UpdateTests(unittest.TestCase):
    def test_api_failure_preserves_last_good_readme(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            path.write_text(README, encoding="utf-8")
            with (
                mock.patch.object(
                    update_profile, "fetch_github_bio", return_value="new bio"
                ),
                mock.patch.object(
                    update_profile,
                    "fetch_wakatime_stats",
                    side_effect=RuntimeError("network failure"),
                ),
            ):
                with self.assertRaises(RuntimeError):
                    update_profile.update_profile(path, "owner", "github", "wakatime")
            self.assertEqual(path.read_text(encoding="utf-8"), README)


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

from win_validation.social import SocialError, _ApifyCredentialPool, _run_actor


class ApifyCredentialTests(unittest.TestCase):
    def test_rotation_and_deduplication(self):
        pool = _ApifyCredentialPool({"APIFY": "first", "APIFY_2": "second", "APIFY_3": "first"})
        with patch("win_validation.social._run_actor", return_value=([], {"http_status": 200})) as actor:
            for _ in range(3):
                pool.run("actor", {}, 30)
        self.assertEqual([call.args[2] for call in actor.call_args_list], ["first", "second", "first"])

    def test_unauthorized_token_is_removed_and_retried(self):
        pool = _ApifyCredentialPool({"APIFY": "invalid", "APIFY_2": "valid"})
        with patch("win_validation.social._run_actor", side_effect=[SocialError("unauthorized", {"http_status": 401}), ([], {"http_status": 200})]) as actor:
            pool.run("actor", {}, 30)
        self.assertEqual(actor.call_count, 2)
        self.assertEqual(pool.last_slot, "APIFY_2")
        self.assertEqual(pool.rejected_slots, ["APIFY"])

    def test_timeout_is_not_retried(self):
        pool = _ApifyCredentialPool({"APIFY": "first", "APIFY_2": "second"})
        with patch("win_validation.social._run_actor", side_effect=SocialError("timeout", {"http_status": None})) as actor:
            with self.assertRaises(SocialError):
                pool.run("actor", {}, 30)
        self.assertEqual(actor.call_count, 1)

    def test_explicit_rejection_tries_other_accounts(self):
        for status in (402, 403, 429):
            with self.subTest(status=status):
                pool = _ApifyCredentialPool({"APIFY": "first", "APIFY_2": "second"})
                with patch("win_validation.social._run_actor", side_effect=[SocialError("rejected", {"http_status": status}), ([], {"http_status": 200})]) as actor:
                    pool.run("actor", {}, 30)
                self.assertEqual(actor.call_count, 2)
                self.assertEqual(pool.last_slot, "APIFY_2")

    def test_all_rejected_stops_after_each_account_once(self):
        pool = _ApifyCredentialPool({"APIFY": "first", "APIFY_2": "second"})
        with patch("win_validation.social._run_actor", side_effect=SocialError("rate limit", {"http_status": 429})) as actor:
            with self.assertRaises(SocialError):
                pool.run("actor", {}, 30)
        self.assertEqual(actor.call_count, 2)

    def test_server_error_is_not_retried(self):
        pool = _ApifyCredentialPool({"APIFY": "first", "APIFY_2": "second"})
        with patch("win_validation.social._run_actor", side_effect=SocialError("server error", {"http_status": 500})) as actor:
            with self.assertRaises(SocialError):
                pool.run("actor", {}, 30)
        self.assertEqual(actor.call_count, 1)

    def test_sync_actor_accepts_201_response(self):
        with patch("win_validation.social.request", return_value=({"http_status": 201}, b"[]")):
            items, _record = _run_actor("actor", {}, "token", 30)
        self.assertEqual(items, [])


if __name__ == "__main__":
    unittest.main()

from app.security.auth import should_skip_auth


def test_only_public_subscription_feed_skips_panel_auth():
    assert should_skip_auth("sg_subscription_v1") is True
    assert should_skip_auth("sg_subscription_v1_info") is False

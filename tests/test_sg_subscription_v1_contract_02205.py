from app.clients.sg_subscription import _canonical_uri, canonical_profile_ids


def test_exact_nine_canonical_profiles():
    assert canonical_profile_ids() == (
        "xray_reality_tcp",
        "xray_xhttp_reality",
        "xray_xhttp_tls",
        "xray_hysteria2",
        "amneziawg",
        "amneziawg3",
        "mieru",
        "anytls",
        "tuic",
    )


def test_anytls_and_tuic_are_canonicalized():
    anytls = (
        "anytls://pw@example.com:9443?security=tls&sni=example.com"
        "&fp=firefox&type=tcp#Shany"
    )
    assert _canonical_uri("anytls", anytls) == (
        "anytls://pw@example.com:9443/?sni=example.com#Shany"
    )

    tuic = (
        "tuic://uuid:pw@example.com:10443?congestion_control=bbr"
        "&udp_relay_mode=native&alpn=h3&sni=example.com#Shany"
    )
    assert _canonical_uri("tuic", tuic) == (
        "tuic://uuid:pw@example.com:10443/?congestion_control=bbr"
        "&udp_relay_mode=native&alpn=h3&sni=example.com#Shany"
    )

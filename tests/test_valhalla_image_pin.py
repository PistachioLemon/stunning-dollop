import pytest

from nova.routing.image_pin import RoutingImagePin, VALHALLA_3_8_3_ARM64


def test_valhalla_383_arm64_pin_is_immutable_and_valid():
    VALHALLA_3_8_3_ARM64.validate()
    assert VALHALLA_3_8_3_ARM64.image.endswith(
        "@sha256:58c7dd3fb256f306b00c558fb76aea9fd4fb804edd831e2b4847c26511cca507"
    )


def test_valhalla_latest_tag_is_rejected():
    pin = RoutingImagePin(
        engine="valhalla",
        version="3.8.3",
        architecture="linux/arm64",
        image="ghcr.io/gis-ops/docker-valhalla/valhalla:latest@sha256:" + "a" * 64,
        digest="a" * 64,
    )
    with pytest.raises(ValueError, match="latest"):
        pin.validate()


def test_valhalla_digest_mismatch_is_rejected():
    pin = RoutingImagePin(
        engine="valhalla",
        version="3.8.3",
        architecture="linux/arm64",
        image="ghcr.io/gis-ops/docker-valhalla/valhalla@sha256:" + "a" * 64,
        digest="b" * 64,
    )
    with pytest.raises(ValueError, match="pinned"):
        pin.validate()

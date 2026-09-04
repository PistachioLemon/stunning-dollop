from nova.logistics.epcis import epcis_to_freight, freight_to_epcis
from nova.logistics.rfid import RfidRead, reconcile_receiving


def test_epcis_shipping_round_trip():
    raw = {
        "type": "ObjectEvent",
        "eventID": "urn:uuid:ship-1",
        "eventTime": "2026-08-20T12:00:00Z",
        "action": "OBSERVE",
        "bizStep": "https://ref.gs1.org/cbv/BizStep-shipping",
        "epcList": ["urn:epc:id:sgtin:0614141.107346.2017"],
        "readPoint": {"id": "urn:epc:id:sgln:0614141.07346.1234"},
    }
    event = epcis_to_freight(raw)
    assert event.event_type == "SHIPPING"
    back = freight_to_epcis(event)
    assert back["eventID"] == raw["eventID"]
    assert back["epcList"] == raw["epcList"]
    assert back["readPoint"]["id"] == raw["readPoint"]["id"]


def test_epcis_aggregation_and_sensor_data():
    raw = {
        "type": "AggregationEvent",
        "eventID": "urn:uuid:pallet-1",
        "eventTime": "2026-08-20T12:00:00Z",
        "action": "ADD",
        "parentID": "urn:epc:id:sscc:0614141.1234567890",
        "childEPCs": ["urn:epc:id:sgtin:0614141.107346.1"],
        "sensorElementList": [{"sensorReport": [{"type": "Temperature", "value": 36.5, "uom": "FAH"}]}],
    }
    event = epcis_to_freight(raw)
    assert event.event_type == "AGGREGATION"
    assert event.parent_id == raw["parentID"]
    assert event.sensor["value"] == 36.5
    back = freight_to_epcis(event)
    assert back["parentID"] == raw["parentID"]
    assert back["sensorElementList"][0]["sensorReport"][0]["value"] == 36.5


def test_rfid_receiving_deduplicates_and_reconciles():
    reads = [
        RfidRead("epc:1", "dock-1"),
        RfidRead("epc:1", "dock-1"),
        RfidRead("epc:3", "dock-1"),
    ]
    result = reconcile_receiving(reads, ["epc:1", "epc:2"])
    assert result.unique_epcs == ("epc:1", "epc:3")
    assert result.duplicate_reads == 1
    assert result.missing_expected == ("epc:2",)
    assert result.unexpected == ("epc:3",)

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


BUSINESS_STEP_MAP = {
    "shipping": "SHIPPING",
    "receiving": "RECEIVING",
    "loading": "LOADING",
    "unloading": "UNLOADING",
    "arriving": "ARRIVAL",
    "departing": "DEPARTURE",
    "storing": "STORAGE",
    "commissioning": "COMMISSIONING",
}


@dataclass(frozen=True)
class FreightEvent:
    event_id: str
    event_type: str
    occurred_at: str
    object_ids: tuple[str, ...] = ()
    location: str | None = None
    business_step: str | None = None
    disposition: str | None = None
    parent_id: str | None = None
    sensor: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _business_step(value: Any) -> str | None:
    raw = str(value or "").rstrip("/").split("/")[-1]
    if raw.lower().startswith("bizstep-"):
        raw = raw[len("BizStep-"):]
    raw = raw.lower()
    return BUSINESS_STEP_MAP.get(raw, raw.upper() or None)


def epcis_to_freight(event: dict[str, Any]) -> FreightEvent:
    event_type = str(event.get("type", "ObjectEvent"))
    action = str(event.get("action", "OBSERVE")).upper()
    business_step = _business_step(event.get("bizStep"))

    internal_type = {
        ("AggregationEvent", "ADD"): "AGGREGATION",
        ("AggregationEvent", "DELETE"): "DISAGGREGATION",
        ("ObjectEvent", "OBSERVE"): business_step or "OBSERVATION",
        ("ObjectEvent", "ADD"): business_step or "OBJECT_ADD",
        ("ObjectEvent", "DELETE"): business_step or "OBJECT_REMOVE",
    }.get((event_type, action), business_step or event_type.upper())

    read_point = event.get("readPoint") or {}
    biz_location = event.get("bizLocation") or {}
    location = read_point.get("id") or biz_location.get("id")
    object_ids = tuple(event.get("epcList") or event.get("childEPCs") or ())
    sensor = {}
    sensor_element_list = event.get("sensorElementList") or []
    if sensor_element_list:
        reports = sensor_element_list[0].get("sensorReport") or []
        if reports:
            first = reports[0]
            sensor = {
                "type": first.get("type"),
                "value": first.get("value"),
                "uom": first.get("uom"),
            }

    return FreightEvent(
        event_id=str(event.get("eventID") or f"urn:requantai:event:{event.get('eventTime', _now())}"),
        event_type=internal_type,
        occurred_at=str(event.get("eventTime") or _now()),
        object_ids=object_ids,
        location=location,
        business_step=business_step,
        disposition=event.get("disposition"),
        parent_id=event.get("parentID"),
        sensor=sensor,
        extensions={"epcis_type": event_type, "epcis_action": action},
    )


def freight_to_epcis(event: FreightEvent) -> dict[str, Any]:
    is_aggregation = event.event_type in {"AGGREGATION", "DISAGGREGATION"} or event.parent_id is not None
    epcis_type = "AggregationEvent" if is_aggregation else "ObjectEvent"
    action = "OBSERVE"
    if event.event_type == "AGGREGATION":
        action = "ADD"
    elif event.event_type == "DISAGGREGATION":
        action = "DELETE"

    result: dict[str, Any] = {
        "type": epcis_type,
        "eventID": event.event_id,
        "eventTime": event.occurred_at,
        "action": action,
    }
    if is_aggregation:
        result["parentID"] = event.parent_id
        result["childEPCs"] = list(event.object_ids)
    else:
        result["epcList"] = list(event.object_ids)
    if event.location:
        result["readPoint"] = {"id": event.location}
    if event.business_step:
        result["bizStep"] = f"https://ref.gs1.org/cbv/BizStep-{event.business_step.lower()}"
    if event.disposition:
        result["disposition"] = event.disposition
    if event.sensor:
        result["sensorElementList"] = [{
            "sensorReport": [{
                "type": event.sensor.get("type"),
                "value": event.sensor.get("value"),
                "uom": event.sensor.get("uom"),
            }]
        }]
    return result

# A number rented from LiveKit: inbound only, no trunk; its dispatch rule is assigned to it in
# LiveKit (`lk number update`). A provider's SIP trunk (Plivo, Telnyx, Twilio, Exotel, Vobiz)
# can also call out and transfer.
LIVEKIT_PROVIDER = "livekit"
SIP_TRUNK_PROVIDER = "sip_trunk"
PROVIDERS = (LIVEKIT_PROVIDER, SIP_TRUNK_PROVIDER)

E164_PATTERN = r"^\+[1-9]\d{6,14}$"

PHONE_CHANNEL = "phone"
INBOUND_CALL_ROOM_PREFIX = "call-"
OUTBOUND_CALL_ROOM_PREFIX = "out-"
LIVEKIT_RESOURCE_PREFIX = "studio"

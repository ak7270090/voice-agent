"""Starting points for new agents: settings, plus a flow where the job has fixed steps."""

from studio_api.agents.constants import ENGLISH
from studio_api.agents.schemas import AgentFields, AgentTemplate, VoiceSettings
from studio_api.config import Settings
from studio_api.flows.templates import (
    build_clinic_booking_flow,
    build_lead_qualifier_flow,
    build_reminder_flow,
)

CLINIC_BOOKING_INSTRUCTIONS = """You are the receptionist of City Hospital.
Help callers book, move or cancel an appointment, and answer questions about the hospital.
Be warm and brief."""

REMINDER_INSTRUCTIONS = """You call patients to remind them of tomorrow's appointment.
Confirm they are coming, or offer to move the appointment. Keep the call short."""

LEAD_QUALIFIER_INSTRUCTIONS = """You call people who asked about our product.
Find out what they need, their budget and their timeline, and offer a meeting with sales."""

DELIVERY_FOLLOW_UP_INSTRUCTIONS = """You call customers about a delivery.
Confirm the address and a delivery slot that suits them."""


def build_templates(settings: Settings) -> list[AgentTemplate]:
    voice = VoiceSettings(
        stt_model=settings.default_stt_model,
        tts_model=settings.default_tts_model,
        voice=settings.default_voice,
    )

    def fields(name: str, instructions: str, greeting: str) -> AgentFields:
        return AgentFields(
            name=name,
            instructions=instructions,
            greeting=greeting,
            llm_model=settings.default_llm_model,
            languages=[ENGLISH],
            language_settings={ENGLISH: voice},
        )

    return [
        AgentTemplate(
            id="clinic-booking",
            name="Clinic booking",
            summary="Books, moves and cancels appointments; answers from hospital documents.",
            channel_label="Inbound",
            fields=fields(
                "Clinic receptionist",
                CLINIC_BOOKING_INSTRUCTIONS,
                "Welcome to City Hospital. How can I help you today?",
            ),
            flow=build_clinic_booking_flow(settings.demo_clinic_api_url),
        ),
        AgentTemplate(
            id="appointment-reminder",
            name="Appointment reminder",
            summary="Calls tomorrow's patients, confirms or reschedules, leaves voicemail.",
            channel_label="Outbound campaign",
            fields=fields(
                "Appointment reminder",
                REMINDER_INSTRUCTIONS,
                "Hello, this is City Hospital calling about your appointment tomorrow.",
            ),
            flow=build_reminder_flow(),
        ),
        AgentTemplate(
            id="lead-qualifier",
            name="Lead qualifier",
            summary="Asks about need, budget and timeline, then books a meeting.",
            channel_label="Outbound",
            fields=fields(
                "Lead qualifier",
                LEAD_QUALIFIER_INSTRUCTIONS,
                "Hi, thanks for your interest. Do you have two minutes to talk about it?",
            ),
            flow=build_lead_qualifier_flow(),
        ),
        AgentTemplate(
            id="delivery-follow-up",
            name="Delivery follow-up",
            summary="Confirms the address and a delivery slot.",
            channel_label="Outbound",
            fields=fields(
                "Delivery follow-up",
                DELIVERY_FOLLOW_UP_INSTRUCTIONS,
                "Hello, I'm calling about your delivery. Is now a good time?",
            ),
        ),
    ]

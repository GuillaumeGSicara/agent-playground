from a2a.types import AgentCard, AgentCapabilities, AgentInterface, AgentSkill
from a2a.utils.constants import PROTOCOL_VERSION_CURRENT, TransportProtocol

from agent_playground.constants import AgentMeta, SkillId


def build_agent_card(url: str) -> AgentCard:
    card: AgentCard = AgentCard()
    card.name = AgentMeta.NAME
    card.description = AgentMeta.DESCRIPTION
    card.version = AgentMeta.VERSION
    card.default_input_modes.append("text/plain")
    card.default_output_modes.append("text/plain")
    card.capabilities.CopyFrom(AgentCapabilities(streaming=True, push_notifications=False))

    iface: AgentInterface = AgentInterface()
    iface.url = url
    iface.protocol_binding = TransportProtocol.JSONRPC.value
    iface.protocol_version = PROTOCOL_VERSION_CURRENT
    card.supported_interfaces.append(iface)

    skill: AgentSkill = AgentSkill()
    skill.id = SkillId.WEB_SEARCH
    skill.name = "Web Search"
    skill.description = "Search the web for current information"
    skill.tags.extend(["search", "web"])
    card.skills.append(skill)

    return card

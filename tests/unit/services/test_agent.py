from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_playground.models.messages import AssistantMessage, LLMMessage, SystemMessage, ToolMessage, UserMessage
from agent_playground.services.agent import Agent


def _make_agent(max_context_tokens: int = 100_000) -> Agent:
    return Agent(llm_client=MagicMock(), tool_providers=[], max_context_tokens=max_context_tokens)


def _user(text: str) -> UserMessage:
    return UserMessage(role="user", content=text)


def _assistant(text: str) -> AssistantMessage:
    return AssistantMessage(role="assistant", content=text)


class TestEstimateTokens:
    def test_empty_list_returns_zero(self) -> None:
        assert Agent._estimate_tokens([]) == 0

    def test_positive_for_non_empty_messages(self) -> None:
        msgs: list[LLMMessage] = [_user("hello world")]
        assert Agent._estimate_tokens(msgs) > 0

    def test_longer_message_costs_more_tokens(self) -> None:
        short: list[LLMMessage] = [_user("hi")]
        long: list[LLMMessage] = [_user("hi " * 500)]
        assert Agent._estimate_tokens(long) > Agent._estimate_tokens(short)


class TestTrimHistory:
    def test_short_history_passes_through_unchanged(self) -> None:
        agent: Agent = _make_agent(max_context_tokens=100_000)
        history: list[LLMMessage] = [_user("q1"), _assistant("a1"), _user("q2"), _assistant("a2")]
        result: list[LLMMessage] = agent._trim_history(history, reserved_tokens=100)
        assert result == history

    def test_newest_messages_kept_when_over_budget(self) -> None:
        agent: Agent = _make_agent(max_context_tokens=100_000)
        # Build a history large enough to exceed any small budget
        big_history: list[LLMMessage] = [_user("old message " * 200), _assistant("old reply " * 200)]
        new_pair: list[LLMMessage] = [_user("recent question"), _assistant("recent answer")]
        history: list[LLMMessage] = big_history + new_pair

        # Reserve almost the entire budget so only the new pair can fit
        total_estimated: int = Agent._estimate_tokens(history)
        tight_budget: int = int(agent._max_context_tokens * 0.85)
        reserved: int = tight_budget - Agent._estimate_tokens(new_pair) - 10

        result: list[LLMMessage] = agent._trim_history(history, reserved_tokens=reserved)

        assert new_pair[0] in result
        assert new_pair[1] in result
        assert big_history[0] not in result

    def test_empty_history_returns_empty(self) -> None:
        agent: Agent = _make_agent(max_context_tokens=100_000)
        assert agent._trim_history([], reserved_tokens=100) == []

    def test_budget_exhausted_returns_empty(self) -> None:
        agent: Agent = _make_agent(max_context_tokens=100)
        history: list[LLMMessage] = [_user("some message")]
        # reserved_tokens equal to or above budget means nothing fits
        result: list[LLMMessage] = agent._trim_history(history, reserved_tokens=90)
        assert result == []

    def test_chronological_order_preserved(self) -> None:
        agent: Agent = _make_agent(max_context_tokens=100_000)
        history: list[LLMMessage] = [_user("first"), _assistant("second"), _user("third")]
        result: list[LLMMessage] = agent._trim_history(history, reserved_tokens=0)
        assert result == history


class TestBuildInitialMessages:
    def test_always_starts_with_system_message(self) -> None:
        agent: Agent = _make_agent()
        messages: list[LLMMessage] = agent._build_initial_messages("hello")
        assert isinstance(messages[0], SystemMessage)

    def test_always_ends_with_user_message(self) -> None:
        agent: Agent = _make_agent()
        messages: list[LLMMessage] = agent._build_initial_messages("hello")
        assert isinstance(messages[-1], UserMessage)
        assert messages[-1].content == "hello"

    def test_history_inserted_between_system_and_user(self) -> None:
        agent: Agent = _make_agent()
        history: list[LLMMessage] = [_user("prev q"), _assistant("prev a")]
        messages: list[LLMMessage] = agent._build_initial_messages("new q", history=history)
        assert isinstance(messages[0], SystemMessage)
        assert messages[1] == history[0]
        assert messages[2] == history[1]
        assert isinstance(messages[3], UserMessage)

    def test_system_and_user_present_when_history_trimmed_away(self) -> None:
        # Tiny budget so all history is dropped
        agent: Agent = _make_agent(max_context_tokens=100)
        history: list[LLMMessage] = [_user("old " * 500)]
        messages: list[LLMMessage] = agent._build_initial_messages("new question", history=history)
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[-1], UserMessage)
        assert messages[-1].content == "new question"

"""Slack integration for approval workflows."""

from cite_before_act.slack.client import SlackClient
from cite_before_act.slack.handlers import SlackHandler

__all__ = ["SlackClient", "SlackHandler"]


class AgentLearnError(Exception):
    """Base project error."""


class DocumentParsingError(AgentLearnError):
    """Raised when a document cannot be parsed."""


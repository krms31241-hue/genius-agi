class GeniusError(Exception):
    pass

class ClassificationError(GeniusError):
    pass

class ProviderSelectionError(GeniusError):
    pass

class EvaluationError(GeniusError):
    pass

class ConversationError(GeniusError):
    pass

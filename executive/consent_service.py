from executive.user_consent import UserConsentManager


class ConsentService:
    """
    High-level interface between the UI and the resource system.
    """

    def __init__(self):
        self.manager = UserConsentManager()

    def needs_consent(self):
        return not self.manager.accepted()

    def get_settings(self):
        return self.manager.load()

    def approve(self, mode="balanced"):
        self.manager.accept(mode)

    def reject(self):
        self.manager.revoke()

    def set_custom(self, cpu, memory, disk):
        self.manager.set_custom_limits(cpu, memory, disk)
        self.manager.accept("custom")

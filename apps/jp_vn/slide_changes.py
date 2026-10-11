"""Ignore local pointer motion, refresh minor content changes at a bounded rate."""
class SlideChangeTracker:
    def __init__(self):
        self.reference = None
        self.stable_since = 0
        self.last_scan = None

    def observe(self, signature, now):
        broad = self.reference is None or len(signature) != len(self.reference)
        if not broad:
            broad = sum(a != b for a, b in zip(signature, self.reference)) / max(1, len(signature)) > .035
        if broad:
            self.reference = signature
            self.stable_since = now
            self.last_scan = None
            return 'changed'
        if now - self.stable_since < 1:
            return 'wait'
        # Periodic refresh catches incremental text reveals even with a moving pointer.
        # It never clears valid slide context while OCR runs.
        if self.last_scan is None or now - self.last_scan >= 15:
            return 'scan'
        return 'wait'

    def scanned(self, now):
        self.last_scan = now

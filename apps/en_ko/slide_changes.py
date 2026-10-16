"""Ignore pointer motion; bound settling time so video never starves capture."""
class SlideChangeTracker:
    def __init__(self,max_settle=3.0):
        self.reference=None;self.stable_since=0;self.last_scan=None
        self.change_started=None;self.max_settle=max_settle;self.scan_reason='initial'
    def observe(self,signature,now):
        broad=self.reference is None or len(signature)!=len(self.reference)
        if not broad:broad=sum(a!=b for a,b in zip(signature,self.reference))/max(1,len(signature))>.035
        if broad:
            self.reference=signature;self.stable_since=now
            if self.change_started is None:self.change_started=now
            if now-self.change_started>=self.max_settle:
                self.scan_reason='motion';return 'scan'
            return 'changed'
        if now-self.stable_since<1:
            if self.change_started is not None and now-self.change_started>=self.max_settle:
                self.scan_reason='motion';return 'scan'
            return 'wait'
        if self.change_started is not None or self.last_scan is None:
            self.scan_reason='stable';return 'scan'
        if now-self.last_scan>=15:
            self.scan_reason='periodic';return 'scan'
        return 'wait'
    def scanned(self,now):
        self.last_scan=now;self.change_started=None

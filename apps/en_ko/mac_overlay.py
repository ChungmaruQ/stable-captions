"""Mac-only native window policy for the app's click-through caption overlay."""
import sys

def native_window(widget):
    import objc,ctypes
    view=objc.objc_object(c_void_p=ctypes.c_void_p(int(widget.winId())))
    return view.window()

def enforce(widget):
    if sys.platform!='darwin' or not widget.isVisible():return
    import AppKit
    try:
        window=native_window(widget)
        if window is None:return
        # Join other apps' fullscreen Spaces without turning the control panel
        # into an accessory app or stealing keyboard focus.
        behavior=int(window.collectionBehavior())
        remove=(AppKit.NSWindowCollectionBehaviorMoveToActiveSpace |
                AppKit.NSWindowCollectionBehaviorFullScreenPrimary |
                AppKit.NSWindowCollectionBehaviorFullScreenNone |
                getattr(AppKit,'NSWindowCollectionBehaviorPrimary',0) |
                getattr(AppKit,'NSWindowCollectionBehaviorAuxiliary',0))
        behavior=(behavior & ~remove) | AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary | getattr(AppKit,'NSWindowCollectionBehaviorCanJoinAllApplications',0)
        window.setCollectionBehavior_(behavior)
        window.setLevel_(AppKit.NSStatusWindowLevel)
        window.setHidesOnDeactivate_(False)
        window.setCanHide_(False)
        window.setIgnoresMouseEvents_(True)
        window.orderFrontRegardless()
        widget.mac_topmost_error=''
    except Exception as exc:
        widget.mac_topmost_error=type(exc).__name__

def install(widget):
    if sys.platform!='darwin':return
    from PySide6.QtCore import QTimer
    widget.mac_topmost_error=''
    timer=QTimer(widget);timer.timeout.connect(lambda:enforce(widget));timer.start(500)
    widget.mac_topmost_timer=timer

def state(widget):
    if sys.platform!='darwin':return {}
    window=native_window(widget)
    return {'level':int(window.level()),'collection_behavior':int(window.collectionBehavior()),'click_through':bool(window.ignoresMouseEvents()),'hides_on_deactivate':bool(window.hidesOnDeactivate()),'error':getattr(widget,'mac_topmost_error','')}

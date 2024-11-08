import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

class CameraTest:
    def __init__(self):
        Gst.init(None)
        
        # Enable debug output
        Gst.debug_set_active(True)
        Gst.debug_set_default_threshold(4)
        
        # Create pipeline using v4l2src with IPU3 format
        pipeline_str = (
            'v4l2src device=/dev/video1 io-mode=mmap ! '
            'v4l2convert ! '
            'video/x-raw,format=RGB,width=640,height=480 ! '
            'videoconvert ! '
            'autovideosink'
        )
        
        print(f"Creating pipeline: {pipeline_str}")
        
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect('message::error', self.on_error)
            self.bus.connect('message::state-changed', self.on_state_changed)
            
        except GLib.Error as e:
            print(f"Error creating pipeline: {e}")
            sys.exit(1)
    
    def start(self):
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Unable to set the pipeline to the playing state")
            sys.exit(1)
    
    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)
    
    def on_error(self, bus, message):
        err, debug = message.parse_error()
        print(f"Error: {err.message}")
        print(f"Debug info: {debug}")
        self.stop()
    
    def on_state_changed(self, bus, message):
        old, new, pending = message.parse_state_changed()
        print(f"Pipeline state changed from {old.value_nick} to {new.value_nick}")

if __name__ == "__main__":
    camera = CameraTest()
    camera.start()
    
    try:
        loop = GLib.MainLoop()
        loop.run()
    except KeyboardInterrupt:
        camera.stop()
        print("\nInterrupted by user")
    finally:
        if camera:
            camera.stop()

if __name__ == '__main__':
    main() 
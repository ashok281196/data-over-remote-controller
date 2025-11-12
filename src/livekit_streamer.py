"""
LiveKit Streaming Module
Handles video streaming to LiveKit servers with telemetry data overlay.
"""

import asyncio
import logging
import numpy as np
import cv2
from typing import Optional, Dict
from livekit import rtc
import json

logger = logging.getLogger(__name__)


class LiveKitStreamer:
    """
    LiveKit video streamer with telemetry support.
    Streams camera frames to LiveKit room and publishes telemetry as data channel.
    """
    
    def __init__(self, config: dict):
        """
        Initialize LiveKit streamer.
        
        Args:
            config: LiveKit configuration dictionary
        """
        self.config = config
        self.url = config.get('url', 'ws://localhost:7880')
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.room_name = config.get('room_name', 'jetson-stream')
        self.participant_name = config.get('participant_name', 'jetson-device')
        
        # LiveKit objects
        self.room = None
        self.video_source = None
        self.video_track = None
        
        # State
        self.connected = False
        self.streaming = False
        
        # Video settings
        self.video_bitrate = config.get('video_bitrate', 2000000)  # 2 Mbps
        self.frame_width = 0
        self.frame_height = 0
        
        logger.info(f"LiveKit streamer initialized for room: {self.room_name}")
    
    async def connect(self) -> bool:
        """
        Connect to LiveKit room.
        
        Returns:
            True if connected successfully
        """
        try:
            # Create room instance
            self.room = rtc.Room()
            
            # Set up event handlers
            @self.room.on("participant_connected")
            def on_participant_connected(participant: rtc.RemoteParticipant):
                logger.info(f"Participant connected: {participant.identity}")
            
            @self.room.on("participant_disconnected")
            def on_participant_disconnected(participant: rtc.RemoteParticipant):
                logger.info(f"Participant disconnected: {participant.identity}")
            
            @self.room.on("track_subscribed")
            def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication,
                                   participant: rtc.RemoteParticipant):
                logger.info(f"Track subscribed: {track.sid}")
            
            # Generate access token
            from livekit.api import AccessToken, VideoGrants
            
            token = AccessToken(self.api_key, self.api_secret)
            token.with_identity(self.participant_name)
            token.with_name(self.participant_name)
            token.with_grants(VideoGrants(
                room_join=True,
                room=self.room_name,
                can_publish=True,
                can_subscribe=True
            ))
            
            jwt_token = token.to_jwt()
            
            # Connect to room
            logger.info(f"Connecting to LiveKit room: {self.room_name}")
            await self.room.connect(self.url, jwt_token)
            
            self.connected = True
            logger.info("Successfully connected to LiveKit room")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to LiveKit: {e}")
            return False
    
    async def start_streaming(self, width: int = 1920, height: int = 1080, fps: int = 30) -> bool:
        """
        Start video streaming.
        
        Args:
            width: Video width
            height: Video height
            fps: Frames per second
            
        Returns:
            True if streaming started successfully
        """
        if not self.connected:
            logger.error("Not connected to LiveKit room")
            return False
        
        try:
            self.frame_width = width
            self.frame_height = height
            
            # Create video source
            self.video_source = rtc.VideoSource(width, height)
            
            # Create video track
            self.video_track = rtc.LocalVideoTrack.create_video_track(
                "camera",
                self.video_source
            )
            
            # Publish video track
            options = rtc.TrackPublishOptions()
            options.video_encoding = rtc.VideoEncoding(
                max_bitrate=self.video_bitrate,
                max_framerate=fps
            )
            
            await self.room.local_participant.publish_track(self.video_track, options)
            
            self.streaming = True
            logger.info(f"Started LiveKit streaming: {width}x{height} @ {fps}fps")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            return False
    
    async def send_frame(self, frame: np.ndarray) -> bool:
        """
        Send video frame to LiveKit.
        
        Args:
            frame: Video frame (numpy array in BGR format)
            
        Returns:
            True if frame sent successfully
        """
        if not self.streaming or not self.video_source:
            return False
        
        try:
            # Convert BGR to RGB (OpenCV uses BGR, LiveKit expects RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize if necessary
            if frame.shape[1] != self.frame_width or frame.shape[0] != self.frame_height:
                frame_rgb = cv2.resize(frame_rgb, (self.frame_width, self.frame_height))
            
            # Create VideoFrame
            video_frame = rtc.VideoFrame(
                width=self.frame_width,
                height=self.frame_height,
                type=rtc.VideoBufferType.RGBA,
                data=frame_rgb.tobytes()
            )
            
            # Capture frame to video source
            self.video_source.capture_frame(video_frame)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending frame: {e}")
            return False
    
    async def send_telemetry(self, telemetry_data: Dict) -> bool:
        """
        Send telemetry data via data channel.
        
        Args:
            telemetry_data: Dictionary with telemetry information
            
        Returns:
            True if sent successfully
        """
        if not self.connected:
            return False
        
        try:
            # Serialize telemetry data
            data_str = json.dumps(telemetry_data)
            data_bytes = data_str.encode('utf-8')
            
            # Publish data via data channel
            await self.room.local_participant.publish_data(
                data_bytes,
                kind=rtc.DataPacketKind.RELIABLE,
                topic="telemetry"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending telemetry: {e}")
            return False
    
    async def stop_streaming(self):
        """Stop video streaming."""
        if self.streaming:
            logger.info("Stopping LiveKit streaming")
            self.streaming = False
            
            if self.video_track and self.room:
                await self.room.local_participant.unpublish_track(self.video_track.sid)
            
            self.video_track = None
            self.video_source = None
    
    async def disconnect(self):
        """Disconnect from LiveKit room."""
        if self.streaming:
            await self.stop_streaming()
        
        if self.connected and self.room:
            logger.info("Disconnecting from LiveKit")
            await self.room.disconnect()
            self.connected = False
            self.room = None
            logger.info("Disconnected from LiveKit")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class LiveKitStreamManager:
    """
    Manager class to handle LiveKit streaming in a background task.
    Provides synchronous interface for async LiveKit operations.
    """
    
    def __init__(self, config: dict):
        """
        Initialize stream manager.
        
        Args:
            config: LiveKit configuration
        """
        self.config = config
        self.streamer = None
        self.loop = None
        self.running = False
        self.task = None
        
    def start(self) -> bool:
        """
        Start the stream manager.
        
        Returns:
            True if started successfully
        """
        try:
            # Create new event loop for background task
            self.loop = asyncio.new_event_loop()
            self.streamer = LiveKitStreamer(self.config)
            
            # Run connection in loop
            self.running = True
            
            async def run_streamer():
                await self.streamer.connect()
                while self.running:
                    await asyncio.sleep(0.1)
                await self.streamer.disconnect()
            
            # Start event loop in background thread
            import threading
            
            def run_loop():
                asyncio.set_event_loop(self.loop)
                self.loop.run_until_complete(run_streamer())
            
            thread = threading.Thread(target=run_loop, daemon=True)
            thread.start()
            
            # Wait for connection
            import time
            timeout = 5.0
            start_time = time.time()
            while not self.streamer.connected and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if self.streamer.connected:
                logger.info("LiveKit stream manager started")
                return True
            else:
                logger.error("Failed to connect within timeout")
                return False
                
        except Exception as e:
            logger.error(f"Error starting stream manager: {e}")
            return False
    
    def send_frame(self, frame: np.ndarray) -> bool:
        """
        Send video frame (synchronous wrapper).
        
        Args:
            frame: Video frame
            
        Returns:
            True if sent successfully
        """
        if not self.loop or not self.streamer:
            return False
        
        try:
            asyncio.run_coroutine_threadsafe(
                self.streamer.send_frame(frame),
                self.loop
            )
            return True
        except Exception as e:
            logger.error(f"Error sending frame: {e}")
            return False
    
    def send_telemetry(self, telemetry_data: Dict) -> bool:
        """
        Send telemetry data (synchronous wrapper).
        
        Args:
            telemetry_data: Telemetry dictionary
            
        Returns:
            True if sent successfully
        """
        if not self.loop or not self.streamer:
            return False
        
        try:
            asyncio.run_coroutine_threadsafe(
                self.streamer.send_telemetry(telemetry_data),
                self.loop
            )
            return True
        except Exception as e:
            logger.error(f"Error sending telemetry: {e}")
            return False
    
    def stop(self):
        """Stop the stream manager."""
        logger.info("Stopping LiveKit stream manager")
        self.running = False
        
        if self.loop:
            self.loop.stop()
        
        logger.info("LiveKit stream manager stopped")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test configuration
    test_config = {
        'url': 'ws://localhost:7880',
        'api_key': 'test-api-key',
        'api_secret': 'test-api-secret',
        'room_name': 'test-room',
        'participant_name': 'test-jetson'
    }
    
    # Test async streaming
    async def test_streaming():
        async with LiveKitStreamer(test_config) as streamer:
            logger.info("Testing LiveKit streaming...")
            
            # Start streaming
            await streamer.start_streaming(1280, 720, 30)
            
            # Send test frames
            for i in range(10):
                # Create test frame
                frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
                await streamer.send_frame(frame)
                
                # Send telemetry
                await streamer.send_telemetry({
                    'frame_number': i,
                    'timestamp': i * 0.033
                })
                
                await asyncio.sleep(0.033)  # ~30 fps
            
            logger.info("Test completed")
    
    # Run test
    # asyncio.run(test_streaming())
    logger.info("LiveKit streamer module loaded")

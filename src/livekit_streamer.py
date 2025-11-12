"""
LiveKit streaming module for video and telemetry data.
"""

import asyncio
import logging
import numpy as np
import cv2
from typing import Optional
from livekit import rtc, api
from livekit.plugins import opencv

logger = logging.getLogger(__name__)


class LiveKitStreamer:
    """LiveKit video and telemetry streamer."""
    
    def __init__(self, url: str, api_key: str, api_secret: str, 
                 room_name: str, participant_name: str = "jetson-camera"):
        """
        Initialize LiveKit streamer.
        
        Args:
            url: LiveKit server URL
            api_key: LiveKit API key
            api_secret: LiveKit API secret
            room_name: Room name to join
            participant_name: Participant name
        """
        self.url = url
        self.api_key = api_key
        self.api_secret = api_secret
        self.room_name = room_name
        self.participant_name = participant_name
        
        self.room: Optional[rtc.Room] = None
        self.video_track: Optional[rtc.VideoTrack] = None
        self.audio_track: Optional[rtc.AudioTrack] = None
        self.connected = False
        
    async def connect(self) -> bool:
        """Connect to LiveKit room."""
        try:
            token = api.AccessToken(self.api_key, self.api_secret) \
                .with_identity(self.participant_name) \
                .with_name(self.participant_name) \
                .with_grants(api.VideoGrants(
                    room_join=True,
                    room=self.room_name,
                    can_publish=True,
                    can_subscribe=True
                )).to_jwt()
            
            self.room = rtc.Room()
            
            # Set up event handlers
            @self.room.on("participant_connected")
            def on_participant_connected(participant: rtc.RemoteParticipant):
                logger.info(f"Participant connected: {participant.identity}")
            
            @self.room.on("participant_disconnected")
            def on_participant_disconnected(participant: rtc.RemoteParticipant):
                logger.info(f"Participant disconnected: {participant.identity}")
            
            @self.room.on("track_published")
            def on_track_published(
                publication: rtc.RemoteTrackPublication,
                participant: rtc.RemoteParticipant
            ):
                logger.info(f"Track published: {publication.kind}")
            
            # Connect to room
            await self.room.connect(self.url, token)
            self.connected = True
            logger.info(f"Connected to LiveKit room: {self.room_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to LiveKit: {e}")
            return False
    
    def create_video_track(self, width: int = 1920, height: int = 1080, fps: int = 30):
        """Create video track for streaming."""
        try:
            source = rtc.VideoSource(width, height)
            self.video_track = rtc.LocalVideoTrack.create_video_track(
                "camera", source
            )
            
            # Publish video track
            if self.room:
                options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_CAMERA)
                self.room.local_participant.publish_track(
                    self.video_track, options
                )
                logger.info("Video track published to LiveKit")
            
            return source
        except Exception as e:
            logger.error(f"Error creating video track: {e}")
            return None
    
    def send_frame(self, frame: np.ndarray, source: Optional[rtc.VideoSource] = None):
        """Send video frame to LiveKit."""
        if not self.connected or not source:
            return
        
        try:
            # Convert numpy array to LiveKit video frame
            # OpenCV frame is BGR, LiveKit expects RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to bytes
            frame_bytes = frame_rgb.tobytes()
            
            # Create video frame
            video_frame = rtc.VideoFrame(
                width=frame.shape[1],
                height=frame.shape[0],
                data=frame_bytes,
                rotation=0
            )
            
            # Send frame
            source.capture_frame(video_frame)
            
        except Exception as e:
            logger.error(f"Error sending frame: {e}")
    
    async def send_telemetry(self, telemetry_data: dict):
        """Send telemetry data as data channel message."""
        if not self.connected or not self.room:
            return
        
        try:
            # Create data channel if not exists
            if not hasattr(self, 'data_channel'):
                self.data_channel = await self.room.local_participant.create_data_channel(
                    "telemetry"
                )
            
            # Send telemetry as JSON
            import json
            message = json.dumps(telemetry_data)
            self.data_channel.send(message.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error sending telemetry: {e}")
    
    async def disconnect(self):
        """Disconnect from LiveKit room."""
        if self.room:
            await self.room.disconnect()
            self.connected = False
            logger.info("Disconnected from LiveKit room")
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

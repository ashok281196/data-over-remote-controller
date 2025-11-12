// WebSocket connection
const socket = io();

// State
let lastUpdateTime = Date.now();

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Jetson Camera Stream Monitor...');
    setupSocketHandlers();
    startHeartbeat();
});

// Setup WebSocket event handlers
function setupSocketHandlers() {
    socket.on('connect', function() {
        console.log('Connected to server');
        updateStatus('Connected', true);
    });

    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        updateStatus('Disconnected', false);
    });

    socket.on('status', function(data) {
        console.log('Status:', data);
    });

    socket.on('telemetry_update', function(data) {
        console.log('Telemetry update:', data);
        updateTelemetry(data);
    });
}

// Update connection status
function updateStatus(text, connected) {
    const statusText = document.getElementById('statusText');
    const statusDot = document.getElementById('statusDot');
    
    statusText.textContent = text;
    
    if (connected) {
        statusDot.classList.remove('disconnected');
    } else {
        statusDot.classList.add('disconnected');
    }
}

// Update telemetry data
function updateTelemetry(data) {
    lastUpdateTime = Date.now();
    
    // Update CPU usage
    if (data.cpu_usage_percent !== undefined) {
        document.getElementById('cpuUsage').textContent = data.cpu_usage_percent.toFixed(1);
        document.getElementById('cpuProgress').style.width = data.cpu_usage_percent + '%';
    }
    
    // Update Memory usage
    if (data.memory_percent !== undefined) {
        document.getElementById('memoryUsage').textContent = data.memory_percent.toFixed(1);
        document.getElementById('memoryProgress').style.width = data.memory_percent + '%';
        
        if (data.memory_used_mb && data.memory_total_mb) {
            document.getElementById('memoryDetail').textContent = 
                `${data.memory_used_mb.toFixed(0)} MB / ${data.memory_total_mb.toFixed(0)} MB`;
        }
    }
    
    // Update GPU usage
    if (data.gpu_usage_percent !== undefined) {
        document.getElementById('gpuUsage').textContent = data.gpu_usage_percent.toFixed(1);
        document.getElementById('gpuProgress').style.width = data.gpu_usage_percent + '%';
    }
    
    // Update temperatures
    if (data.temperatures) {
        const tempList = document.getElementById('temperatureList');
        tempList.innerHTML = '';
        
        for (const [zone, temp] of Object.entries(data.temperatures)) {
            const tempItem = document.createElement('div');
            tempItem.className = 'temp-item';
            
            const zoneName = zone.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            tempItem.innerHTML = `
                <span>${zoneName}:</span>
                <span style="color: ${getTempColor(temp)}">${temp.toFixed(1)} °C</span>
            `;
            
            tempList.appendChild(tempItem);
        }
    }
    
    // Update network stats
    if (data.bytes_sent_mb !== undefined) {
        document.getElementById('bytesSent').textContent = data.bytes_sent_mb.toFixed(2) + ' MB';
    }
    if (data.bytes_recv_mb !== undefined) {
        document.getElementById('bytesRecv').textContent = data.bytes_recv_mb.toFixed(2) + ' MB';
    }
    
    // Update FPS counters
    if (data.camera_fps !== undefined) {
        document.getElementById('cameraFps').textContent = data.camera_fps.toFixed(1);
        document.getElementById('fpsCounter').textContent = `FPS: ${data.camera_fps.toFixed(1)}`;
    }
    if (data.stream_fps !== undefined) {
        document.getElementById('streamFps').textContent = data.stream_fps.toFixed(1);
    }
    
    // Update status indicators
    updateStatusIndicators(data);
    
    // Update last update time
    const now = new Date();
    document.getElementById('lastUpdate').textContent = now.toLocaleTimeString();
}

// Update status indicators
function updateStatusIndicators(data) {
    // SIYI status (placeholder - implement based on actual data)
    const siyiStatus = document.getElementById('siyiStatus');
    if (data.siyi_connected !== undefined) {
        siyiStatus.textContent = data.siyi_connected ? 'Connected' : 'Disconnected';
        siyiStatus.style.color = data.siyi_connected ? 'var(--accent-green)' : 'var(--accent-red)';
    } else {
        siyiStatus.textContent = 'Unknown';
        siyiStatus.style.color = 'var(--text-secondary)';
    }
    
    // LiveKit status (placeholder - implement based on actual data)
    const livekitStatus = document.getElementById('livekitStatus');
    if (data.livekit_connected !== undefined) {
        livekitStatus.textContent = data.livekit_connected ? 'Streaming' : 'Disconnected';
        livekitStatus.style.color = data.livekit_connected ? 'var(--accent-green)' : 'var(--accent-red)';
    } else {
        livekitStatus.textContent = 'Unknown';
        livekitStatus.style.color = 'var(--text-secondary)';
    }
}

// Get color based on temperature
function getTempColor(temp) {
    if (temp < 50) return 'var(--accent-green)';
    if (temp < 70) return 'var(--accent-orange)';
    return 'var(--accent-red)';
}

// Request telemetry updates
function startHeartbeat() {
    setInterval(function() {
        socket.emit('request_telemetry');
        
        // Check if we've lost connection (no updates for 5 seconds)
        if (Date.now() - lastUpdateTime > 5000) {
            console.warn('No telemetry updates received');
        }
    }, 1000); // Request every second
}

// Handle video feed errors
document.getElementById('videoFeed').onerror = function() {
    console.error('Video feed error');
};

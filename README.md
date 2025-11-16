# System Architecture - Drone vSLAM + Wi-Fi RSSI Fusion

## System Architecture Diagram (Mermaid)

```mermaid
flowchart TD
    Camera[📷 Camera - Monocular] --> VIO[VIO<br/>Pose + Map]
    Camera --> Depth[Depth Anything V3<br/>Depth Estimation]
    
    VIO -->| | Depth
    VIO -->|/slam/pose| Logger[Fusion Logger<br/>Collects Pose + Depth + RSSI]
    
    Depth -->|/depth/image<br/>/depth/cloud| Recon[3D Reconstruction Fusion<br/>Combines pose + depth]
    
    Recon -->|/reconstruction/points| Logger
    
    WiFi[📶 Wi-Fi Interface - wlan0] --> Monitor[wifi_monitor]
    Monitor -->|/wifi/rssi| Logger
    
    Logger -->|logs/fused_data_*.csv| Final[Final 3D Reconstruction<br/>Post-processing]
    Recon -->|reconstruction data| Final
    
    Final --> Output1[logs/final_reconstruction_*.ply]
    Final --> Output2[logs/wifi_heatmap_3d_*.json]
    Final --> Output3[logs/colored_pointcloud_*.ply]
    
    style Camera fill:#e1f5ff
    style SLAM fill:#ffe1e1
    style Depth fill:#e1ffe1
    style Recon fill:#fff5e1
    style WiFi fill:#e1f5ff
    style Monitor fill:#e1e1ff
    style Logger fill:#ffe1ff
    style Final fill:#ffb3ba
    style Output1 fill:#bae1ff
    style Output2 fill:#bae1ff
    style Output3 fill:#bae1ff
```

## Detailed Component Flow

```mermaid
graph LR
    subgraph Jetson Drone
        subgraph Input
            A[Camera] --> B[stella_vslam]
            A --> C[Depth Anything V3]
            D[Wi-Fi wlan0] --> E[wifi_monitor]
        end
        
        subgraph Processing
            B -->|pose| C
            B -->|pose| F[Fusion Logger]
            C -->|depth| G[3D Reconstruction<br/>Fusion]
            G -->|points| F
            E -->|rssi| F
        end
        
        subgraph Output
            F --> H[CSV Logs]
            G --> I[Point Clouds]
            H --> J[Final 3D<br/>Reconstruction]
            I --> J
            J --> K[PLY Files]
            J --> L[Heatmap JSON]
        end
    end
```

## Demo
![Demo - 3D reconstruction](demo.gif)

## Data Flow Sequence

```mermaid
sequenceDiagram
    participant C as Camera
    participant S as VIO
    participant D as Depth Anything V3
    participant R as 3D Recon Fusion
    participant W as wifi_monitor
    participant L as Fusion Logger
    participant F as Final 3D Recon
    
    C->>S: image frames
    C->>D: image frames
    S->>D: pose for alignment
    S->>L: pose data
    D->>R: depth point cloud
    S->>R: pose for transform
    R->>L: global points
    W->>L: RSSI readings
    
    Note over L: Time-sync all data
    L->>F: fused_data.csv
    R->>F: reconstruction.ply
    
    F->>F: Post-process
    F-->>C: final outputs
```

## Component Responsibilities

```mermaid
mindmap
  root((Drone System))
    VIO
      Camera pose estimation
      Sparse feature map
      Provides pose to Depth
      Sends pose to Logger
    Depth Anything V3
      Monocular depth estimation
      Generates depth maps
      Creates 3D point clouds
    3D Reconstruction Fusion
      Transform to world frame
      Accumulate points over time
      Publish global point cloud
    wifi_monitor
      Poll Wi-Fi RSSI
      Publish signal strength
    Fusion Logger
      Collect all data streams
      Time-synchronize data
      Write CSV logs
      Store point clouds
    Final 3D Reconstruction
      Post-process collected data
      Map RSSI to 3D coordinates
      Generate colored point clouds
      Create final outputs
```

## System States

```mermaid
stateDiagram-v2
    [*] --> Initialization
    Initialization --> Calibrating: Load models & configs
    Calibrating --> Ready: All systems OK
    
    Ready --> Running: Start flight
    Running --> Tracking: Camera & VIO active
    Tracking --> Mapping: Building 3D map
    Mapping --> Logging: Recording data
    
    Logging --> Tracking: Continue flight
    Logging --> Stopped: End flight
    
    Stopped --> Processing: Post-processing
    Processing --> Complete: Generate outputs
    Complete --> [*]
    
    Tracking --> Lost: Tracking failure
    Lost --> Recovering: Re-initialize
    Recovering --> Tracking: Success
    Recovering --> Error: Failed
    Error --> [*]
```



## Performance Pipeline

```mermaid
gantt
    title Processing Timeline (per frame)
    dateFormat X
    axisFormat %L ms
    
    section Camera
    Image Capture: 0, 33ms
    
    section VIO
    Feature Extract: 5, 20ms
    Pose Estimate: 25, 15ms
    
    section Depth V3
    Depth Inference: 10, 80ms
    Point Cloud Gen: 90, 10ms
    
    section 3D Fusion
    Transform Points: 100, 5ms
    Accumulate: 105, 5ms
    
    section Logging
    Write Data: 110, 5ms
```

---

## How to Use These Diagrams

### On GitHub
1. Copy the entire markdown file to your repository
2. GitHub will automatically render the Mermaid diagrams
3. They will look clean and professional

### Alternative: Generate Images
```bash
# Install mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# Generate PNG images
mmdc -i SYSTEM_ARCHITECTURE_MERMAID.md -o architecture.png
```

### In Documentation
- Use the Mermaid code blocks directly in README.md
- GitHub, GitLab, and many other platforms support Mermaid natively
- VS Code has Mermaid preview extensions

---

## Advantages of Mermaid Diagrams

✅ **Renders properly** on GitHub/GitLab  
✅ **Version controllable** - plain text, easy to diff  
✅ **Easy to update** - just edit the text  
✅ **Multiple diagram types** - flowcharts, sequences, state diagrams  
✅ **Professional looking** - consistent styling  
✅ **Exportable** - can convert to PNG/SVG/PDF  

---

## Original ASCII Diagram (For Reference)

The ASCII art diagram you saw uses box-drawing characters which don't render well in most markdown viewers. Instead, use the Mermaid diagrams above for clean, professional visualization.

# Visual SLAM Implementation in MATLAB

## Overview

This is a complete feature-based Visual SLAM (Simultaneous Localization and Mapping) system implementation in MATLAB. The system is capable of:
- Building 3D maps from monocular camera image sequences
- Real-time tracking of camera position and pose
- Loop closure detection and drift correction
- Visualization of camera trajectory and 3D map points

## System Requirements

- MATLAB R2019b or higher
- Computer Vision Toolbox
- Image Processing Toolbox

## File Description

### Core Files
- **VisualSLAM.m** - Main Visual SLAM class containing the complete SLAM pipeline
- **example_visual_slam.m** - Basic example script demonstrating usage with synthetic data
- **example_real_data.m** - Real data example supporting image sequences, video, or camera input

## Features

### 1. Map Initialization
- Initialize 3D map using first two frames
- SURF feature detection and matching
- Essential matrix estimation
- Triangulation for 3D point reconstruction

### 2. Feature Tracking
- Track known map points in new frames
- Camera pose estimation using PnP algorithm
- RANSAC robust estimation

### 3. Local Mapping
- Keyframe selection strategy
- Creation of new 3D points
- Local bundle adjustment optimization
- Covisibility graph maintenance

### 4. Loop Detection
- Feature-based loop closure detection
- Similarity computation with historical keyframes
- Automatic loop candidate identification

### 5. Drift Correction
- Pose graph optimization
- Distributed application of loop closure constraints
- Global consistency optimization

## Usage

### Quick Start

```matlab
% 1. Define camera parameters
focalLength = [800, 800];
principalPoint = [320, 240];
imageSize = [480, 640];
intrinsics = cameraIntrinsics(focalLength, principalPoint, imageSize);

% 2. Create Visual SLAM object
vslam = VisualSLAM(intrinsics);

% 3. Initialize map
success = vslam.initializeMap(image1, image2);

% 4. Process subsequent frames
for i = 3:numImages
    % Track features
    [pose, numMatches] = vslam.trackFrame(images{i});
    
    % Check if keyframe
    if vslam.checkKeyFrame(images{i})
        vslam.addKeyFrame(images{i});
        
        % Detect loop closure
        loopCandidates = vslam.detectLoop(vslam.KeyFrameCount);
        
        % Correct drift
        if ~isempty(loopCandidates)
            vslam.correctDrift(vslam.KeyFrameCount, loopCandidates(1));
        end
    end
end

% 5. Visualize results
vslam.visualizeMap();
trajectory = vslam.getTrajectory();
```

### Detailed Examples

#### Example 1: Using Synthetic Data

```matlab
% Run basic example
example_visual_slam
```

This script will:
1. Generate synthetic 3D scene and camera trajectory
2. Create simulated image sequence
3. Run complete Visual SLAM pipeline
4. Display 3D map and trajectory

#### Example 2: Using Real Image Sequences

```matlab
% Modify image folder path in example_real_data.m
imageFolder = 'path/to/your/images';

% Run script
example_real_data
```

#### Example 3: Real-time Camera Processing

```matlab
% Set in example_real_data.m
dataSource = 2;  % Use camera

% Run script
example_real_data
```

## Parameter Configuration

The Visual SLAM object supports the following configurable parameters:

```matlab
vslam = VisualSLAM(intrinsics, ...
    'MinFeatures', 100, ...           % Minimum features required for tracking
    'MaxReprojError', 4.0, ...        % Maximum reprojection error (pixels)
    'MinParallax', 1.0, ...           % Minimum parallax angle (degrees)
    'KeyFrameThreshold', 0.7, ...     % Keyframe selection threshold
    'LoopScoreThreshold', 0.75);      % Loop detection threshold
```

### Parameter Descriptions

- **MinFeatures**: Minimum number of feature points required for successful tracking
- **MaxReprojError**: Maximum reprojection error allowed in RANSAC
- **MinParallax**: Minimum parallax angle for triangulation
- **KeyFrameThreshold**: Create new keyframe when feature matching rate falls below this value
- **LoopScoreThreshold**: Detect loop closure when feature matching score exceeds this value

## API Reference

### VisualSLAM Class

#### Constructor
```matlab
obj = VisualSLAM(cameraParams, varargin)
```

#### Main Methods

**initializeMap(image1, image2)**
- Initialize map using first two frames
- Returns: success (boolean)

**trackFrame(image)**
- Track features in new frame
- Returns: [pose, numMatches]
  - pose: 4x4 camera pose matrix
  - numMatches: Number of matched features

**checkKeyFrame(image)**
- Check if current frame should become a keyframe
- Returns: isKeyFrame (boolean)

**addKeyFrame(image)**
- Add new keyframe and update local map

**detectLoop(kfID)**
- Detect loop closure candidates
- Returns: loopCandidates (array of keyframe IDs)

**correctDrift(currentKFID, loopKFID)**
- Correct drift using loop closure constraints

**getTrajectory()**
- Get camera trajectory
- Returns: Nx3 matrix (camera positions)

**visualizeMap()**
- Visualize 3D map and camera trajectory

### Properties

- **MapPoints**: Nx3 matrix containing all 3D map points
- **KeyFrames**: Keyframe structure array
- **CovisibilityGraph**: Covisibility graph adjacency matrix
- **CurrentPose**: Current camera pose (4x4 matrix)

## Typical Workflow

```
1. Map Initialization
   ├─ Detect SURF features
   ├─ Feature matching
   ├─ Estimate essential matrix
   ├─ Recover relative pose
   └─ Triangulate 3D points

2. For each frame:
   ├─ Feature tracking
   │  ├─ Detect features
   │  ├─ Match with map points
   │  └─ PnP pose estimation
   │
   ├─ Keyframe decision
   │  └─ If keyframe:
   │     ├─ Add keyframe
   │     ├─ Update covisibility graph
   │     ├─ Local bundle adjustment
   │     └─ Loop detection
   │        └─ If loop detected:
   │           └─ Pose graph optimization
   └─ Continue to next frame
```

## Visualization Output

The system provides multiple visualization options:

1. **3D Map View**: Display 3D point cloud and camera trajectory
2. **Trajectory View**: Show camera motion from different angles
3. **Covisibility Graph**: Show connections between keyframes
4. **Statistics**: Display processing progress and performance metrics

## Performance Considerations

### Optimization Recommendations

1. **Image Resolution**: Lower resolution improves processing speed
2. **Feature Count**: Reducing MinFeatures improves robustness but decreases speed
3. **Keyframe Frequency**: Increasing KeyFrameThreshold reduces number of keyframes
4. **Loop Detection**: For long sequences, detect periodically rather than every frame

### Typical Performance

- 640x480 images: ~2-5 FPS (MATLAB)
- Memory usage: ~100-500 MB (depending on map size)
- Applicable scenarios: Indoor/outdoor navigation, AR applications

## Limitations and Known Issues

1. **Pure Rotation Motion**: System struggles with pure rotation, requires translational motion
2. **Lack of Texture**: Feature detection may fail in low-texture environments
3. **Fast Motion**: Excessive camera speed may cause tracking failure
4. **Illumination Changes**: Large illumination changes may affect feature matching

## Troubleshooting

### Issue: Map initialization fails
**Solution**:
- Ensure first two frames have sufficient parallax
- Check image quality and feature richness
- Adjust MinFeatures parameter

### Issue: Tracking frequently fails
**Solution**:
- Reduce camera motion speed
- Increase scene texture
- Adjust MaxReprojError parameter

### Issue: No loop closures detected
**Solution**:
- Lower LoopScoreThreshold
- Ensure similar viewpoint when revisiting same location
- Increase number of keyframes

## Extension Suggestions

This system can be extended to include:

1. **Stereo Vision**: Use binocular cameras to improve depth estimation
2. **IMU Fusion**: Integrate inertial measurement unit data
3. **Semantic Information**: Add object detection and recognition
4. **Dense Reconstruction**: Generate dense 3D models
5. **Deep Learning**: Use deep features to replace SURF

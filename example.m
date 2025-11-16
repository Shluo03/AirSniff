% Visual SLAM Example Script
% This script demonstrates how to use the VisualSLAM class
% to process a sequence of images and build a 3D map

%% Setup
clear; close all; clc;

fprintf('=== Visual SLAM Demo ===\n\n');

%% 1. Define Camera Parameters
% Example camera intrinsics (adjust to your camera)
focalLength = [800, 800];    % [fx, fy] in pixels
principalPoint = [320, 240];  % [cx, cy] in pixels
imageSize = [480, 640];       % [height, width]

intrinsics = cameraIntrinsics(focalLength, principalPoint, imageSize);

fprintf('Camera parameters set\n');
fprintf('  Focal length: [%.1f, %.1f]\n', focalLength);
fprintf('  Principal point: [%.1f, %.1f]\n', principalPoint);
fprintf('  Image size: [%d, %d]\n\n', imageSize);

%% 2. Create Visual SLAM Object
vslam = VisualSLAM(intrinsics, ...
    'MinFeatures', 100, ...
    'MaxReprojError', 4.0, ...
    'KeyFrameThreshold', 0.7);

fprintf('Visual SLAM object created\n\n');

%% 3. Option A: Use Sample Images (if available)
% This example assumes you have a sequence of images
% You can replace this with your own image sequence

% Example: Generate synthetic data or load real images
% For demonstration, we'll show how to load images

imageFolder = 'path/to/your/images';  % Change this to your image folder
imageFiles = dir(fullfile(imageFolder, '*.png'));  % or *.jpg

if isempty(imageFiles)
    fprintf('No images found. Creating synthetic example...\n\n');
    % Create synthetic images for demonstration
    useSyntheticData = true;
else
    fprintf('Found %d images in folder\n\n', length(imageFiles));
    useSyntheticData = false;
end

%% 3. Option B: Create Synthetic Data for Demonstration
if useSyntheticData
    fprintf('Generating synthetic camera motion and images...\n');
    
    % Generate camera trajectory (forward motion with small rotation)
    numFrames = 30;
    
    images = cell(numFrames, 1);
    cameraPoses = cell(numFrames, 1);
    
    for i = 1:numFrames
        % Create a feature-rich synthetic image
        img = uint8(zeros(imageSize(1), imageSize(2)));
        
        % Add checkerboard pattern (shifted based on frame)
        offset = (i-1) * 10;
        checkerSize = 40;
        checker = uint8(checkerboard(checkerSize, ...
            ceil(imageSize(1)/checkerSize), ...
            ceil(imageSize(2)/checkerSize)) * 200);
        
        % Crop and shift the checkerboard
        startY = max(1, offset);
        startX = max(1, offset);
        endY = min(size(checker, 1), imageSize(1) + offset);
        endX = min(size(checker, 2), imageSize(2) + offset);
        
        cropY = endY - startY + 1;
        cropX = endX - startX + 1;
        
        if cropY <= imageSize(1) && cropX <= imageSize(2)
            img(1:cropY, 1:cropX) = checker(startY:endY, startX:endX);
        else
            img = checker(1:imageSize(1), 1:imageSize(2));
        end
        
        % Add random circles (features)
        numCircles = 50;
        for j = 1:numCircles
            cx = randi([20, imageSize(2)-20]);
            cy = randi([20, imageSize(1)-20]);
            radius_circle = randi([5, 15]);
            
            % Draw filled circle
            [yy, xx] = meshgrid(1:imageSize(2), 1:imageSize(1));
            circle = ((xx - cy).^2 + (yy - cx).^2) <= radius_circle^2;
            img(circle) = uint8(255 - img(circle));
        end
        
        % Add random rectangles
        numRects = 30;
        for j = 1:numRects
            x1 = randi([1, imageSize(2)-30]);
            y1 = randi([1, imageSize(1)-30]);
            w = randi([10, 30]);
            h = randi([10, 30]);
            
            x2 = min(x1 + w, imageSize(2));
            y2 = min(y1 + h, imageSize(1));
            
            img(y1:y2, x1:x2) = img(y1:y2, x1:x2) + uint8(100);
        end
        
        % Add texture noise for better feature detection
        noise_pattern = uint8(rand(imageSize(1), imageSize(2)) * 60);
        img = img + noise_pattern;
        
        % Add some Gaussian blur for smoothness
        img = imgaussfilt(img, 1.0);
        
        % Add corner features using random lines
        numLines = 20;
        for j = 1:numLines
            x1 = randi([1, imageSize(2)]);
            y1 = randi([1, imageSize(1)]);
            x2 = randi([1, imageSize(2)]);
            y2 = randi([1, imageSize(1)]);
            
            % Draw line
            numPts = 100;
            xline = round(linspace(x1, x2, numPts));
            yline = round(linspace(y1, y2, numPts));
            
            for k = 1:numPts
                if xline(k) >= 1 && xline(k) <= imageSize(2) && ...
                   yline(k) >= 1 && yline(k) <= imageSize(1)
                    % Make line thicker
                    for dy = -2:2
                        for dx = -2:2
                            py = yline(k) + dy;
                            px = xline(k) + dx;
                            if py >= 1 && py <= imageSize(1) && ...
                               px >= 1 && px <= imageSize(2)
                                img(py, px) = 255;
                            end
                        end
                    end
                end
            end
        end
        
        images{i} = img;
        
        % Create corresponding camera pose (simple forward motion)
        pose = eye(4);
        pose(1:3, 4) = [0; 0; -(i-1)*0.1];  % Move forward
        cameraPoses{i} = pose;
    end
    
    fprintf('Generated %d synthetic images\n\n', numFrames);
end

%% 4. Initialize Map
fprintf('=== Map Initialization ===\n');

if useSyntheticData
    image1 = images{1};
    image2 = images{2};
else
    image1 = imread(fullfile(imageFolder, imageFiles(1).name));
    image2 = imread(fullfile(imageFolder, imageFiles(2).name));
end

success = vslam.initializeMap(image1, image2);

if ~success
    error('Map initialization failed');
end

fprintf('Map successfully initialized\n\n');

%% 5. Process Remaining Frames
fprintf('=== Processing Image Sequence ===\n');

startFrame = 3;
if useSyntheticData
    endFrame = numFrames;
else
    endFrame = min(length(imageFiles), 50);
end

numTracked = 0;
numKeyFrames = 2;  % Already have 2 from initialization

for i = startFrame:endFrame
    % Load image
    if useSyntheticData
        currentImage = images{i};
    else
        currentImage = imread(fullfile(imageFolder, imageFiles(i).name));
    end
    
    % Track features and estimate pose
    [pose, numMatches] = vslam.trackFrame(currentImage);
    
    if numMatches > 0
        numTracked = numTracked + 1;
    end
    
    % Check if this should be a key frame
    if vslam.checkKeyFrame(currentImage)
        vslam.addKeyFrame(currentImage);
        numKeyFrames = numKeyFrames + 1;
        
        % Detect loops
        loopCandidates = vslam.detectLoop(vslam.KeyFrameCount);
        
        % If loop detected, correct drift
        if ~isempty(loopCandidates)
            vslam.correctDrift(vslam.KeyFrameCount, loopCandidates(1));
        end
    end
    
    % Display progress
    if mod(i, 5) == 0
        fprintf('Processed frame %d/%d\n', i, endFrame);
    end
end

fprintf('\n=== Processing Complete ===\n');
fprintf('Total frames processed: %d\n', endFrame - startFrame + 1);
fprintf('Frames tracked: %d\n', numTracked);
fprintf('Key frames created: %d\n', numKeyFrames);
fprintf('Map points: %d\n\n', size(vslam.MapPoints, 1));

%% 6. Visualize Results
fprintf('=== Visualization ===\n');

% Visualize the 3D map and trajectory
vslam.visualizeMap();

% Plot trajectory in 2D (top view)
figure('Name', 'Camera Trajectory (Top View)');
trajectory = vslam.getTrajectory();
plot(trajectory(:, 1), trajectory(:, 2), 'b-o', 'LineWidth', 2, 'MarkerSize', 8);
grid on;
xlabel('X (m)');
ylabel('Y (m)');
title('Camera Trajectory - Top View');
axis equal;

% Display covisibility graph
if vslam.KeyFrameCount > 1
    figure('Name', 'Covisibility Graph');
    imagesc(vslam.CovisibilityGraph);
    colorbar;
    xlabel('Key Frame ID');
    ylabel('Key Frame ID');
    title('Covisibility Graph (Shared Map Points)');
    axis square;
end

fprintf('Visualization complete\n');

%% 7. Save Results (Optional)
saveResults = false;  % Set to true to save results

if saveResults
    fprintf('\n=== Saving Results ===\n');
    
    % Save map points
    mapPoints = vslam.MapPoints;
    save('vslam_map_points.mat', 'mapPoints');
    
    % Save trajectory
    trajectory = vslam.getTrajectory();
    save('vslam_trajectory.mat', 'trajectory');
    
    % Save key frame poses
    keyFramePoses = cell(vslam.KeyFrameCount, 1);
    for i = 1:vslam.KeyFrameCount
        keyFramePoses{i} = vslam.KeyFrames(i).Pose;
    end
    save('vslam_key_frame_poses.mat', 'keyFramePoses');
    
    fprintf('Results saved\n');
end

fprintf('\n=== Visual SLAM Demo Complete ===\n');
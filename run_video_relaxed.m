% Visual SLAM with Video - Relaxed Parameters
% For videos with fast motion or fewer features

clear; close all; clc;

fprintf('=== Visual SLAM with Video (Relaxed Mode) ===\n\n');

%% 1. Select Video File
fprintf('Please select a video file...\n');
[videoFile, videoPath] = uigetfile(...
    {'*.mp4;*.mov;*.avi;*.m4v', 'Video Files (*.mp4, *.mov, *.avi, *.m4v)'; ...
     '*.*', 'All Files'}, ...
    'Select Video File');

if videoFile == 0
    error('No video file selected');
end

videoFullPath = fullfile(videoPath, videoFile);
fprintf('Selected video: %s\n\n', videoFile);

%% 2. Read Video
fprintf('=== Reading Video ===\n');

try
    vidObj = VideoReader(videoFullPath);
catch ME
    error('Failed to read video: %s', ME.message);
end

fprintf('Video information:\n');
fprintf('  Duration: %.2f seconds\n', vidObj.Duration);
fprintf('  Frame rate: %.2f fps\n', vidObj.FrameRate);
fprintf('  Resolution: %d x %d\n', vidObj.Width, vidObj.Height);

%% 3. Extract Frames - EXTRACT MORE FREQUENTLY
fprintf('\n=== Extracting Frames ===\n');

% Extract MORE frames (every 3-5 frames instead of 10)
frameSkip = max(1, round(vidObj.FrameRate / 5));  % ~5 fps instead of 3
maxFrames = 80;  % More frames

fprintf('Frame extraction settings (RELAXED):\n');
fprintf('  Extracting every %d frames (~%.1f fps)\n', frameSkip, vidObj.FrameRate/frameSkip);
fprintf('  Maximum frames: %d\n\n', maxFrames);

images = {};
totalFrames = 0;

fprintf('Extracting frames...\n');

while hasFrame(vidObj) && length(images) < maxFrames
    frame = readFrame(vidObj);
    totalFrames = totalFrames + 1;
    
    if mod(totalFrames, frameSkip) == 1
        % Resize
        maxDim = 800;
        if max(size(frame, 1), size(frame, 2)) > maxDim
            scale = maxDim / max(size(frame, 1), size(frame, 2));
            frame = imresize(frame, scale);
        end
        
        % Convert to grayscale
        if size(frame, 3) == 3
            frame = rgb2gray(frame);
        end
        
        images{end+1} = frame;
        
        if mod(length(images), 10) == 0
            fprintf('  Extracted %d frames...\n', length(images));
        end
    end
end

fprintf('✓ Extracted %d frames\n\n', length(images));

if length(images) < 3
    error('Not enough frames extracted');
end

%% 4. Check Quality
fprintf('=== Checking Frame Quality ===\n');

firstFrame = images{1};
points = detectSURFFeatures(firstFrame);
fprintf('Frame size: %d x %d\n', size(firstFrame, 2), size(firstFrame, 1));
fprintf('Features detected: %d\n\n', points.Count);

%% 5. Camera Parameters
imageWidth = size(firstFrame, 2);
imageHeight = size(firstFrame, 1);

focalLength = imageWidth / (2 * tan(deg2rad(30)));
focalLength = [focalLength, focalLength];
principalPoint = [imageWidth/2, imageHeight/2];
imageSize = [imageHeight, imageWidth];

intrinsics = cameraIntrinsics(focalLength, principalPoint, imageSize);

fprintf('Camera parameters estimated\n\n');

%% 6. Create SLAM with RELAXED parameters
fprintf('=== Creating Visual SLAM (RELAXED PARAMETERS) ===\n');

vslam = VisualSLAM(intrinsics, ...
    'MinFeatures', 20, ...              % Much lower (was 40)
    'MaxReprojError', 8.0, ...          % More tolerant (was 5.0)
    'KeyFrameThreshold', 0.5, ...       % Create more key frames (was 0.65)
    'LoopScoreThreshold', 0.70);        % Easier loop detection

fprintf('✓ SLAM object created with relaxed parameters\n');
fprintf('  MinFeatures: 20 (very low threshold)\n');
fprintf('  MaxReprojError: 8.0 (very tolerant)\n');
fprintf('  KeyFrameThreshold: 0.5 (more key frames)\n\n');

%% 7. Initialize - Try many combinations
fprintf('=== Map Initialization ===\n');

initSuccess = false;
initPair = [1, 2];

% Try multiple frame combinations
attempts = [
    1, 2;
    1, 3;
    1, 4;
    1, 5;
    1, 8;
    1, 10;
    2, 5;
    2, 8;
];

for a = 1:size(attempts, 1)
    f1 = attempts(a, 1);
    f2 = attempts(a, 2);
    
    if f2 <= length(images)
        fprintf('  Try %d: frames %d and %d...', a, f1, f2);
        initSuccess = vslam.initializeMap(images{f1}, images{f2});
        
        if initSuccess
            fprintf(' ✓\n');
            initPair = [f1, f2];
            break;
        else
            fprintf(' ✗\n');
        end
    end
end

if ~initSuccess
    error('Initialization failed with all attempts');
end

fprintf('\nInitialization successful!\n');
fprintf('  Used frames: %d and %d\n', initPair(1), initPair(2));
fprintf('  Map points: %d\n', size(vslam.MapPoints, 1));
fprintf('  Key frames: %d\n\n', vslam.KeyFrameCount);

%% 8. Process frames
fprintf('=== Processing Video Frames ===\n');

startFrame = max(initPair) + 1;

stats.total = 0;
stats.tracked = 0;
stats.keyFrames = vslam.KeyFrameCount;
stats.failed = 0;
stats.loops = 0;

hFig = figure('Name', 'Relaxed SLAM Processing', 'Position', [50, 50, 1400, 500]);

for i = startFrame:length(images)
    stats.total = stats.total + 1;
    
    [pose, numMatches] = vslam.trackFrame(images{i});
    
    if numMatches >= vslam.MinFeatures
        stats.tracked = stats.tracked + 1;
        
        if vslam.checkKeyFrame(images{i})
            vslam.addKeyFrame(images{i});
            stats.keyFrames = stats.keyFrames + 1;
            
            loopCandidates = vslam.detectLoop(vslam.KeyFrameCount);
            if ~isempty(loopCandidates)
                vslam.correctDrift(vslam.KeyFrameCount, loopCandidates(1));
                stats.loops = stats.loops + 1;
            end
        end
    else
        stats.failed = stats.failed + 1;
    end
    
    % Visualize every 3 frames
    if mod(i, 3) == 0 || i == length(images)
        figure(hFig);
        
        subplot(1, 3, 1);
        imshow(images{i});
        title(sprintf('Frame %d/%d', i, length(images)));
        
        subplot(1, 3, 2);
        trajectory = vslam.getTrajectory();
        plot(trajectory(:, 1), trajectory(:, 2), 'b-', 'LineWidth', 2);
        hold on;
        plot(trajectory(end, 1), trajectory(end, 2), 'ro', 'MarkerSize', 10, 'LineWidth', 2);
        hold off;
        grid on;
        xlabel('X (m)');
        ylabel('Y (m)');
        title('Trajectory');
        axis equal;
        
        subplot(1, 3, 3);
        cla; axis off;
        text(0.05, 0.95, 'Statistics', 'FontSize', 14, 'FontWeight', 'bold');
        text(0.05, 0.85, sprintf('Processed: %d/%d', i, length(images)));
        text(0.05, 0.75, sprintf('Tracked: %d', stats.tracked));
        text(0.05, 0.65, sprintf('Failed: %d', stats.failed));
        text(0.05, 0.55, sprintf('Key frames: %d', stats.keyFrames));
        text(0.05, 0.45, sprintf('Map points: %d', size(vslam.MapPoints, 1)));
        text(0.05, 0.35, sprintf('Matches: %d', numMatches));
        
        if stats.total > 0
            successRate = 100 * stats.tracked / stats.total;
            text(0.05, 0.25, sprintf('Success: %.1f%%', successRate), 'FontWeight', 'bold');
        end
        
        drawnow;
    end
    
    if mod(i, 10) == 0
        fprintf('  Frame %d/%d\n', i, length(images));
    end
end

fprintf('\n✓ Processing complete!\n\n');

%% 9. Results
fprintf('=== Final Statistics ===\n');
fprintf('Video: %s\n', videoFile);
fprintf('Frames extracted: %d\n', length(images));
fprintf('Frames processed: %d\n', stats.total);
fprintf('Successfully tracked: %d (%.1f%%)\n', stats.tracked, 100*stats.tracked/stats.total);
fprintf('Key frames: %d\n', stats.keyFrames);
fprintf('Map points: %d\n', size(vslam.MapPoints, 1));
fprintf('Loop closures: %d\n\n', stats.loops);

%% 10. Visualize
vslam.visualizeMap();

trajectory = vslam.getTrajectory();

figure('Name', 'Relaxed SLAM - Results');
subplot(2, 2, 1);
plot(trajectory(:, 1), trajectory(:, 2), 'b-o', 'LineWidth', 1.5);
grid on; xlabel('X'); ylabel('Y'); title('Top View'); axis equal;

subplot(2, 2, 2);
plot(trajectory(:, 1), trajectory(:, 3), 'r-o', 'LineWidth', 1.5);
grid on; xlabel('X'); ylabel('Z'); title('Side XZ'); axis equal;

subplot(2, 2, 3);
plot(trajectory(:, 2), trajectory(:, 3), 'g-o', 'LineWidth', 1.5);
grid on; xlabel('Y'); ylabel('Z'); title('Side YZ'); axis equal;

subplot(2, 2, 4);
if size(trajectory, 1) > 1
    distances = sqrt(sum(diff(trajectory).^2, 2));
    cumDist = [0; cumsum(distances)];
    plot(cumDist, 'k-', 'LineWidth', 2);
    grid on; xlabel('Key Frame'); ylabel('Distance (m)');
    title(sprintf('Path: %.2f m', cumDist(end)));
end

fprintf('=== Complete! ===\n');
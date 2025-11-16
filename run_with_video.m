% Visual SLAM with Video File
% Process a video file for Visual SLAM

clear; close all; clc;

fprintf('=== Visual SLAM with Video ===\n\n');

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
fprintf('  Total frames: ~%d\n\n', round(vidObj.Duration * vidObj.FrameRate));

%% 3. Extract Frames
fprintf('=== Extracting Frames ===\n');

% Settings for frame extraction
frameSkip = max(1, round(vidObj.FrameRate / 3));  % Extract ~3 frames per second
maxFrames = 50;  % Limit total frames to process

fprintf('Frame extraction settings:\n');
fprintf('  Extracting every %d frames (~%.1f fps)\n', frameSkip, vidObj.FrameRate/frameSkip);
fprintf('  Maximum frames to extract: %d\n\n', maxFrames);

images = {};
frameCount = 0;
totalFrames = 0;

fprintf('Extracting frames...\n');

while hasFrame(vidObj) && length(images) < maxFrames
    frame = readFrame(vidObj);
    totalFrames = totalFrames + 1;
    
    % Only keep every Nth frame
    if mod(totalFrames, frameSkip) == 1
        % Resize if too large
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
        frameCount = frameCount + 1;
        
        if mod(frameCount, 10) == 0
            fprintf('  Extracted %d frames...\n', frameCount);
        end
    end
end

fprintf('✓ Extracted %d frames from %d total frames\n\n', length(images), totalFrames);

if length(images) < 3
    error('Not enough frames extracted. Try a longer video or reduce frameSkip.');
end

%% 4. Check First Frame Quality
fprintf('=== Checking Frame Quality ===\n');

firstFrame = images{1};
fprintf('Frame size: %d x %d\n', size(firstFrame, 2), size(firstFrame, 1));

% Detect features
points = detectSURFFeatures(firstFrame);
fprintf('Features detected: %d\n', points.Count);

if points.Count < 100
    warning('⚠️  Low number of features detected!');
    fprintf('Tips for better results:\n');
    fprintf('  - Record video of textured scenes (books, desks, etc.)\n');
    fprintf('  - Avoid plain walls or sky\n');
    fprintf('  - Ensure good lighting\n');
    fprintf('  - Move camera slowly and smoothly\n\n');
else
    fprintf('✓ Sufficient features for SLAM\n\n');
end

% Visualize features
figure('Name', 'Feature Detection - First Frame');
imshow(firstFrame);
hold on;
if points.Count > 0
    plot(points.selectStrongest(min(100, points.Count)));
end
title(sprintf('Frame 1: %d features detected', points.Count));
hold off;

%% 5. Setup Camera Parameters
fprintf('=== Camera Parameters ===\n');

imageWidth = size(firstFrame, 2);
imageHeight = size(firstFrame, 1);

% Estimate camera parameters (assuming ~60 degree field of view)
focalLength = imageWidth / (2 * tan(deg2rad(30)));
focalLength = [focalLength, focalLength];
principalPoint = [imageWidth/2, imageHeight/2];
imageSize = [imageHeight, imageWidth];

intrinsics = cameraIntrinsics(focalLength, principalPoint, imageSize);

fprintf('Estimated intrinsics:\n');
fprintf('  Focal length: [%.1f, %.1f]\n', focalLength);
fprintf('  Principal point: [%.1f, %.1f]\n', principalPoint);
fprintf('  Image size: [%d, %d]\n\n', imageSize);

%% 6. Create Visual SLAM Object
fprintf('=== Creating Visual SLAM Object ===\n');

vslam = VisualSLAM(intrinsics, ...
    'MinFeatures', 40, ...
    'MaxReprojError', 5.0, ...
    'KeyFrameThreshold', 0.65, ...  % More key frames for video
    'LoopScoreThreshold', 0.75);

fprintf('✓ Visual SLAM object created\n\n');

%% 7. Initialize Map
fprintf('=== Map Initialization ===\n');

initSuccess = false;
initPair = [1, 2];

% Try different frame pairs for initialization
fprintf('Attempting initialization...\n');

% Try 1: frames 1 and 2
fprintf('  Try 1: frames 1 and 2...');
initSuccess = vslam.initializeMap(images{1}, images{2});
if initSuccess
    fprintf(' ✓\n');
    initPair = [1, 2];
end

% Try 2: frames 1 and 5
if ~initSuccess && length(images) >= 5
    fprintf(' ✗\n  Try 2: frames 1 and 5...');
    initSuccess = vslam.initializeMap(images{1}, images{5});
    if initSuccess
        fprintf(' ✓\n');
        initPair = [1, 5];
    end
end

% Try 3: frames 1 and 10
if ~initSuccess && length(images) >= 10
    fprintf(' ✗\n  Try 3: frames 1 and 10...');
    initSuccess = vslam.initializeMap(images{1}, images{10});
    if initSuccess
        fprintf(' ✓\n');
        initPair = [1, 10];
    end
end

% Try 4: frames 1 and 15
if ~initSuccess && length(images) >= 15
    fprintf(' ✗\n  Try 4: frames 1 and 15...');
    initSuccess = vslam.initializeMap(images{1}, images{15});
    if initSuccess
        fprintf(' ✓\n');
        initPair = [1, 15];
    end
end

if ~initSuccess
    error(['Initialization failed!\n\n' ...
           'Possible reasons:\n' ...
           '1. Camera moved too slowly (insufficient parallax)\n' ...
           '2. Scene lacks features (plain walls, sky)\n' ...
           '3. Video is too short\n\n' ...
           'Suggestions:\n' ...
           '- Record a new video with more camera movement\n' ...
           '- Point camera at textured objects\n' ...
           '- Move camera steadily forward or sideways\n']);
end

fprintf('\nInitialization successful!\n');
fprintf('  Used frames: %d and %d\n', initPair(1), initPair(2));
fprintf('  Initial map points: %d\n', size(vslam.MapPoints, 1));
fprintf('  Key frames: %d\n\n', vslam.KeyFrameCount);

%% 8. Process Video Frames
fprintf('=== Processing Video Frames ===\n');

startFrame = max(initPair) + 1;

% Statistics
stats.totalFrames = 0;
stats.trackedFrames = 0;
stats.keyFrames = vslam.KeyFrameCount;
stats.trackingFailures = 0;
stats.loopsDetected = 0;

% Create visualization figure
hFig = figure('Name', 'Video SLAM Processing', ...
    'Position', [50, 50, 1400, 500]);

for i = startFrame:length(images)
    stats.totalFrames = stats.totalFrames + 1;
    
    % Track current frame
    [pose, numMatches] = vslam.trackFrame(images{i});
    
    if numMatches >= vslam.MinFeatures
        stats.trackedFrames = stats.trackedFrames + 1;
        
        % Check if key frame
        if vslam.checkKeyFrame(images{i})
            vslam.addKeyFrame(images{i});
            stats.keyFrames = stats.keyFrames + 1;
            
            % Loop detection
            loopCandidates = vslam.detectLoop(vslam.KeyFrameCount);
            if ~isempty(loopCandidates)
                vslam.correctDrift(vslam.KeyFrameCount, loopCandidates(1));
                stats.loopsDetected = stats.loopsDetected + 1;
                fprintf('  🔄 Loop detected! (frame %d <-> %d)\n', ...
                    vslam.KeyFrameCount, loopCandidates(1));
            end
        end
    else
        stats.trackingFailures = stats.trackingFailures + 1;
    end
    
    % Update visualization every 5 frames
    if mod(i, 5) == 0 || i == length(images)
        figure(hFig);
        
        % Current frame
        subplot(1, 3, 1);
        imshow(images{i});
        title(sprintf('Frame %d/%d', i, length(images)));
        
        % Trajectory
        subplot(1, 3, 2);
        trajectory = vslam.getTrajectory();
        plot(trajectory(:, 1), trajectory(:, 2), 'b-', 'LineWidth', 2);
        hold on;
        plot(trajectory(end, 1), trajectory(end, 2), 'ro', ...
            'MarkerSize', 10, 'LineWidth', 2);
        hold off;
        grid on;
        xlabel('X (m)');
        ylabel('Y (m)');
        title('Camera Trajectory');
        axis equal;
        
        % Statistics
        subplot(1, 3, 3);
        cla;
        axis off;
        text(0.05, 0.95, '📊 Statistics', 'FontSize', 14, 'FontWeight', 'bold');
        text(0.05, 0.85, sprintf('Processed: %d/%d', i, length(images)));
        text(0.05, 0.75, sprintf('Tracked: %d', stats.trackedFrames));
        text(0.05, 0.65, sprintf('Failed: %d', stats.trackingFailures));
        text(0.05, 0.55, sprintf('Key frames: %d', stats.keyFrames));
        text(0.05, 0.45, sprintf('Map points: %d', size(vslam.MapPoints, 1)));
        text(0.05, 0.35, sprintf('Loops: %d', stats.loopsDetected));
        text(0.05, 0.25, sprintf('Matches: %d', numMatches));
        
        successRate = 100 * stats.trackedFrames / stats.totalFrames;
        text(0.05, 0.15, sprintf('Success: %.1f%%', successRate), ...
            'FontWeight', 'bold');
        
        drawnow;
    end
    
    % Progress update
    if mod(i, 10) == 0
        fprintf('Progress: %d/%d frames (%.1f%%)\n', i, length(images), ...
            100*i/length(images));
    end
end

fprintf('\n✓ All frames processed!\n\n');

%% 9. Final Statistics
fprintf('=== Final Statistics ===\n');
fprintf('Video: %s\n', videoFile);
fprintf('Total frames extracted: %d\n', length(images));
fprintf('Frames processed: %d\n', stats.totalFrames);
fprintf('Successfully tracked: %d (%.1f%%)\n', stats.trackedFrames, ...
    100*stats.trackedFrames/stats.totalFrames);
fprintf('Tracking failures: %d\n', stats.trackingFailures);
fprintf('Key frames: %d\n', stats.keyFrames);
fprintf('Map points: %d\n', size(vslam.MapPoints, 1));
fprintf('Loop closures: %d\n\n', stats.loopsDetected);

%% 10. Final Visualization
fprintf('=== Generating Visualizations ===\n');

% 3D map
vslam.visualizeMap();

% Trajectory analysis
figure('Name', 'Video SLAM - Trajectory Analysis');

trajectory = vslam.getTrajectory();

% Top view
subplot(2, 2, 1);
plot(trajectory(:, 1), trajectory(:, 2), 'b-o', 'LineWidth', 1.5);
grid on;
xlabel('X (m)');
ylabel('Y (m)');
title('Top View');
axis equal;

% Side view XZ
subplot(2, 2, 2);
plot(trajectory(:, 1), trajectory(:, 3), 'r-o', 'LineWidth', 1.5);
grid on;
xlabel('X (m)');
ylabel('Z (m)');
title('Side View (XZ)');
axis equal;

% Side view YZ
subplot(2, 2, 3);
plot(trajectory(:, 2), trajectory(:, 3), 'g-o', 'LineWidth', 1.5);
grid on;
xlabel('Y (m)');
ylabel('Z (m)');
title('Side View (YZ)');
axis equal;

% Path length
subplot(2, 2, 4);
if size(trajectory, 1) > 1
    distances = sqrt(sum(diff(trajectory).^2, 2));
    cumDist = [0; cumsum(distances)];
    plot(cumDist, 'k-', 'LineWidth', 2);
    grid on;
    xlabel('Key Frame');
    ylabel('Cumulative Distance (m)');
    title(sprintf('Total Path: %.2f m', cumDist(end)));
end

fprintf('✓ Visualizations complete\n\n');

%% 11. Save Results
fprintf('=== Saving Results ===\n');

% Create results folder
[~, videoName, ~] = fileparts(videoFile);
resultsFolder = fullfile(videoPath, [videoName '_SLAM_Results']);

if ~exist(resultsFolder, 'dir')
    mkdir(resultsFolder);
end

% Save data
save(fullfile(resultsFolder, 'map_points.mat'), 'vslam');
save(fullfile(resultsFolder, 'trajectory.mat'), 'trajectory');
save(fullfile(resultsFolder, 'statistics.mat'), 'stats');

% Save video info
videoInfo.file = videoFile;
videoInfo.duration = vidObj.Duration;
videoInfo.frameRate = vidObj.FrameRate;
videoInfo.resolution = [vidObj.Width, vidObj.Height];
videoInfo.framesExtracted = length(images);
save(fullfile(resultsFolder, 'video_info.mat'), 'videoInfo');

% Save figures
figList = findall(0, 'Type', 'figure');
for i = 1:length(figList)
    figName = get(figList(i), 'Name');
    if ~isempty(figName)
        figName = strrep(figName, ' ', '_');
        figName = strrep(figName, '-', '_');
        saveas(figList(i), fullfile(resultsFolder, [figName '.png']));
    end
end

fprintf('✓ Results saved to: %s\n', resultsFolder);

%% 12. Complete
fprintf('\n=== ✅ Video SLAM Complete! ===\n');
fprintf('\nResults Summary:\n');
fprintf('  🎥 Video: %s\n', videoFile);
fprintf('  📍 Map points: %d\n', size(vslam.MapPoints, 1));
fprintf('  📷 Key frames: %d\n', stats.keyFrames);
if exist('cumDist', 'var')
    fprintf('  📏 Camera path: %.2f m\n', cumDist(end));
end
fprintf('  ✓ Success rate: %.1f%%\n', 100*stats.trackedFrames/stats.totalFrames);
fprintf('\n📁 Results folder: %s\n', resultsFolder);
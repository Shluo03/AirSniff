% Ultra-Relaxed 3D Reconstruction
% For challenging videos - extracts maximum possible 3D points

clear; close all; clc;

fprintf('=== Ultra-Relaxed 3D Reconstruction ===\n');
fprintf('This mode extracts maximum 3D points from difficult videos\n\n');

%% Select Video
[videoFile, videoPath] = uigetfile('*.mov;*.mp4;*.avi', 'Select Video');
if videoFile == 0, error('No video selected'); end

videoFullPath = fullfile(videoPath, videoFile);
vidObj = VideoReader(videoFullPath);

fprintf('Video: %s (%.1f sec)\n\n', videoFile, vidObj.Duration);

%% Extract MANY frames
fprintf('Extracting frames (MAXIMUM)...\n');
frameSkip = max(1, round(vidObj.FrameRate / 10));  % 10 fps!
maxFrames = 150;  % More frames

images = {};
colorImages = {};
totalFrames = 0;

while hasFrame(vidObj) && length(images) < maxFrames
    frame = readFrame(vidObj);
    totalFrames = totalFrames + 1;
    
    if mod(totalFrames, frameSkip) == 1
        maxDim = 640;  % Smaller for speed
        if max(size(frame, 1), size(frame, 2)) > maxDim
            scale = maxDim / max(size(frame, 1), size(frame, 2));
            frame = imresize(frame, scale);
        end
        
        colorImages{end+1} = frame;
        if size(frame, 3) == 3
            images{end+1} = rgb2gray(frame);
        else
            images{end+1} = frame;
        end
        
        if mod(length(images), 30) == 0
            fprintf('  %d frames...\n', length(images));
        end
    end
end

fprintf('✓ Extracted %d frames\n\n', length(images));

%% Camera Setup  
imageWidth = size(images{1}, 2);
imageHeight = size(images{1}, 1);
focalLength = imageWidth / (2 * tan(deg2rad(30)));
focalLength = [focalLength, focalLength];
intrinsics = cameraIntrinsics(focalLength, [imageWidth/2, imageHeight/2], ...
    [imageHeight, imageWidth]);

%% ULTRA-RELAXED SLAM
fprintf('Running ULTRA-RELAXED SLAM...\n');

vslam = VisualSLAM(intrinsics, ...
    'MinFeatures', 10, ...              % VERY low (was 20)
    'MaxReprojError', 12.0, ...         % VERY tolerant (was 8.0)
    'KeyFrameThreshold', 0.4, ...       % Many key frames (was 0.5)
    'LoopScoreThreshold', 0.65);

% Try MANY initialization combinations
initSuccess = false;
attempts = [1,2; 1,3; 1,5; 1,8; 1,10; 1,15; 2,5; 2,8; 2,10; 3,8; 3,10; 5,10; 5,15];

for i = 1:size(attempts, 1)
    f1 = attempts(i,1);
    f2 = attempts(i,2);
    
    if f2 <= length(images)
        initSuccess = vslam.initializeMap(images{f1}, images{f2});
        if initSuccess
            fprintf('✓ Init: frames %d & %d\n', f1, f2);
            startFrame = max(f1, f2) + 1;
            break;
        end
    end
end

if ~initSuccess
    error('Cannot initialize - video too difficult');
end

fprintf('  Initial points: %d\n\n', size(vslam.MapPoints, 1));

%% Process frames
fprintf('Processing...\n');
stats.tracked = 0;
stats.total = 0;

for i = startFrame:length(images)
    stats.total = stats.total + 1;
    [~, numMatches] = vslam.trackFrame(images{i});
    
    if numMatches >= vslam.MinFeatures
        stats.tracked = stats.tracked + 1;
        if vslam.checkKeyFrame(images{i})
            vslam.addKeyFrame(images{i});
        end
    end
    
    if mod(i, 30) == 0
        fprintf('  %d/%d (%.0f%% tracked)\n', i, length(images), ...
            100*stats.tracked/max(1,stats.total));
    end
end

fprintf('\n✓ SLAM done: %.0f%% success, %d key frames, %d points\n\n', ...
    100*stats.tracked/max(1,stats.total), vslam.KeyFrameCount, size(vslam.MapPoints, 1));

%% Generate MAXIMUM dense points
fprintf('Generating MAXIMUM dense 3D points...\n');

allPoints3D = [];
allColors = [];

% Use MORE key frame pairs
numPairs = min(vslam.KeyFrameCount-1, 30);

for i = 1:numPairs
    kf1 = vslam.KeyFrames(i);
    kf2 = vslam.KeyFrames(min(i+1, vslam.KeyFrameCount));
    
    % Find images
    kf1_idx = [];
    kf2_idx = [];
    
    for j = 1:length(images)
        if isequal(images{j}, kf1.Image)
            kf1_idx = j;
        end
        if isequal(images{j}, kf2.Image)
            kf2_idx = j;
        end
    end
    
    if ~isempty(kf1_idx) && ~isempty(kf2_idx)
        img1 = images{kf1_idx};
        img2 = images{kf2_idx};
        colorImg1 = colorImages{kf1_idx};
        
        % DENSE features
        points1 = detectSURFFeatures(img1, 'NumOctaves', 4, 'NumScaleLevels', 6);
        points2 = detectSURFFeatures(img2, 'NumOctaves', 4, 'NumScaleLevels', 6);
        
        [features1, validPts1] = extractFeatures(img1, points1);
        [features2, validPts2] = extractFeatures(img2, points2);
        
        indexPairs = matchFeatures(features1, features2, ...
            'Unique', true, 'MaxRatio', 0.8);
        
        if size(indexPairs, 1) > 20
            matchedPts1 = validPts1(indexPairs(:, 1));
            matchedPts2 = validPts2(indexPairs(:, 2));
            
            % Camera matrices
            camMatrix1 = cameraMatrix(intrinsics, ...
                kf1.Pose(1:3,1:3)', -kf1.Pose(1:3,1:3)' * kf1.Pose(1:3,4));
            camMatrix2 = cameraMatrix(intrinsics, ...
                kf2.Pose(1:3,1:3)', -kf2.Pose(1:3,1:3)' * kf2.Pose(1:3,4));
            
            % Triangulate
            [points3D, reprojErrors] = triangulate(matchedPts1, matchedPts2, ...
                camMatrix1, camMatrix2);
            
            % RELAXED filtering
            validIdx = reprojErrors < 8.0;  % Very tolerant
            points3D = points3D(validIdx, :);
            
            % Colors
            locations = round(matchedPts1.Location(validIdx, :));
            colors = zeros(size(points3D, 1), 3);
            
            for j = 1:size(points3D, 1)
                x = max(1, min(imageWidth, locations(j, 1)));
                y = max(1, min(imageHeight, locations(j, 2)));
                
                if size(colorImg1, 3) == 3
                    colors(j, :) = double(squeeze(colorImg1(y, x, :)))' / 255;
                else
                    gray = double(colorImg1(y, x)) / 255;
                    colors(j, :) = [gray, gray, gray];
                end
            end
            
            allPoints3D = [allPoints3D; points3D];
            allColors = [allColors; colors];
            
            if mod(i, 5) == 0
                fprintf('  Pair %d/%d: %d total points\n', i, numPairs, size(allPoints3D, 1));
            end
        end
    end
end

fprintf('\n✓ Generated %d dense 3D points\n\n', size(allPoints3D, 1));

%% Clean outliers
if size(allPoints3D, 1) > 10
    distances = sqrt(sum(allPoints3D.^2, 2));
    medianDist = median(distances);
    stdDist = std(distances);
    
    validIdx = abs(distances - medianDist) < 4 * stdDist;  % More tolerant
    
    cleanPoints3D = allPoints3D(validIdx, :);
    cleanColors = allColors(validIdx, :);
    
    fprintf('Cleaned: %d points (removed %d outliers)\n\n', ...
        size(cleanPoints3D, 1), nnz(~validIdx));
else
    cleanPoints3D = allPoints3D;
    cleanColors = allColors;
end

%% Visualize
if size(cleanPoints3D, 1) > 0
    fprintf('Creating visualization...\n');
    
    figure('Name', 'Ultra-Relaxed 3D Reconstruction', ...
        'Position', [50, 50, 1400, 900]);
    
    % Main view - POINTS ONLY
    scatter3(cleanPoints3D(:,1), cleanPoints3D(:,2), cleanPoints3D(:,3), ...
        15, cleanColors, 'filled', 'MarkerEdgeAlpha', 0.7);
    
    xlabel('X (m)'); ylabel('Y (m)'); zlabel('Z (m)');
    title(sprintf('3D Reconstruction - %d points', size(cleanPoints3D, 1)));
    axis equal; grid on;
    view(3);
    set(gca, 'Color', 'k');  % Black background
    camlight('headlight');
    rotate3d on;
    
    % Statistics
    fprintf('\n=== Results ===\n');
    fprintf('3D Points: %d\n', size(cleanPoints3D, 1));
    fprintf('Key Frames: %d\n', vslam.KeyFrameCount);
    fprintf('Success Rate: %.1f%%\n', 100*stats.tracked/max(1,stats.total));
    
    % Extent
    minPt = min(cleanPoints3D);
    maxPt = max(cleanPoints3D);
    extent = maxPt - minPt;
    fprintf('\nScene size:\n');
    fprintf('  X: %.2f m\n', extent(1));
    fprintf('  Y: %.2f m\n', extent(2));
    fprintf('  Z: %.2f m\n', extent(3));
    
    % Save
    [~, name, ~] = fileparts(videoFile);
    resultsFolder = fullfile(videoPath, [name '_UltraRelaxed_3D']);
    if ~exist(resultsFolder, 'dir'), mkdir(resultsFolder); end
    
    pointCloud.points = cleanPoints3D;
    pointCloud.colors = cleanColors;
    pointCloud.trajectory = vslam.getTrajectory();
    
    save(fullfile(resultsFolder, 'point_cloud.mat'), 'pointCloud');
    saveas(gcf, fullfile(resultsFolder, 'reconstruction.png'));
    
    fprintf('\n✓ Saved to: %s\n', resultsFolder);
else
    warning('No 3D points generated');
end

fprintf('\n=== Complete ===\n');
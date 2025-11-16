% 3D Reconstruction from Video
% Creates dense 3D point cloud reconstruction

clear; close all; clc;

fprintf('=== 3D Reconstruction from Video ===\n\n');

%% 1. Select Video
fprintf('Select video file for 3D reconstruction...\n');
[videoFile, videoPath] = uigetfile(...
    {'*.mp4;*.mov;*.avi;*.m4v', 'Video Files'}, ...
    'Select Video for 3D Reconstruction');

if videoFile == 0
    error('No video selected');
end

videoFullPath = fullfile(videoPath, videoFile);
fprintf('Selected: %s\n\n', videoFile);

%% 2. Read Video
fprintf('=== Loading Video ===\n');
vidObj = VideoReader(videoFullPath);

fprintf('Video info:\n');
fprintf('  Duration: %.1f sec\n', vidObj.Duration);
fprintf('  Frame rate: %.1f fps\n', vidObj.FrameRate);
fprintf('  Resolution: %d x %d\n\n', vidObj.Width, vidObj.Height);

%% 3. Extract Frames for Dense Reconstruction
fprintf('=== Extracting Frames ===\n');

% For 3D reconstruction, we want MORE frames
frameSkip = max(1, round(vidObj.FrameRate / 6));  % 6 fps
maxFrames = 100;  % More frames = better 3D

fprintf('Extracting every %d frames (~%.1f fps)\n', frameSkip, vidObj.FrameRate/frameSkip);
fprintf('Maximum frames: %d\n\n', maxFrames);

images = {};
colorImages = {};  % Keep color for visualization
totalFrames = 0;

while hasFrame(vidObj) && length(images) < maxFrames
    frame = readFrame(vidObj);
    totalFrames = totalFrames + 1;
    
    if mod(totalFrames, frameSkip) == 1
        % Resize if needed
        maxDim = 800;
        if max(size(frame, 1), size(frame, 2)) > maxDim
            scale = maxDim / max(size(frame, 1), size(frame, 2));
            frame = imresize(frame, scale);
        end
        
        % Store both color and grayscale
        colorImages{end+1} = frame;
        
        if size(frame, 3) == 3
            grayFrame = rgb2gray(frame);
        else
            grayFrame = frame;
        end
        
        images{end+1} = grayFrame;
        
        if mod(length(images), 20) == 0
            fprintf('  Extracted %d frames...\n', length(images));
        end
    end
end

fprintf('✓ Extracted %d frames\n\n', length(images));

%% 4. Setup Camera
fprintf('=== Camera Setup ===\n');

imageWidth = size(images{1}, 2);
imageHeight = size(images{1}, 1);

focalLength = imageWidth / (2 * tan(deg2rad(30)));
focalLength = [focalLength, focalLength];
principalPoint = [imageWidth/2, imageHeight/2];
imageSize = [imageHeight, imageWidth];

intrinsics = cameraIntrinsics(focalLength, principalPoint, imageSize);
fprintf('Camera intrinsics estimated\n\n');

%% 5. Run SLAM with Relaxed Parameters
fprintf('=== Running Visual SLAM ===\n');

vslam = VisualSLAM(intrinsics, ...
    'MinFeatures', 20, ...
    'MaxReprojError', 8.0, ...
    'KeyFrameThreshold', 0.5, ...
    'LoopScoreThreshold', 0.70);

% Initialize
fprintf('Initializing map...\n');
initSuccess = false;

for attempt = 1:8
    pairs = [1,2; 1,3; 1,5; 1,8; 2,5; 2,8; 1,10; 3,10];
    
    if attempt <= size(pairs, 1)
        f1 = pairs(attempt, 1);
        f2 = pairs(attempt, 2);
        
        if f2 <= length(images)
            initSuccess = vslam.initializeMap(images{f1}, images{f2});
            if initSuccess
                fprintf('✓ Initialized with frames %d and %d\n', f1, f2);
                startFrame = max(f1, f2) + 1;
                break;
            end
        end
    end
end

if ~initSuccess
    error('Initialization failed');
end

fprintf('  Initial 3D points: %d\n\n', size(vslam.MapPoints, 1));

%% 6. Process All Frames
fprintf('=== Processing for 3D Reconstruction ===\n');

stats.total = 0;
stats.tracked = 0;
stats.keyFrames = vslam.KeyFrameCount;

for i = startFrame:length(images)
    stats.total = stats.total + 1;
    
    [~, numMatches] = vslam.trackFrame(images{i});
    
    if numMatches >= vslam.MinFeatures
        stats.tracked = stats.tracked + 1;
        
        if vslam.checkKeyFrame(images{i})
            vslam.addKeyFrame(images{i});
            stats.keyFrames = stats.keyFrames + 1;
        end
    end
    
    if mod(i, 20) == 0
        fprintf('  Processed %d/%d frames (%.0f%% tracked)\n', ...
            i, length(images), 100*stats.tracked/stats.total);
    end
end

fprintf('\n✓ SLAM complete!\n');
fprintf('  Success rate: %.1f%%\n', 100*stats.tracked/stats.total);
fprintf('  Key frames: %d\n', stats.keyFrames);
fprintf('  3D points: %d\n\n', size(vslam.MapPoints, 1));

%% 7. Dense Point Cloud Generation
fprintf('=== Generating Dense 3D Point Cloud ===\n');

allPoints3D = [];
allColors = [];

% For each key frame pair, generate dense points
for i = 1:min(stats.keyFrames-1, 20)  % Limit for performance
    kf1 = vslam.KeyFrames(i);
    kf2 = vslam.KeyFrames(i+1);
    
    fprintf('  Processing key frame pair %d-%d...\n', i, i+1);
    
    % Get images
    kf1_idx = find(cellfun(@(x) isequal(x, kf1.Image), images), 1);
    kf2_idx = find(cellfun(@(x) isequal(x, kf2.Image), images), 1);
    
    if ~isempty(kf1_idx) && ~isempty(kf2_idx)
        img1 = images{kf1_idx};
        img2 = images{kf2_idx};
        colorImg1 = colorImages{kf1_idx};
        
        % Dense feature matching
        points1 = detectSURFFeatures(img1, 'NumOctaves', 4);
        points2 = detectSURFFeatures(img2, 'NumOctaves', 4);
        
        [features1, validPts1] = extractFeatures(img1, points1);
        [features2, validPts2] = extractFeatures(img2, points2);
        
        indexPairs = matchFeatures(features1, features2, 'Unique', true);
        
        if size(indexPairs, 1) > 50
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
            
            % Filter by reprojection error
            validIdx = reprojErrors < 4.0;
            points3D = points3D(validIdx, :);
            
            % Get colors
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
            
            % Add to collection
            allPoints3D = [allPoints3D; points3D];
            allColors = [allColors; colors];
            
            fprintf('    Added %d dense points\n', size(points3D, 1));
        end
    end
end

fprintf('\n✓ Dense reconstruction complete!\n');
fprintf('  Total 3D points: %d\n\n', size(allPoints3D, 1));

%% 8. Filter and Clean Point Cloud
fprintf('=== Cleaning Point Cloud ===\n');

if size(allPoints3D, 1) > 0
    % Remove outliers based on distance from median
    distances = sqrt(sum(allPoints3D.^2, 2));
    medianDist = median(distances);
    stdDist = std(distances);
    
    % Keep points within 3 standard deviations
    validIdx = abs(distances - medianDist) < 3 * stdDist;
    
    cleanPoints3D = allPoints3D(validIdx, :);
    cleanColors = allColors(validIdx, :);
    
    fprintf('  Removed %d outliers\n', nnz(~validIdx));
    fprintf('  Clean points: %d\n\n', size(cleanPoints3D, 1));
else
    cleanPoints3D = allPoints3D;
    cleanColors = allColors;
end

%% 9. Visualize 3D Reconstruction
fprintf('=== Visualizing 3D Reconstruction ===\n');

if size(cleanPoints3D, 1) > 0
    % Main 3D visualization
    figure('Name', '3D Reconstruction - Dense Point Cloud', ...
        'Position', [100, 100, 1200, 800]);
    
    scatter3(cleanPoints3D(:,1), cleanPoints3D(:,2), cleanPoints3D(:,3), ...
        2, cleanColors, 'filled');
    
    hold on;
    
    % Add camera trajectory
    trajectory = vslam.getTrajectory();
    plot3(trajectory(:,1), trajectory(:,2), trajectory(:,3), ...
        'r-', 'LineWidth', 3);
    plot3(trajectory(:,1), trajectory(:,2), trajectory(:,3), ...
        'ro', 'MarkerSize', 8, 'LineWidth', 2);
    
    % Plot camera positions with orientation
    for i = 1:size(trajectory, 1)
        pose = vslam.KeyFrames(i).Pose;
        loc = pose(1:3, 4);
        R = pose(1:3, 1:3);
        
        % Camera coordinate axes
        scale = 0.1;
        quiver3(loc(1), loc(2), loc(3), ...
            R(1,3)*scale, R(2,3)*scale, R(3,3)*scale, ...
            'r', 'LineWidth', 2, 'MaxHeadSize', 0.5);
    end
    
    hold off;
    
    xlabel('X (m)'); ylabel('Y (m)'); zlabel('Z (m)');
    title(sprintf('3D Reconstruction (%d points)', size(cleanPoints3D, 1)));
    grid on;
    axis equal;
    view(3);
    
    % Add lighting for better visualization
    camlight('headlight');
    lighting gouraud;
    
    fprintf('✓ 3D visualization created\n');
    
    % Multiple view angles
    figure('Name', '3D Reconstruction - Multiple Views', ...
        'Position', [150, 150, 1400, 900]);
    
    % Top view
    subplot(2, 3, 1);
    scatter3(cleanPoints3D(:,1), cleanPoints3D(:,2), cleanPoints3D(:,3), ...
        1, cleanColors, 'filled');
    hold on;
    plot3(trajectory(:,1), trajectory(:,2), trajectory(:,3), 'r-', 'LineWidth', 2);
    hold off;
    view(0, 90);
    xlabel('X'); ylabel('Y'); title('Top View');
    axis equal; grid on;
    
    % Front view
    subplot(2, 3, 2);
    scatter3(cleanPoints3D(:,1), cleanPoints3D(:,2), cleanPoints3D(:,3), ...
        1, cleanColors, 'filled');
    hold on;
    plot3(trajectory(:,1), trajectory(:,2), trajectory(:,3), 'r-', 'LineWidth', 2);
    hold off;
    view(0, 0);
    xlabel('X'); ylabel('Z'); title('Front View');
    axis equal; grid on;
    
    % Side view
    subplot(2, 3, 3);
    scatter3(cleanPoints3D(:,1), cleanPoints3D(:,2), cleanPoints3D(:,3), ...
        1, cleanColors, 'filled');
    hold on;
    plot3(trajectory(:,1), trajectory(:,2), trajectory(:,3), 'r-', 'LineWidth', 2);
    hold off;
    view(90, 0);
    xlabel('Y'); ylabel('Z'); title('Side View');
    axis equal; grid on;
    
    % 3D perspective views
    for i = 1:3
        subplot(2, 3, 3+i);
        scatter3(cleanPoints3D(:,1), cleanPoints3D(:,2), cleanPoints3D(:,3), ...
            1, cleanColors, 'filled');
        hold on;
        plot3(trajectory(:,1), trajectory(:,2), trajectory(:,3), 'r-', 'LineWidth', 2);
        hold off;
        view(45 + (i-1)*60, 30);
        xlabel('X'); ylabel('Y'); zlabel('Z');
        title(sprintf('3D View %d', i));
        axis equal; grid on;
    end
    
    fprintf('✓ Multiple view visualization created\n');
    
else
    warning('No 3D points generated - reconstruction failed');
end

%% 10. Point Cloud Statistics
fprintf('\n=== 3D Reconstruction Statistics ===\n');
fprintf('Video: %s\n', videoFile);
fprintf('Frames processed: %d\n', length(images));
fprintf('Key frames used: %d\n', stats.keyFrames);
fprintf('SLAM 3D points: %d\n', size(vslam.MapPoints, 1));
fprintf('Dense 3D points: %d\n', size(allPoints3D, 1));
fprintf('Clean 3D points: %d\n', size(cleanPoints3D, 1));

if size(cleanPoints3D, 1) > 0
    % Point cloud extent
    minPt = min(cleanPoints3D);
    maxPt = max(cleanPoints3D);
    extent = maxPt - minPt;
    
    fprintf('\nReconstruction extent:\n');
    fprintf('  X: %.2f to %.2f m (%.2f m)\n', minPt(1), maxPt(1), extent(1));
    fprintf('  Y: %.2f to %.2f m (%.2f m)\n', minPt(2), maxPt(2), extent(2));
    fprintf('  Z: %.2f to %.2f m (%.2f m)\n', minPt(3), maxPt(3), extent(3));
end

%% 11. Save Results
fprintf('\n=== Saving 3D Reconstruction ===\n');

[~, videoName, ~] = fileparts(videoFile);
resultsFolder = fullfile(videoPath, [videoName '_3D_Reconstruction']);

if ~exist(resultsFolder, 'dir')
    mkdir(resultsFolder);
end

% Save point cloud data
pointCloud.points = cleanPoints3D;
pointCloud.colors = cleanColors;
pointCloud.trajectory = trajectory;
pointCloud.keyFrames = vslam.KeyFrames;

save(fullfile(resultsFolder, 'point_cloud.mat'), 'pointCloud');
fprintf('✓ Saved point cloud data\n');

% Save as PLY format (standard 3D format)
if size(cleanPoints3D, 1) > 0
    plyFile = fullfile(resultsFolder, 'reconstruction.ply');
    writePLY(plyFile, cleanPoints3D, cleanColors);
    fprintf('✓ Saved PLY file: %s\n', plyFile);
end

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

fprintf('✓ Saved visualization images\n');
fprintf('\n📁 Results folder: %s\n', resultsFolder);

fprintf('\n=== ✅ 3D Reconstruction Complete! ===\n');

%% Helper function to write PLY file
function writePLY(filename, points, colors)
    fid = fopen(filename, 'w');
    
    % Header
    fprintf(fid, 'ply\n');
    fprintf(fid, 'format ascii 1.0\n');
    fprintf(fid, 'element vertex %d\n', size(points, 1));
    fprintf(fid, 'property float x\n');
    fprintf(fid, 'property float y\n');
    fprintf(fid, 'property float z\n');
    fprintf(fid, 'property uchar red\n');
    fprintf(fid, 'property uchar green\n');
    fprintf(fid, 'property uchar blue\n');
    fprintf(fid, 'end_header\n');
    
    % Data
    for i = 1:size(points, 1)
        fprintf(fid, '%f %f %f %d %d %d\n', ...
            points(i,1), points(i,2), points(i,3), ...
            round(colors(i,1)*255), ...
            round(colors(i,2)*255), ...
            round(colors(i,3)*255));
    end
    
    fclose(fid);
end
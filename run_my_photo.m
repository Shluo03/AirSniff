% Visual SLAM using My_photo folder
% 使用 My_photo 文件夹中的照片运行 Visual SLAM

clear; close all; clc;

fprintf('=== Visual SLAM - My_photo 文件夹 ===\n\n');

%% 1. 设置照片文件夹路径
% 使用 My_photo 文件夹(在当前目录下)
imageFolder = fullfile(pwd, 'My_photo');

if ~exist(imageFolder, 'dir')
    error('找不到 My_photo 文件夹!当前目录: %s', pwd);
end

fprintf('照片文件夹: %s\n', imageFolder);

%% 2. 读取照片(支持 JPG, JPEG, PNG 格式)
fprintf('正在读取照片...\n');

% 查找图片文件(只查找JPG/JPEG/PNG,不查找HEIC)
imageFiles = [dir(fullfile(imageFolder, '*.jpg')); ...
              dir(fullfile(imageFolder, '*.jpeg')); ...
              dir(fullfile(imageFolder, '*.png'))];

if isempty(imageFiles)
    error('在 My_photo 文件夹中没有找到 JPG/JPEG/PNG 格式的图片文件');
end

fprintf('找到 %d 张照片\n', length(imageFiles));

% 读取所有照片
images = cell(length(imageFiles), 1);

for i = 1:length(imageFiles)
    fprintf('  读取照片 %d/%d: %s\n', i, length(imageFiles), imageFiles(i).name);
    
    try
        % 读取图片
        img = imread(fullfile(imageFolder, imageFiles(i).name));
        
        % 如果图片太大,缩小以加快处理
        maxDim = 800;
        if max(size(img, 1), size(img, 2)) > maxDim
            scale = maxDim / max(size(img, 1), size(img, 2));
            img = imresize(img, scale);
            fprintf('    图片已缩放到: %d x %d\n', size(img, 2), size(img, 1));
        end
        
        % 转换为灰度
        if size(img, 3) == 3
            img = rgb2gray(img);
        end
        
        images{i} = img;
        
    catch ME
        error('读取照片失败: %s\n错误: %s', imageFiles(i).name, ME.message);
    end
end

fprintf('✓ 所有照片读取完成\n\n');

%% 3. 检查第一张照片的质量
fprintf('=== 检查照片质量 ===\n');

firstImg = images{1};
fprintf('照片尺寸: %d x %d\n', size(firstImg, 2), size(firstImg, 1));

% 检测特征点
points = detectSURFFeatures(firstImg);
fprintf('检测到特征点: %d\n', points.Count);

if points.Count < 100
    warning('⚠️  特征点较少!可能影响SLAM效果');
    fprintf('建议:\n');
    fprintf('  - 拍摄时对准纹理丰富的物体\n');
    fprintf('  - 避免对着纯色墙壁或天空\n');
    fprintf('  - 增加室内光照\n\n');
else
    fprintf('✓ 特征点充足,可以运行SLAM\n\n');
end

% 可视化特征
figure('Name', '照片1的特征检测');
imshow(firstImg);
hold on;
if points.Count > 0
    plot(points.selectStrongest(min(100, points.Count)));
end
title(sprintf('%s - %d 个特征点', imageFiles(1).name, points.Count));
hold off;

%% 4. 设置相机参数
% 估算相机内参(基于iPhone的典型参数)
imageWidth = size(firstImg, 2);
imageHeight = size(firstImg, 1);

% iPhone 相机典型焦距(估算)
focalLength = imageWidth / (2 * tan(deg2rad(30)));  % 假设60度视场角
focalLength = [focalLength, focalLength];
principalPoint = [imageWidth/2, imageHeight/2];
imageSize = [imageHeight, imageWidth];

intrinsics = cameraIntrinsics(focalLength, principalPoint, imageSize);

fprintf('=== 相机参数(估算) ===\n');
fprintf('焦距: [%.1f, %.1f] 像素\n', focalLength);
fprintf('主点: [%.1f, %.1f]\n', principalPoint);
fprintf('图片尺寸: [%d, %d]\n\n', imageSize);

%% 5. 创建 Visual SLAM 对象
fprintf('=== 创建 Visual SLAM 对象 ===\n');

vslam = VisualSLAM(intrinsics, ...
    'MinFeatures', 40, ...              % 降低要求以适应真实照片
    'MaxReprojError', 5.0, ...          % 增加容错
    'KeyFrameThreshold', 0.7, ...       
    'LoopScoreThreshold', 0.75);

fprintf('✓ Visual SLAM 对象已创建\n\n');

%% 6. 初始化地图
fprintf('=== 初始化地图 ===\n');

% 尝试不同的图片组合进行初始化
initSuccess = false;
initPair = [1, 2];  % 默认使用第1和第2张

% 尝试1: 第1和第2张
fprintf('尝试使用照片 1 和 2 初始化...\n');
initSuccess = vslam.initializeMap(images{1}, images{2});

if initSuccess
    fprintf('✓ 初始化成功 (照片 1 和 2)\n');
    initPair = [1, 2];
end

% 尝试2: 如果失败,使用第1和第3张
if ~initSuccess && length(images) >= 3
    fprintf('❌ 失败,尝试照片 1 和 3...\n');
    initSuccess = vslam.initializeMap(images{1}, images{3});
    if initSuccess
        fprintf('✓ 初始化成功 (照片 1 和 3)\n');
        initPair = [1, 3];
    end
end

% 尝试3: 如果还是失败,使用第1和第4张
if ~initSuccess && length(images) >= 4
    fprintf('❌ 失败,尝试照片 1 和 4...\n');
    initSuccess = vslam.initializeMap(images{1}, images{4});
    if initSuccess
        fprintf('✓ 初始化成功 (照片 1 和 4)\n');
        initPair = [1, 4];
    end
end

% 尝试4: 最后尝试第1和第5张
if ~initSuccess && length(images) >= 5
    fprintf('❌ 失败,尝试照片 1 和 5...\n');
    initSuccess = vslam.initializeMap(images{1}, images{5});
    if initSuccess
        fprintf('✓ 初始化成功 (照片 1 和 5)\n');
        initPair = [1, 5];
    end
end

if ~initSuccess
    error(['❌ 初始化失败!\n\n' ...
           '可能原因:\n' ...
           '1. 照片之间的相机移动太小(视差不够)\n' ...
           '2. 场景特征太少(如对着墙壁或天空)\n' ...
           '3. 照片模糊或光照不足\n\n' ...
           '建议:\n' ...
           '- 重新拍摄,每张照片之间移动相机 20-30cm\n' ...
           '- 对准纹理丰富的场景(书桌、书架等)\n' ...
           '- 确保照片清晰,光照充足\n']);
end

fprintf('\n初始化信息:\n');
fprintf('  使用照片: %s 和 %s\n', imageFiles(initPair(1)).name, ...
    imageFiles(initPair(2)).name);
fprintf('  初始地图点数: %d\n', size(vslam.MapPoints, 1));
fprintf('  关键帧数: %d\n\n', vslam.KeyFrameCount);

%% 7. 处理剩余照片
fprintf('=== 处理照片序列 ===\n');

% 确定起始照片(跳过已用于初始化的)
startIdx = max(initPair) + 1;

% 统计信息
stats.totalProcessed = 0;
stats.successfulTracks = 0;
stats.keyFrames = vslam.KeyFrameCount;
stats.failedTracks = 0;
stats.loopsDetected = 0;

% 创建实时显示窗口
hFig = figure('Name', 'Visual SLAM 处理进度', ...
    'Position', [50, 50, 1400, 500]);

for i = startIdx:length(images)
    stats.totalProcessed = stats.totalProcessed + 1;
    
    fprintf('处理照片 %d/%d: %s\n', i, length(images), imageFiles(i).name);
    
    % 跟踪当前帧
    [pose, numMatches] = vslam.trackFrame(images{i});
    
    fprintf('  匹配点数: %d', numMatches);
    
    if numMatches >= vslam.MinFeatures
        stats.successfulTracks = stats.successfulTracks + 1;
        fprintf(' ✓\n');
        
        % 检查是否应该创建关键帧
        if vslam.checkKeyFrame(images{i})
            fprintf('  → 创建关键帧\n');
            vslam.addKeyFrame(images{i});
            stats.keyFrames = stats.keyFrames + 1;
            
            % 闭环检测
            loopCandidates = vslam.detectLoop(vslam.KeyFrameCount);
            if ~isempty(loopCandidates)
                fprintf('  🔄 检测到闭环! (关键帧 %d <-> %d)\n', ...
                    vslam.KeyFrameCount, loopCandidates(1));
                vslam.correctDrift(vslam.KeyFrameCount, loopCandidates(1));
                stats.loopsDetected = stats.loopsDetected + 1;
            end
        end
    else
        stats.failedTracks = stats.failedTracks + 1;
        fprintf(' ❌ 跟踪失败\n');
    end
    
    % 更新可视化
    figure(hFig);
    
    % 显示当前照片
    subplot(1, 3, 1);
    imshow(images{i});
    title(sprintf('照片 %d/%d: %s', i, length(images), imageFiles(i).name), ...
        'Interpreter', 'none');
    
    % 显示轨迹
    subplot(1, 3, 2);
    trajectory = vslam.getTrajectory();
    plot(trajectory(:, 1), trajectory(:, 2), 'b-o', 'LineWidth', 2, ...
        'MarkerSize', 6);
    hold on;
    plot(trajectory(end, 1), trajectory(end, 2), 'ro', ...
        'MarkerSize', 12, 'LineWidth', 2);
    hold off;
    grid on;
    xlabel('X (米)');
    ylabel('Y (米)');
    title('相机轨迹 (俯视图)');
    axis equal;
    
    % 显示统计信息
    subplot(1, 3, 3);
    cla;
    axis off;
    
    text(0.05, 0.95, '📊 处理统计', 'FontSize', 14, 'FontWeight', 'bold');
    text(0.05, 0.85, sprintf('已处理: %d/%d 张', i, length(images)), 'FontSize', 11);
    text(0.05, 0.75, sprintf('成功跟踪: %d 张', stats.successfulTracks), 'FontSize', 11);
    text(0.05, 0.65, sprintf('跟踪失败: %d 张', stats.failedTracks), 'FontSize', 11);
    text(0.05, 0.55, sprintf('关键帧: %d 个', stats.keyFrames), 'FontSize', 11);
    text(0.05, 0.45, sprintf('地图点: %d 个', size(vslam.MapPoints, 1)), 'FontSize', 11);
    text(0.05, 0.35, sprintf('闭环检测: %d 次', stats.loopsDetected), 'FontSize', 11);
    text(0.05, 0.25, sprintf('当前匹配: %d 点', numMatches), 'FontSize', 11);
    
    % 成功率
    successRate = 100 * stats.successfulTracks / stats.totalProcessed;
    text(0.05, 0.15, sprintf('成功率: %.1f%%', successRate), ...
        'FontSize', 11, 'FontWeight', 'bold');
    
    drawnow;
    fprintf('\n');
end

fprintf('✓ 所有照片处理完成!\n\n');

%% 8. 最终统计
fprintf('=== 最终统计 ===\n');
fprintf('总照片数: %d\n', length(images));
fprintf('已处理: %d\n', stats.totalProcessed);
fprintf('成功跟踪: %d (%.1f%%)\n', stats.successfulTracks, ...
    100*stats.successfulTracks/stats.totalProcessed);
fprintf('跟踪失败: %d\n', stats.failedTracks);
fprintf('关键帧: %d\n', stats.keyFrames);
fprintf('地图点: %d\n', size(vslam.MapPoints, 1));
fprintf('闭环检测: %d\n\n', stats.loopsDetected);

%% 9. 创建最终可视化
fprintf('=== 生成可视化结果 ===\n');

% 3D 地图和轨迹
vslam.visualizeMap();

% 多视角轨迹图
figure('Name', 'My_photo - 相机轨迹分析');

trajectory = vslam.getTrajectory();

% 俯视图
subplot(2, 2, 1);
plot(trajectory(:, 1), trajectory(:, 2), 'b-o', ...
    'LineWidth', 2, 'MarkerSize', 6);
grid on;
xlabel('X (米)');
ylabel('Y (米)');
title('俯视图 (XY)');
axis equal;

% 侧视图 XZ
subplot(2, 2, 2);
plot(trajectory(:, 1), trajectory(:, 3), 'r-o', ...
    'LineWidth', 2, 'MarkerSize', 6);
grid on;
xlabel('X (米)');
ylabel('Z (米)');
title('侧视图 (XZ)');
axis equal;

% 侧视图 YZ
subplot(2, 2, 3);
plot(trajectory(:, 2), trajectory(:, 3), 'g-o', ...
    'LineWidth', 2, 'MarkerSize', 6);
grid on;
xlabel('Y (米)');
ylabel('Z (米)');
title('侧视图 (YZ)');
axis equal;

% 路径长度
subplot(2, 2, 4);
if size(trajectory, 1) > 1
    distances = sqrt(sum(diff(trajectory).^2, 2));
    cumDist = [0; cumsum(distances)];
    plot(cumDist, 'k-', 'LineWidth', 2);
    grid on;
    xlabel('关键帧编号');
    ylabel('累计距离 (米)');
    title(sprintf('总路径长度: %.2f 米', cumDist(end)));
else
    text(0.5, 0.5, '需要更多关键帧', 'HorizontalAlignment', 'center');
end

fprintf('✓ 可视化完成\n\n');

%% 10. 保存结果
fprintf('=== 保存结果 ===\n');

% 创建结果文件夹
resultsFolder = fullfile(imageFolder, 'SLAM_Results');
if ~exist(resultsFolder, 'dir')
    mkdir(resultsFolder);
    fprintf('创建结果文件夹: %s\n', resultsFolder);
end

% 保存数据
save(fullfile(resultsFolder, 'map_points.mat'), 'vslam');
save(fullfile(resultsFolder, 'trajectory.mat'), 'trajectory');
save(fullfile(resultsFolder, 'statistics.mat'), 'stats');

% 保存图形
figList = findall(0, 'Type', 'figure');
for i = 1:length(figList)
    figName = get(figList(i), 'Name');
    if ~isempty(figName)
        % 清理文件名
        figName = strrep(figName, ' ', '_');
        figName = strrep(figName, '-', '_');
        saveas(figList(i), fullfile(resultsFolder, [figName '.png']));
    end
end

fprintf('✓ 结果已保存到: %s\n', resultsFolder);

%% 11. 完成
fprintf('\n=== ✅ Visual SLAM 完成! ===\n');
fprintf('\n结果摘要:\n');
fprintf('  📍 地图点数: %d\n', size(vslam.MapPoints, 1));
fprintf('  📷 关键帧数: %d\n', stats.keyFrames);
fprintf('  📏 相机移动距离: %.2f 米\n', cumDist(end));
fprintf('  ✓ 成功率: %.1f%%\n', 100*stats.successfulTracks/stats.totalProcessed);
fprintf('\n结果已保存在: %s\n', resultsFolder);
fprintf('\n您可以使用以下命令查看数据:\n');
fprintf('  vslam.MapPoints        - 3D地图点\n');
fprintf('  vslam.getTrajectory()  - 相机轨迹\n');
fprintf('  vslam.KeyFrames        - 关键帧信息\n');
# Visual SLAM Implementation in MATLAB

## 概述

这是一个完整的基于特征的视觉SLAM(Simultaneous Localization and Mapping)系统的MATLAB实现。该系统能够:
- 从单目摄像头图像序列构建3D地图
- 实时跟踪相机位置和姿态
- 检测闭环并校正漂移
- 可视化相机轨迹和3D地图点

## 系统要求

- MATLAB R2019b或更高版本
- Computer Vision Toolbox
- Image Processing Toolbox

## 文件说明

### 核心文件
- **VisualSLAM.m** - Visual SLAM主类,包含完整的SLAM流程
- **example_visual_slam.m** - 基础示例脚本,演示如何使用合成数据
- **example_real_data.m** - 实际数据示例,支持图像序列、视频或摄像头输入

## 功能特性

### 1. 地图初始化 (Map Initialization)
- 使用前两帧图像初始化3D地图
- SURF特征检测和匹配
- 本质矩阵估计
- 三角测量重建3D点

### 2. 特征跟踪 (Feature Tracking)
- 在新帧中跟踪已知地图点
- 使用PnP算法估计相机位姿
- RANSAC鲁棒性估计

### 3. 局部建图 (Local Mapping)
- 关键帧选择策略
- 新3D点的创建
- 局部光束法平差优化
- 共视图维护

### 4. 闭环检测 (Loop Detection)
- 基于特征匹配的闭环检测
- 与历史关键帧的相似度计算
- 自动闭环候选识别

### 5. 漂移校正 (Drift Correction)
- 姿态图优化
- 闭环约束的分布式应用
- 全局一致性优化

## 使用方法

### 快速开始

```matlab
% 1. 定义相机参数
focalLength = [800, 800];
principalPoint = [320, 240];
imageSize = [480, 640];
intrinsics = cameraIntrinsics(focalLength, principalPoint, imageSize);

% 2. 创建Visual SLAM对象
vslam = VisualSLAM(intrinsics);

% 3. 初始化地图
success = vslam.initializeMap(image1, image2);

% 4. 处理后续帧
for i = 3:numImages
    % 跟踪特征
    [pose, numMatches] = vslam.trackFrame(images{i});
    
    % 检查是否为关键帧
    if vslam.checkKeyFrame(images{i})
        vslam.addKeyFrame(images{i});
        
        % 检测闭环
        loopCandidates = vslam.detectLoop(vslam.KeyFrameCount);
        
        % 校正漂移
        if ~isempty(loopCandidates)
            vslam.correctDrift(vslam.KeyFrameCount, loopCandidates(1));
        end
    end
end

% 5. 可视化结果
vslam.visualizeMap();
trajectory = vslam.getTrajectory();
```

### 详细示例

#### 示例1: 使用合成数据

```matlab
% 运行基础示例
example_visual_slam
```

这个脚本会:
1. 生成合成的3D场景和相机轨迹
2. 创建模拟图像序列
3. 运行完整的Visual SLAM流程
4. 显示3D地图和轨迹

#### 示例2: 使用真实图像序列

```matlab
% 修改example_real_data.m中的图像文件夹路径
imageFolder = 'path/to/your/images';

% 运行脚本
example_real_data
```

#### 示例3: 使用摄像头实时处理

```matlab
% 在example_real_data.m中设置
dataSource = 2;  % 使用摄像头

% 运行脚本
example_real_data
```

## 参数配置

Visual SLAM对象支持以下可配置参数:

```matlab
vslam = VisualSLAM(intrinsics, ...
    'MinFeatures', 100, ...           % 跟踪所需的最小特征数
    'MaxReprojError', 4.0, ...        % 最大重投影误差(像素)
    'MinParallax', 1.0, ...           % 最小视差角(度)
    'KeyFrameThreshold', 0.7, ...     % 关键帧选择阈值
    'LoopScoreThreshold', 0.75);      % 闭环检测阈值
```

### 参数说明

- **MinFeatures**: 成功跟踪所需的最小特征点数量
- **MaxReprojError**: RANSAC中允许的最大重投影误差
- **MinParallax**: 三角测量时的最小视差角度
- **KeyFrameThreshold**: 特征匹配率低于此值时创建新关键帧
- **LoopScoreThreshold**: 特征匹配分数超过此值时检测到闭环

## API 参考

### VisualSLAM 类

#### 构造函数
```matlab
obj = VisualSLAM(cameraParams, varargin)
```

#### 主要方法

**initializeMap(image1, image2)**
- 使用前两帧初始化地图
- 返回: success (boolean)

**trackFrame(image)**
- 跟踪新帧中的特征
- 返回: [pose, numMatches]
  - pose: 4x4相机位姿矩阵
  - numMatches: 匹配特征数量

**checkKeyFrame(image)**
- 检查当前帧是否应该成为关键帧
- 返回: isKeyFrame (boolean)

**addKeyFrame(image)**
- 添加新关键帧并更新局部地图

**detectLoop(kfID)**
- 检测闭环候选
- 返回: loopCandidates (关键帧ID数组)

**correctDrift(currentKFID, loopKFID)**
- 使用闭环约束校正漂移

**getTrajectory()**
- 获取相机轨迹
- 返回: Nx3矩阵(相机位置)

**visualizeMap()**
- 可视化3D地图和相机轨迹

### 属性

- **MapPoints**: Nx3矩阵,包含所有3D地图点
- **KeyFrames**: 关键帧结构数组
- **CovisibilityGraph**: 共视图邻接矩阵
- **CurrentPose**: 当前相机位姿(4x4矩阵)

## 典型工作流程

```
1. 地图初始化
   ├─ 检测SURF特征
   ├─ 特征匹配
   ├─ 估计本质矩阵
   ├─ 恢复相对位姿
   └─ 三角测量3D点

2. 对于每一帧:
   ├─ 特征跟踪
   │  ├─ 检测特征
   │  ├─ 与地图点匹配
   │  └─ PnP位姿估计
   │
   ├─ 关键帧决策
   │  └─ 如果是关键帧:
   │     ├─ 添加关键帧
   │     ├─ 更新共视图
   │     ├─ 局部光束法平差
   │     └─ 闭环检测
   │        └─ 如果检测到闭环:
   │           └─ 姿态图优化
   └─ 继续下一帧
```

## 可视化输出

系统提供多种可视化选项:

1. **3D地图视图**: 显示3D点云和相机轨迹
2. **轨迹视图**: 从不同角度显示相机运动
3. **共视图**: 显示关键帧之间的连接
4. **统计信息**: 显示处理进度和性能指标

## 性能考虑

### 优化建议

1. **图像分辨率**: 较低分辨率可提高处理速度
2. **特征数量**: 减少MinFeatures可提高鲁棒性但降低速度
3. **关键帧频率**: 提高KeyFrameThreshold减少关键帧数量
4. **闭环检测**: 对于长序列,定期检测而非每帧检测

### 典型性能

- 640x480图像: ~2-5 FPS (MATLAB)
- 内存使用: ~100-500 MB (取决于地图大小)
- 适用场景: 室内/室外导航,AR应用

## 限制和已知问题

1. **纯旋转运动**: 系统难以处理纯旋转,需要平移运动
2. **纹理缺失**: 在低纹理环境中特征检测可能失败
3. **快速运动**: 相机运动过快可能导致跟踪失败
4. **光照变化**: 大的光照变化可能影响特征匹配

## 故障排除

### 问题: 地图初始化失败
**解决方案**:
- 确保前两帧有足够的视差
- 检查图像质量和特征丰富度
- 调整MinFeatures参数

### 问题: 跟踪频繁失败
**解决方案**:
- 降低相机运动速度
- 增加场景纹理
- 调整MaxReprojError参数

### 问题: 没有检测到闭环
**解决方案**:
- 降低LoopScoreThreshold
- 确保重访同一位置时视角相似
- 增加关键帧数量

## 扩展建议

可以扩展此系统以包含:

1. **立体视觉**: 使用双目相机提高深度估计
2. **IMU融合**: 整合惯性测量单元数据
3. **语义信息**: 添加物体检测和识别
4. **密集重建**: 生成密集3D模型
5. **深度学习**: 使用深度特征替代SURF


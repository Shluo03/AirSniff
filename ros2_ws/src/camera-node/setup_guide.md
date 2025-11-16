### Phase 1: Hardware & Jetson Setup (The Prerequisite)

This phase is **not** about ROS, but it's a **must-do** before any software will work.

1.  **Check Your Cable:** The RPi camera has a 15-pin connector. The Jetson Orin NX has a 22-pin connector. You **must** use a **15-to-22-pin adapter cable** to connect them.

2.  **Tell the Jetson to Use the Camera:** By default, the Jetson's camera ports are off. You need to use a built-in tool to turn them on.

      * Open a terminal on your Jetson.
      * Run this command:
        ```bash
        sudo /opt/nvidia/jetson-io/jetson-io.py
        ```
      * A blue menu will pop up. Use your arrow keys to navigate.
      * Go to: `Configure Jetson CSI Connector` -\> Select the port you plugged into (e.g., `CAM0`) -\> Select your camera (e.g., "Raspberry Pi Camera v2") -\> `Save` and `Exit`.
      * **CRITICAL:** The tool will ask you to **reboot**. You must do this.

After rebooting, your Jetson's operating system can now see the camera hardware.

-----

### Phase 2: Create the Camera Node Software

We will use a pre-built ROS node called `gscam`. We use this on a Jetson because it's a simple "wrapper" that lets us run NVIDIA's special, hardware-accelerated GStreamer pipeline. This gives us high-speed video without using much CPU.

#### Step 1: Install the `gscam` Node

In a terminal, install the `gscam` package for ROS 2 Humble:

```bash
sudo apt update
sudo apt install ros-humble-gscam
```

#### Step 2: Create Your "Workspace"

You can't just save files anywhere in ROS. You need to create an organized "workspace" folder for your project.

```bash
# 1. Create a workspace directory
mkdir -p ~/ros2_ws/src

# 2. Go into that directory
cd ~/ros2_ws/src
```

#### Step 3: Create Your "Package"

Inside your workspace, you'll create a "package." This is just a folder that holds all the files for a specific task (like our camera setup).

```bash
# This command automatically creates a package named 'my_camera_pkg'
ros2 pkg create --build-type ament_cmake my_camera_pkg
```

#### Step 4: Create the "Launch File"

A "launch file" is a script that tells ROS *how* to start your node with the correct settings. This is where we'll put that special NVIDIA pipeline.

1.  Create a `launch` folder inside your new package:

    ```bash
    mkdir -p ~/ros2_ws/src/my_camera_pkg/launch
    ```

2.  Create a new, blank launch file using a text editor:

    ```bash
    gedit ~/ros2_ws/src/my_camera_pkg/launch/camera.launch.py
    ```

3.  **Copy and paste the entire Python code below** into the text editor. This is your launch file.

<!-- end list -->

```python
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    
    # This is the GStreamer pipeline.
    # It tells the Jetson how to get video from the hardware
    # using NVIDIA's special 'nvarguscamerasrc' driver.
    gstreamer_pipeline = (
        "nvarguscamerasrc sensor-id=0 ! "
        "video/x-raw(memory:NVMM), width=1280, height=720, framerate=30/1 ! "
        "nvvidconv flip-method=0 ! "
        "video/x-raw, format=BGRx ! "
        "videoconvert"
    )

    # This is the ROS 2 node that we are starting.
    # We're using the 'gscam_node' that we installed in Step 1.
    return LaunchDescription([
        Node(
            package="gscam",
            executable="gscam_node",
            parameters=[
                {"gscam_config": gstreamer_pipeline},
                {"frame_id": "camera_link"},
                {"camera_name": "default"},
                {"use_camera_info_url": True},
                {"camera_info_url": "package://my_camera_pkg/config/camera.yaml"},
            ],
            # This renames the output "pipe" to what we want
            remappings=[
                ("image_raw", "/camera/image_raw"),
            ]
        )
    ])
```

4.  **Save** the file and **close** the text editor.

*We're almost done, but you'll notice the code points to a file `config/camera.yaml`. That file is for your *calibration* (Phase 3 of the main plan). For now, the node will just warn us that it's missing, but it will still work.*

-----

### Phase 3: Run and Verify Your Node

Now we'll "build" our workspace so ROS can find our new package, and then we'll run it.

#### Step 1: Build Your Workspace

Go to the root of your workspace and run `colcon build`. This "compiles" your packages.

```bash
cd ~/ros2_ws
colcon build
```

#### Step 2: Source Your Workspace

After building, you need to "source" the setup file. This tells your current terminal to "refresh its memory" and learn about your new package. **You must do this in every new terminal you open.**

```bash
source ~/ros2_ws/install/setup.bash
```

#### Step 3: Launch the Camera Node\!

You're now ready to run the launch file you created.

```bash
ros2 launch my_camera_pkg camera.launch.py
```

Your terminal will show a lot of text. If there are no major errors, your camera node is **running**\! It is now capturing images and publishing them to the `/camera/image_raw` topic.

-----

### Phase 4: See Your Camera Feed

How do you know it's working? You'll use two built-in ROS tools in **two new terminals**.

**Open a new terminal (Terminal 2):**

  * Remember to source your workspace\!
    ```bash
    source ~/ros2_ws/install/setup.bash
    ```
  * Use `ros2 topic hz` to check the "heartbeat" of your camera pipe.
    ```bash
    ros2 topic hz /camera/image_raw
    ```
  * You should see this:
    ```
    average rate: 30.000 Hz
    ```
    This means it's successfully publishing 30 images per second.

**Open another new terminal (Terminal 3):**

  * Source your workspace:
    ```bash
    source ~/ros2_ws/install/setup.bash
    ```
  * Install the ROS image viewer:
    ```bash
    sudo apt install ros-humble-rqt-image-view
    ```
  * Run the image viewer:
    ```bash
    rqt_image_view
    ```
  * A window will pop up. Click the drop-down menu at the top and select `/camera/image_raw`.

You should now see the live video feed from your Raspberry Pi camera\! You have successfully created your first ROS node.
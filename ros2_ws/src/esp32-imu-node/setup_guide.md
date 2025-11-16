To set up esp32 as IMU node (source code in repo)
Steps to Compile and Flash
This process uses the standard ESP-IDF command-line tools.
Step 1: Set up your ESP-IDF Project Open a terminal and set up your ESP-IDF environment.
    
    Bash
    # 1. Source your ESP-IDF environment (you already know this step)
    . $IDF_PATH/export.sh

    # 2. Create a new project
    idf.py create-project ros_imu_node
    cd ros_imu_node

Step 2: Add the micro-ROS Component You need to add the micro_ros_espidf_component to your new project.
    
    Bash
    # 3. Create a 'components' directory
    mkdir components

    # 4. Clone the correct micro-ROS branch (humble for ROS 2 Humble)
    git clone -b humble https://github.com/micro-ROS/micro_ros_espidf_component.git components/micro_ros_espidf_component

Step 3: Configure the Project for micro-ROS This is the most important new step. You must tell ESP-IDF to use micro-ROS over USB serial.
    Bash
    # 5. Open the project configuration menu
    idf.py menuconfig

In the text-based menu, navigate to: Component config -> micro-ROS Settings ->
- Transport: Press Enter and select UART.
- UART peripheral: Select the UART port (e.g., UART 0).
- Baudrate: Set this to a high value, like 921600 or 115200.

Save and Exit the menuconfig.
Step 4: Replace main.c and Build Replace the default main/main.c file in your new project with the complete code example provided above.
Bash
    # 6. (Copy/paste the code above into main/main.c)

    # 7. Build the project
    idf.py build

Step 5: Flash to the ESP32 Connect your ESP32 to the Jetson Orin via USB.
Bash
    # 8. Flash the new firmware (replace /dev/ttyUSB0 with your port)
    idf.py -p /dev/ttyUSB0 flash

Final Step: Run on Jetson
Your ESP32 is now flashed and running. When you plug it into the Jetson, it will be publishing IMU data over its USB serial port. The final step is to run the micro-ROS agent on the Jetson to see the data.

    Bash
    # On your Jetson Orin terminal:

    # 1. Install the agent (if you haven't)
    sudo apt install ros-humble-micro-ros-agent

    # 2. Run the agent (use the same port and baudrate from Step 3)
    ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 921600

    # 3. In a *new* Jetson terminal, check for your topic!
    ros2 topic hz /imu/data_raw

    # You should see:
    # average rate: 200.000 Hz

You now have a 200Hz IMU publisher.

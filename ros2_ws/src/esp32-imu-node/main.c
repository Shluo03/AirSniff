#include <stdio.h>
#include <unistd.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/i2c.h"

// --- micro-ROS Headers ---
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <sensor_msgs/msg/imu.h>
#include <rmw_microros/rmw_microros.h>
#include "esp_timer.h"

// --- I2C/IMU Defines (from your code) ---
#define I2C_MASTER_NUM I2C_NUM_0
#define I2C_MASTER_SCL_IO 8       // GPIO number for I2C clock
#define I2C_MASTER_SDA_IO 10      // GPIO number for I2C data
#define I2C_MASTER_FREQ_HZ 100000
#define ICM_ADDR 0x68             // I2C address of the ICM-42670-P sensor

// --- VIO-Specific Defines ---
#define ROS_NODE_TAG "ros_imu_node"
#define IMU_PUB_RATE_MS 5         // 5ms = 200Hz (Ideal for VIO)
#define ACCEL_RANGE_G 16.0f
#define GYRO_RANGE_DPS 2000.0f
#define G_TO_M_S2 9.80665f
#define DPS_TO_RAD_S 0.0174532925f

// Sensitivity / Conversion Factors
// 16-bit sensor: 32768.0
// Accel: 32768.0 / 16.0 = 2048.0 LSB/g (Matches your old code!)
// Gyro:  32768.0 / 2000.0 = 16.384 LSB/dps
const float ACCEL_CONV = (G_TO_M_S2 / (32768.0f / ACCEL_RANGE_G));
const float GYRO_CONV = (DPS_TO_RAD_S / (32768.0f / GYRO_RANGE_DPS));

// --- ROS Globals ---
rcl_publisher_t imu_publisher;
sensor_msgs__msg__Imu imu_msg;
rcl_timer_t timer;
rcl_node_t node;
rcl_allocator_t allocator;
rclc_support_t support;
rclc_executor_t executor;

// --- Your I2C Functions (Copied Directly) ---

static esp_err_t initialize_i2c_master() {
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_MASTER_SDA_IO,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_io_num = I2C_MASTER_SCL_IO,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ,
    };
    esp_err_t config_status = i2c_param_config(I2C_MASTER_NUM, &conf);
    if (config_status != ESP_OK) {
        ESP_LOGE(ROS_NODE_TAG, "Failed to configure I2C: %s", esp_err_to_name(config_status));
        return config_status;
    }
    esp_err_t driver_status = i2c_driver_install(I2C_MASTER_NUM, conf.mode, 0, 0, 0);
    ESP_LOGI(ROS_NODE_TAG, "I2C driver installation %s", driver_status == ESP_OK ? "succeeded" : "failed");
    return driver_status;
}

static void write_byte_to_register(uint8_t reg, uint8_t data) {
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (ICM_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg, true);
    i2c_master_write_byte(cmd, data, true);
    i2c_master_stop(cmd);
    i2c_master_cmd_begin(I2C_MASTER_NUM, cmd, pdMS_TO_TICKS(1000));
    i2c_cmd_link_delete(cmd);
}

static uint8_t read_byte_from_register(uint8_t reg) {
    uint8_t data;
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (ICM_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg, true);
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (ICM_ADDR << 1) | I2C_MASTER_READ, true);
    i2c_master_read_byte(cmd, &data, I2C_MASTER_LAST_NACK);
    i2c_master_stop(cmd);
    i2c_master_cmd_begin(I2C_MASTER_NUM, cmd, pdMS_TO_TICKS(1000));
    i2c_cmd_link_delete(cmd);
    return data;
}

// --- ROS Timer Callback (Replaces your ble_mouse_task) ---

void imu_timer_callback(rcl_timer_t * timer, int64_t last_call_time)
{
    if (timer != NULL) {
        // --- Read all 6 axes of IMU data ---
        // (Register addresses are for ICM-42670-P)
        int16_t acc_x_raw = (read_byte_from_register(0x0B) << 8) | read_byte_from_register(0x0C);
        int16_t acc_y_raw = (read_byte_from_register(0x0D) << 8) | read_byte_from_register(0x0E);
        int16_t acc_z_raw = (read_byte_from_register(0x0F) << 8) | read_byte_from_register(0x10);
        
        int16_t gyro_x_raw = (read_byte_from_register(0x11) << 8) | read_byte_from_register(0x12);
        int16_t gyro_y_raw = (read_byte_from_register(0x13) << 8) | read_byte_from_register(0x14);
        int16_t gyro_z_raw = (read_byte_from_register(0x15) << 8) | read_byte_from_register(0x16);

        // --- Fill the ROS message ---
        // Get current time
        struct timespec ts;
        clock_gettime(CLOCK_REALTIME, &ts);
        imu_msg.header.stamp.sec = ts.tv_sec;
        imu_msg.header.stamp.nanosec = ts.tv_nsec;
        imu_msg.header.frame_id = "imu_link"; // Default frame ID

        // Convert raw data to SI units (m/s^2 and rad/s)
        imu_msg.linear_acceleration.x = (double)acc_x_raw * ACCEL_CONV;
        imu_msg.linear_acceleration.y = (double)acc_y_raw * ACCEL_CONV;
        imu_msg.linear_acceleration.z = (double)acc_z_raw * ACCEL_CONV;

        imu_msg.angular_velocity.x = (double)gyro_x_raw * GYRO_CONV;
        imu_msg.angular_velocity.y = (double)gyro_y_raw * GYRO_CONV;
        imu_msg.angular_velocity.z = (double)gyro_z_raw * GYRO_CONV;

        // (We leave covariance as 0, as we haven't calibrated it)

        // --- Publish the message ---
        rcl_publish(&imu_publisher, &imu_msg, NULL);
    }
}

// --- Main App (Replaces your app_main) ---

void app_main(void)
{
    // 1. Initialize NVS (Good practice, retained from your code)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // 2. Initialize I2C (Your function)
    ESP_ERROR_CHECK(initialize_i2c_master());

    // 3. Initialize IMU (Your settings)
    ESP_LOGI(ROS_NODE_TAG, "Initializing IMU sensor...");
    write_byte_to_register(0x1F, 0b00011111); // Your init value
    write_byte_to_register(0x21, 0b00011111); // Your config value
    ESP_LOGI(ROS_NODE_TAG, "IMU initialization complete.");

    // 4. Initialize micro-ROS
    ESP_LOGI(ROS_NODE_TAG, "Initializing micro-ROS...");
    allocator = rcl_get_default_allocator();
    rclc_support_init(&support, 0, NULL, &allocator);

    // 5. Create micro-ROS Node
    rclc_node_init_default(&node, "esp32_imu_node", "", &support);

    // 6. Create micro-ROS Publisher
    rclc_publisher_init_default(
        &imu_publisher,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, Imu),
        "imu/data_raw" // This is the topic name the Jetson will listen to
    );

    // 7. Create micro-ROS Timer (triggers callback at 200Hz)
    rclc_timer_init_default(
        &timer,
        &support,
        RCL_MS_TO_NS(IMU_PUB_RATE_MS),
        imu_timer_callback
    );

    // 8. Create Executor
    rclc_executor_init(&executor, &support.context, 1, &allocator);
    rclc_executor_add_timer(&executor, &timer);

    ESP_LOGI(ROS_NODE_TAG, "micro-ROS node created. Spinning...");

    // 9. Run the Executor
    while(1) {
        rclc_executor_spin_some(&executor, RCL_MS_TO_NS(1));
        usleep(1000); // 1ms sleep
    }

    // (Cleanup code, though this loop runs forever)
    rcl_publisher_fini(&imu_publisher, &node);
    rcl_node_fini(&node);
    rclc_support_fini(&support);
}
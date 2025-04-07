# Keychain - Klefki Device Monitoring and Management Script

This script checks the status of devices in the Klefki system and resolves issues related to unauthorized workers by sending a restart request to a specified endpoint. It also integrates with Discord for real-time notifications and error reporting.

## Features

- **Device Monitoring**: Checks the device status (workers authorized).
- **Device Issue Resolution**: Triggers a restart for devices with `0` authorized workers.
- **Error Reporting**: Sends real-time error messages and device issue notifications to Discord.
- **Session Cookie Management**: Handles session cookie expiration issues and sends alerts if the session is invalid or expired.

## Requirements

- Python 3.x
- Klefki Session Cookie

You can install the required libraries using `pip`:

```bash
pip install -r .\requrements.txt
```

Login to Klefki and use browser console to extract your Session Cookie value. Use this in the `config.yaml`. This resets when Klefki is restarted, a dedicated error message is made to tag you in order to update this.

## Configuration

Create a `config.yaml` (or use the example) file in the same directory as the script. The configuration file should include the following values:

```yaml
logging: "debug" # Set log level to "debug" or "info"
session_cookie: "" # Obtain the session cookie from the browser after logging into Klefki. Must be updated periodically.
discord_id: "" # Discord ID used in the Klefki API.
discord_webhook: "" # Discord webhook URL used to send updates and error messages.
auth:
  user: "" # Optional: Username for Rotom authentication.
  pass: "" # Optional: Password for Rotom authentication.
urls:
  status: "https://api.klefki.sylvie.fyi/api/v1/devices/" # Klefki status API endpoint URL.
  rotom: "" # Rotom API endpoint URL, including port (for triggering device restarts).
devices: 
  device1: 5   # Example: Device name with expected worker count.
  Device 2: 10
  device3: 0  # Devices with 0 workers will be skipped. Used in deviceless environments.
```

### Fields:

- **logging**: Set to `debug` for detailed logs or `info` for less verbosity.
- **session_cookie**: The session cookie from your Klefki account. You need to obtain this manually after logging into Klefki.
- **discord_id**: Your Discord ID for notifications.
- **discord_webhook**: Webhook URL to send notifications to Discord.
- **auth**: Optional authentication parameters for Rotom API (`user` and `pass`).
- **urls**:
  - `status`: The Klefki API URL to fetch device statuses.
  - `rotom`: The Rotom URL to trigger device restarts, needs port. 
- **devices**: A list of devices, with the expected number of workers. Devices with `0` authed workers when they have a higher value will trigger a restart request.

## Usage

1. **Set Up Configuration**: Ensure that your `config.yaml` is set up with the correct values.
2. **Run the Script**: Execute the script by running the following command in your terminal:
   
   ```bash
   python monitor.py
   ```

3. **Monitor Logs**: The script will output logs to the console based on the configured logging level (`debug` or `info`). It will also send alerts to Discord for specific events:
   - When a device with `0` workers is detected and a restart is triggered.
   - When a device is not found in the Klefki status API.
   - When there is an error contacting the Klefki API or sending a restart request.

4. **Automatic Recheck**: The script will automatically check the devices' statuses every 5 minutes and attempt to resolve any detected issues.

## Example Outputs

### Discord Notifications:

- **Klefki connection error**:
  ```
  <@discord_id> Klefki connection error - 400 - {"error":"session not found"}
  ```

- **Session Cookie Expiry Alert**:
  ```
  <@discord_id> Klefki connection error - Session Key Invalid. May need updating!
  ```

- **Device Restart Triggered**:
  ```
  Restart triggered on device1 - 0 Workers Detected.
  ```

- **Device Not Found**:
  ```
  ⚠️  Warning: 'device1' not found in status data.
  ```

## Troubleshooting

- **Session Expiry**: If you encounter the error `session not found`, you will need to update the session cookie in the `config.yaml` file.
- **Device Not Found**: If a device in your `devices` list is not found in the Klefki API, ensure that the device name is spelled correctly, and the device is correctly registered in Klefki.

## License

This project is open-source and available under the MIT License. See the [LICENSE](LICENSE) file for more details.

---

Let me know if you need any more adjustments or additions!
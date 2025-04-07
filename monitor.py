import time
import requests
import yaml
import json

def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def get_device_status(config):
    device_count = len(config["devices"])
    limit = device_count + 1

    base_url = config["urls"]["status"]
    discord_id = config.get("discord_id")
    full_url = f"{base_url}?after=0&limit={limit}&user={discord_id}"

    headers = {"Cookie": f"session={config['session_cookie']}"}

    try:
        response = requests.get(full_url, headers=headers)
        if response.status_code != 200:
            error_message = (f"❌ Status endpoint returned {response.status_code}: {response.text}")
            
            if response.status_code == 400 and "session not found" in response.text.lower():
                session_error_message = f"<@{config['discord_id']}> Klefki connection error - Session Key Invalid. May need updating!"
                send_discord_message(config, session_error_message)
            else:
                discord_message = (f"<@{config['discord_id']}> Klefki connection error - {response.status_code} - {response.text}")
                print(error_message)
                send_discord_message(config, discord_message)  # Send to Discord
            
            response.raise_for_status()

        json_data = response.json()

        # Debug: Show devices fetched
        print("Raw device data from status endpoint:")
        for device in json_data.get("devices", []):
            print(f"- {device.get('device_name')}")

        return json_data

    except requests.RequestException as e:
        error_message = f"🔴 Error contacting status endpoint: {e}"
        print(error_message)
        raise

def resolve_device_issue(device, config):
    base_url = config["urls"]["resolve"]
    restart_url = f"{base_url}/api/device/{device}/action/restart"

    # Only add auth if user/pass are not empty
    auth = None
    user = config.get("auth", {}).get("user")
    password = config.get("auth", {}).get("pass")
    if user and password:
        auth = (user, password)

    try:
        response = requests.post(
            restart_url,
            auth=auth
        )
        if response.status_code != 200:
            error_message = f"❌ Restart failed for {device} (status {response.status_code}): {response.text}"
            discord_message= f"<@{config['discord_id']}> {device} failed to trigger restart - {response.status_code} - {response.text}"
            print(error_message)
            send_discord_message(config, discord_message)  # Send to Discord
        else:
            success_message = f"Restart triggered on {device} - 0 Workers Detected."
            print(success_message)
            send_discord_message(config, success_message)  # Send to Discord

        response.raise_for_status()
    except requests.RequestException as e:
        error_message = f"🔴 Error sending restart for {device}: {e}"
        print(error_message)
        raise

def check_and_resolve(config):
    print("Checking device statuses...")
    status_data = get_device_status(config)
    device_list = status_data.get("devices", [])

    device_map = {
        dev.get("device_name", "").strip().lower(): dev
        for dev in device_list
    }

    for device, expected_workers in config["devices"].items():
        if expected_workers <= 0:
            print(f"Skipping {device}: expected workers set to 0.")
            continue

        normalized_device = device.strip().lower()

        if normalized_device not in device_map:
            warning_message = f"⚠️  Warning: '{device}' not found in status data."
            print(warning_message)
            send_discord_message(config, warning_message)  # Send to Discord
            continue

        device_status = device_map[normalized_device]
        workers_authorized = device_status.get("workers_authorized", -1)
        print(f"{device}: {workers_authorized} workers authorized")

        if workers_authorized == 0:
            print(f"{device} has 0 authorized workers. Attempting resolution...")
            resolve_device_issue(device, config)

            time.sleep(60)
            retry_data = get_device_status(config).get("devices", [])
            retry_map = {
                dev.get("device_name", "").strip().lower(): dev
                for dev in retry_data
            }
            retry_status = retry_map.get(normalized_device, {})
            retry_workers = retry_status.get("workers_authorized", -1)
            print(f"{device} retry: {retry_workers} workers authorized")

def send_discord_message(config, message):
    webhook_url = config.get("discord_webhook")
    if webhook_url:
        payload = {
            "content": message
        }
        headers = {
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()  # Ensure a 200 response, otherwise an exception is raised
        except requests.RequestException as e:
            print(f"🔴 Error sending Discord message: {e}")

def main():
    config = load_config()

    while True:
        try:
            check_and_resolve(config)
        except Exception as e:
            print(f"Error during check: {e}")
        print("Waiting 5 minutes for next check...\n")
        time.sleep(300)

if __name__ == "__main__":
    main()

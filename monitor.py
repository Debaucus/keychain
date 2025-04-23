import time
import requests
import yaml
import json
import subprocess

failure_counters = {}

def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def get_device_status(config):
    limit = config["total_devices"]

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

def restart_docker_container(device_name, config):
    container_name = config.get("docker_containers", {}).get(device_name)
    if not container_name:
        print(f"❌ No container mapped for {device_name}")
        return

    container_path = config.get("docker_container_path")
    if not container_path:
        print("❌ Docker container path not set in config.")
        return

    try:
        subprocess.run(
            ["docker", "container", "restart", container_name],
            cwd=container_path,
            check=True
        )
        msg = f"<@{config['discord_id']}> Restarted Docker container `{container_name}` for device `{device_name}` after 5 failures."
        print(msg)
        send_discord_message(config, msg)
    except subprocess.CalledProcessError as e:
        error_msg = f"🔴 Docker restart failed for {container_name}: {e}"
        print(error_msg)
        send_discord_message(config, error_msg)


def resolve_device_issue(device, config):
    base_url = config["urls"]["rotom"]
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
            failure_counters[normalized_device] = failure_counters.get(normalized_device, 0) + 1
            warning_message = f"❌ {device} not found in status data. Failure count: {failure_counters[normalized_device]}/5"
            print(warning_message)
            send_discord_message(config, warning_message)  # Send to Discord

            if failure_counters[normalized_device] >= 5:
                print(f"🔥 Restarting container for {device} due to repeated absence from status data.")
                restart_docker_container(device, config)
                failure_counters[normalized_device] = 0  # Reset after restart
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

            # Track failure regardless of retry result
            failure_counters[normalized_device] = failure_counters.get(normalized_device, 0) + 1
            
            if retry_workers == 0:
                print(f"❌ {device} still has 0 workers. Failure count: {failure_counters[normalized_device]}/5")
            else:
                print(f"✅ {device} recovered after restart. Workers: {retry_workers}")
                failure_counters[normalized_device] = 0
            
            # Restart container if threshold hit
            if failure_counters[normalized_device] >= 5:
                print(f"🔥 Restarting container for {device}")
                restart_docker_container(device, config)
                failure_counters[normalized_device] = 0  # Reset after restart



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

    send_discord_message(config, "Keychain - Klefki Monitor started.")

    while True:
        try:
            check_and_resolve(config)
        except Exception as e:
            print(f"Error during check: {e}")
        print("Waiting 1 minute for next check...\n")
        time.sleep(60)

if __name__ == "__main__":
    main()

import time
from machine import Pin
import network
import urequests
import ujson
from time import sleep
import machine
import yaml

# Define error codes
ERROR_CODE_WIFI_NOT_CONNECTED = 2
ERROR_CODE_HOME_ASSISTANT_NOT_CONNECTED = 4
ERROR_CODE_KEYBOARD_INTERRUPT = 6
ERROR_CODE_WIFI_NOT_CONFIGURED = 8

# Define the pins for output
led_on_board: Pin = Pin("LED", Pin.OUT)
led_green: Pin = Pin(13, Pin.OUT)
led_yellow: Pin = Pin(14, Pin.OUT)
led_red: Pin = Pin(15, Pin.OUT)
buzzer: Pin = Pin(16, Pin.OUT)

# Define the pins for input
sensor_bottom: Pin = Pin(12, Pin.IN, pull=Pin.PULL_UP)
sensor_tilt_2: Pin = Pin(11, Pin.IN, pull=Pin.PULL_UP)
sensor_lid: Pin = Pin(10, Pin.IN, pull=Pin.PULL_UP)
sensor_reset: Pin = Pin(9, Pin.IN, pull=Pin.PULL_UP)

# Potentially useful globals
has_mail_been_delivered: bool = False
previous_has_mail_been_delivered: bool = False
lid_open: bool = False
bottom_sensor_active: bool = False
tilt_sensor_active: bool = False
reset_sensor_active: bool = False


def load_settings(file_name: str) -> dict:
    with open(file_name) as file:
        _settings = yaml.safe_load(file)
        return _settings


settings_file_name: str = 'settings.yaml'
settings: dict = load_settings(settings_file_name)

# set the SSID and password of your WiFi along with other useful settings
ssid: str = settings.get('wifi_ssid', 'ssid_not_set')
password: str = settings.get('wifi_password', 'wifi_password_not_set')
home_assistant_url: str = settings.get('home_assistant_url', 'http://homeassistant.local:8123/')
home_assistant_token: str = settings.get('home_assistant_bearer_token', 'not_set')
home_assistant_unique_id: str = settings.get('home_assistant_unique_id', 'net_set')
home_assistant_entity_id: str = settings.get('home_assistant_entity_id', 'not_set')
consecutive_tilt_sensor_active_needed_to_trigger: int = settings.get('consecutive_tilt_sensor_active_needed_to_trigger',
                                                                     10)
consecutive_lid_open_needed_to_trigger: int = settings.get('consecutive_lid_open_needed_to_trigger', 10)
consecutive_bottom_sensor_active_needed_to_trigger: int = settings.get(
    'consecutive_bottom_sensor_active_needed_to_trigger', 10)
max_wifi_connect_attempts_before_resetting_device: int = settings.get(
    'max_wifi_connect_attempts_before_resetting_device', 10)
"""
assert ssid != 'your_ssid', f"Please set your WiFi SSID in {settings_file_name}" # noqa
assert password != 'your_password', f"Please set your WiFi password in {settings_file_name}"  # noqa
assert home_assistant_token != 'your_token', f"Please set your Home Assistant Bearer Token in {settings_file_name}" # noqa
assert home_assistant_unique_id != 'net_set', f"Please set your Home Assistant Unique ID in {settings_file_name}" # noqa
assert home_assistant_entity_id != 'not_set', f"Please set your Home Assistant Entity ID in {settings_file_name}" # noqa
"""


def set_putput_pins(to_low: bool = True, to_high: bool = False) -> None:
    for pin in [led_on_board, led_green, led_yellow, led_red, buzzer]:
        if to_low:
            pin.low()
        elif to_high:
            pin.high()


def flash_led(led: Pin, flashes: int = 5, flash_duration: float = 0.1) -> None:
    print(f'flashing led: {flashes} times for {flash_duration} seconds each')
    for i in range(flashes):
        led.high()
        time.sleep(flash_duration)
        led.low()
    print('flashing led: done')


def slow_flash_led(led: Pin, flashes: int = 5, flash_duration: float = 1) -> None:
    flash_led(led, flashes, flash_duration)


def buzz_buzzer(buzzes: int = 5, buzz_duration: float = 0.1) -> None:
    print(f'buzzing the buzzer: {buzzes} times for {buzz_duration} seconds each')
    for i in range(buzzes):
        buzzer.high()
        time.sleep(buzz_duration)
        buzzer.low()
    print('buzzing the buzzer: done')


def cycle_lights(cycles: int = 5) -> None:
    for i in range(cycles):
        print(f'toggling lights: {i}/{cycles}')
        for led in [led_on_board, led_green, led_yellow, led_red]:
            led.toggle()
            sleep(0.1)
        leds = [led_on_board, led_green, led_yellow, led_red]
        leds.reverse()
        for led in leds:
            led.toggle()
            sleep(0.1)
    print('toggling lights: done')


def signal_error(error_code: int = 1) -> None:
    print(f"Signaling error code: {error_code}")
    buzz_buzzer(2)
    flash_led(led_on_board, 5)
    buzz_buzzer(2)
    slow_flash_led(led_on_board, error_code)
    print(f"Signaling error code: {error_code} done")


def connect() -> network.WLAN:
    print(f"Connecting to WiFi: {ssid}")
    if ssid == 'ssid_not_set' or password == 'password_not_set':  # noqa
        signal_error(ERROR_CODE_WIFI_NOT_CONFIGURED)
        raise ValueError(f"Please set your WiFi SSID and password in {settings_file_name}")
    # Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    attempts = 0
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        sleep(1)
        led_on_board.toggle()
        attempts += 1
        if attempts > max_wifi_connect_attempts_before_resetting_device:
            print(
                f"Could not connect to WiFi (after {attempts} attempts), please check your {settings_file_name} file and wifi status")
            signal_error(ERROR_CODE_WIFI_NOT_CONNECTED)
            print("Resetting the device")
            machine.reset()
    print(wlan.ifconfig())
    flash_led(led_on_board, 5)
    led_on_board.high()
    buzz_buzzer(5)
    print(f"Connected to WiFi: {ssid}")
    return wlan


def send_telemetry_to_ha(mail_has_been_delivered: bool) -> None:
    if home_assistant_token == 'not_set':
        print(f"Home Assistant Bearer Token is not set, please set it in {settings_file_name}")
        signal_error(ERROR_CODE_HOME_ASSISTANT_NOT_CONNECTED)
        return None
    print(f"Sending telemetry to Home Assistant: ")
    state = 0
    if mail_has_been_delivered:
        state = 1
    print(f"Sending telemetry to Home Assistant: {state} mail in box")
    data = {
        "state": state,
        "attributes": {
            "device_class": "presence",
            "friendly_name": "Smart Mailbox",
            "unit_of_measurement": "Mail in box",
            "state_class": "measurement",
            "unique_id": home_assistant_unique_id
        }
    }
    headers = {
        "Authorization": f"Bearer {home_assistant_token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    json = ujson.dumps(data).encode('utf-8')
    url = f"{home_assistant_url}api/states/{home_assistant_entity_id}"
    response = urequests.post(url, data=json, headers=headers)
    print(f"Response from Home Assistant: {response.status_code}")
    print(response.text)


def check_if_mail_has_been_delivered(list_of_samples: list) -> bool:
    """
        {'counter': counter,
        'lid_open': lid_open,
        'bottom_sensor_active': bottom_sensor_active,
        'tilt_sensor_active': tilt_sensor_active}
    """
    print(f"Checking if mail has been delivered")
    consecutive_tilt_sensor_active = 0
    consecutive_lid_open = 0
    consecutive_bottom_sensor_active = 0
    previous_sample = None
    for sample in list_of_samples:
        if previous_sample is None:
            previous_sample = sample
            continue
        if previous_sample is not None:
            if sample['tilt_sensor_active'] and previous_sample['tilt_sensor_active']:
                consecutive_tilt_sensor_active += 1
            elif not sample['tilt_sensor_active']:
                consecutive_tilt_sensor_active = 0
            if sample['lid_open'] and previous_sample['lid_open']:
                consecutive_lid_open += 1
            elif not sample['lid_open']:
                consecutive_lid_open = 0
            if sample['bottom_sensor_active'] and previous_sample['bottom_sensor_active']:
                consecutive_bottom_sensor_active += 1
            elif not sample['bottom_sensor_active']:
                consecutive_bottom_sensor_active = 0
            previous_sample = sample
        if (consecutive_tilt_sensor_active > consecutive_tilt_sensor_active_needed_to_trigger
                or consecutive_lid_open > consecutive_lid_open_needed_to_trigger
                or consecutive_bottom_sensor_active > consecutive_bottom_sensor_active_needed_to_trigger):
            print(f"Mail has been delivered")
            return True
    print(f"Mail has not been delivered")
    return False


def main():
    global has_mail_been_delivered, reset_sensor_active, tilt_sensor_active, bottom_sensor_active, lid_open, previous_has_mail_been_delivered
    set_putput_pins(to_low=True)
    cycle_lights()

    try:
        print("Trying to connect to WLAN")
        connect()
        print("Connected to WLAN")
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
        signal_error(ERROR_CODE_KEYBOARD_INTERRUPT)
        machine.reset()
    except ValueError as e:
        print(f"ValueError: {e}")
        led_on_board.high()
        machine.reset()

    counter = 0
    past_50_samples = []
    while True:
        time.sleep(0.5)
        if sensor_lid.value():
            print("Lid is open")
            lid_open = True
            led_yellow.high()
        elif not sensor_lid.value():
            print("Lid is closed")
            lid_open = False
            led_yellow.low()
        if not sensor_bottom.value():
            print("sensor_bottom is active")
            bottom_sensor_active = True
            led_red.high()
        elif sensor_bottom.value():
            print("sensor_bottom is inactive")
            bottom_sensor_active = False
            led_red.low()
        if sensor_tilt_2.value():
            print("sensor_tilt_2 is active")
            tilt_sensor_active = True
            led_green.high()
        elif not sensor_tilt_2.value():
            print("sensor_tilt_2 is inactive")
            tilt_sensor_active = False
            led_green.low()
        if not sensor_reset.value():
            print("sensor_reset is active")
            reset_sensor_active = True
            if has_mail_been_delivered:
                print("#" * 50)
                print("Resetting mail delivery status")
                print("#" * 50)
                has_mail_been_delivered = False
                past_50_samples = []
        elif sensor_reset.value():
            print("sensor_reset is inactive")
            reset_sensor_active = False
        past_50_samples.append({'counter': counter,
                                'lid_open': lid_open,
                                'bottom_sensor_active': bottom_sensor_active,
                                'tilt_sensor_active': tilt_sensor_active,
                                'reset_sensor_active': reset_sensor_active})
        if len(past_50_samples) > 50:
            past_50_samples.pop(0)
        if not has_mail_been_delivered:
            has_mail_been_delivered = check_if_mail_has_been_delivered(past_50_samples)
            if has_mail_been_delivered:
                print("New mail has been delivered")
                print("Sound the buzzer 5x once")
                buzz_buzzer(5)
        if has_mail_been_delivered:
            print("Mail is in the mailbox")
            flash_led(led_on_board, 5)
        if has_mail_been_delivered != previous_has_mail_been_delivered:
            # we have a state change and should update Home Assistant
            send_telemetry_to_ha(has_mail_been_delivered)
        previous_has_mail_been_delivered = has_mail_been_delivered
        print(f"counter: {counter}")
        print(f"sensor_lid.value(): {sensor_lid.value()}")
        print(f"sensor_bottom.value(): {sensor_bottom.value()}")
        print(f"sensor_tilt_2.value(): {sensor_tilt_2.value()}")
        print(f"sensor_reset.value(): {sensor_reset.value()}")
        counter += 1

main()
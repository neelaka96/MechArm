import json
import sys
import threading
import time

from awscrt import mqtt
from awsiot import mqtt_connection_builder
from pymycobot import PI_PORT, PI_BAUD
from pymycobot.genre import Angle
from pymycobot.mycobot import MyCobot

input_endpoint = "a35i7te1fromnx-ats.iot.us-east-1.amazonaws.com"
input_port = 8883
input_cert = "MechArm.cert.pem"
input_key = "MechArm.private.key"
input_ca = "root-CA.crt"
input_clientId = "basicPubSub"
input_proxy_host = None  # Since the input is 'None', you can assign None directly
input_proxy_port = 8080
input_message = "Hello World!"
input_topic = "sdk/test/python"
input_count = 0
input_is_ci = False

received_count = 0
received_all_event = threading.Event()

pickup_at = [-90, 90, -100, -0, 0, -60]
dropoff_at = [90, 90, -100, -0, 0, -60]

global get
get = 0


# Callback when connection is accidentally lost.
def on_connection_interrupted(connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))


# Callback when an interrupted connection is re-established.
def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        print("Session did not persist. Resubscribing to existing topics...")
        resubscribe_future, _ = connection.resubscribe_existing_topics()
        resubscribe_future.add_done_callback(on_resubscribe_complete)


def on_resubscribe_complete(resubscribe_future):
    resubscribe_results = resubscribe_future.result()
    print("Resubscribe results: {}".format(resubscribe_results))

    for topic, qos in resubscribe_results['topics']:
        if qos is None:
            sys.exit("Server rejected resubscribe to topic: {}".format(topic))


# Callback when the subscribed topic receives a message
def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    print("Type", type(payload))
    print(payload)
    print("Received message: '{}'".format(payload))
    decoded_payload = payload.decode('utf-8')
    parsed_payload = json.loads(decoded_payload)
    message = parsed_payload.get("message")
    print(message)
    if message == "run":
        run_mech()
    global received_count
    received_count += 1
    if received_count == input_count:
        received_all_event.set()


# Callback when the connection successfully connects
def on_connection_success(connection, callback_data):
    assert isinstance(callback_data, mqtt.OnConnectionSuccessData)
    print("Connection Successful with return code: {} session present: {}".format(callback_data.return_code,
                                                                                  callback_data.session_present))


# Callback when a connection attempt fails
def on_connection_failure(connection, callback_data):
    assert isinstance(callback_data, mqtt.OnConnectionFailureData)
    print("Connection failed with error code: {}".format(callback_data.error))


# Callback when a connection has been disconnected or shutdown successfully
def on_connection_closed(connection, callback_data):
    print("Connection closed")


def get_pencil(mc):
    mc.send_angle(Angle.J6.value, 30, 100)
    time.sleep(2.5)
    mc.set_gripper_value(30, 100)
    time.sleep(2.5)

    print('pencil in position (y/N)?')
    x = input()
    while not x.lower().startswith('y'):
        if x.lower().startswith('n'):
            raise Exception('Did not pick up pencil')

        print('input y/N')
        x = input()

    mc.set_gripper_value(10, 100)
    time.sleep(2.5)
    mc.send_angle(Angle.J6.value, -60, 100)
    time.sleep(2.5)


def drop_pencil(mc):
    mc.set_gripper_value(100, 100)
    time.sleep(0.5)


def write_on_paper(mc):
    # Define constants to add to x and y values
    x_addition = 0
    y_addition = -10

    # Define writing coordinates (example for a simple line or circle)
    start_position = [90 + x_addition, 85 + y_addition, -90, 0, 0, -60]  # Adjusted for writing start
    writing_path = [
        [90 + x_addition, 85 + y_addition, -90, 0, 0, -55],
        [95 + x_addition, 85 + y_addition, -90, 0, 0, -55],
        [95 + x_addition, 90 + y_addition, -90, 0, 0, -55],
        [80 + x_addition, 90 + y_addition, -90, 0, 0, -55],
        [80 + x_addition, 85 + y_addition, -90, 0, 0, -55],
        [85 + x_addition, 85 + y_addition, -90, 0, 0, -55],
        [85 + x_addition, 90 + y_addition, -90, 0, 0, -55],
        [82 + x_addition, 90 + y_addition, -90, 0, 0, -55],
        [82 + x_addition, 88 + y_addition, -90, 0, 0, -55],
        [82 + x_addition, 92 + y_addition, -90, 0, 0, -55],
        [82 + x_addition, 90 + y_addition, -90, 0, 0, -55],
        [80 + x_addition, 90 + y_addition, -90, 0, 0, -55],
        [80 + x_addition, 85 + y_addition, -90, 0, 0, -55],
        [75 + x_addition, 85 + y_addition, -90, 0, 0, -55],
        [75 + x_addition, 90 + y_addition, -90, 0, 0, -55],
        [70 + x_addition, 90 + y_addition, -90, 0, 0, -55],
        [70 + x_addition, 85 + y_addition, -90, 0, 0, -55]
    ]

    # Move to the start position
    mc.send_angles(start_position, 50)
    time.sleep(2.5)
    print('Starting to write...')

    # Execute writing path
    for position in writing_path:
        mc.send_angles(position, 50)
        time.sleep(1.5)  # Smaller delay during writing moves

    print('Writing completed.')


# Example usage
def do_test(mc):
    global get
    get = 0

    print('going to pickup location')
    mc.send_angles(pickup_at, 50)
    time.sleep(2.5)
    get_pencil(mc)
    get = 1

    print('Writing on paper...')
    write_on_paper(mc)

    print('Waiting for another Message')
    mc.send_angles(dropoff_at, 50)
    time.sleep(2.5)

    # drop_pencil(mc)


def run_mech():
    mc = MyCobot(PI_PORT, PI_BAUD)
    try:
        do_test(mc)
    finally:
        print("Waiting for another Message")


if __name__ == '__main__':
    proxy_options = None
    if input_proxy_host is not None and input_proxy_port != 0:
        proxy_options = http.HttpProxyOptions(
            host_name=input_proxy_host,
            port=input_proxy_port)
    choice = input("Run Locally (l) or Using AWS (a): ")
    while not (choice == "l" or choice == "a"):
        print("\n\nPlease input valid option.")
        choice = input("\nRun Locally (l) or Using AWS (a): ")
    if choice == 'l':
        run_mech()
        sys.exit()
    else:
        pass
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=input_endpoint,
        port=input_port,
        cert_filepath=input_cert,
        pri_key_filepath=input_key,
        ca_filepath=input_ca,
        on_connection_interrupted=on_connection_interrupted,
        on_connection_resumed=on_connection_resumed,
        client_id=input_clientId,
        clean_session=False,
        keep_alive_secs=30,
        http_proxy_options=proxy_options,
        on_connection_success=on_connection_success,
        on_connection_failure=on_connection_failure,
        on_connection_closed=on_connection_closed)

    if not input_is_ci:
        print(f"Connecting to {input_endpoint} with client ID '{input_clientId}'...")
    else:
        print("Connecting to endpoint with client ID")
    connect_future = mqtt_connection.connect()

    connect_future.result()
    print("Connected!")

    message_topic = input_topic

    print("Subscribing to topic '{}'...".format(message_topic))
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic=message_topic,
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=on_message_received)

    subscribe_result = subscribe_future.result()
    print("Subscribed with {}".format(str(subscribe_result['qos'])))

    message_count = input_count
    if message_count != 0 and not received_all_event.is_set():
        print("Waiting for all messages to be received...")

    received_all_event.wait()
    print("{} message(s) received.".format(received_count))

    print("Disconnecting...")
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()
    print("Disconnected!")

import paho.mqtt.client as mqtt
import tkinter as tk
from tkinter import ttk
import threading
from PIL import Image, ImageTk
import io
import base64
import ssl

# MQTT Connection Constants
BROKER = "54d335627idfe0684c31a4d8ac17a897978b.s1.eu.hivemq.cloud"
PORT = 8884
TOPIC = "/raphael/light_control"
USERNAME = "raphael"
PASSWORD = "raphael1"

class LightSimulationGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MQTT Light Control - Simulation")
        self.root.geometry("400x400")
        self.root.configure(bg='#f8f9fa')

        # Set initial state to unknown until we receive a message
        self.light_status = None
        self.is_connected = False

        # Create styles
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f8f9fa')
        self.style.configure('Header.TLabel', font=('Segoe UI', 18, 'bold'), foreground='#4361ee', background='#f8f9fa')
        self.style.configure('Status.TLabel', font=('Segoe UI', 14), padding=10, background='#f8f9fa')
        self.style.configure('Connection.TLabel', font=('Segoe UI', 10), background='#f8f9fa')

        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="20", style='TFrame')
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_label = ttk.Label(
            self.main_frame,
            text="MQTT Light Control",
            style='Header.TLabel'
        )
        header_label.pack(pady=(0, 20))

        # Light bulb frame
        self.bulb_frame = ttk.Frame(self.main_frame, style='TFrame')
        self.bulb_frame.pack(pady=20)

        # Light bulb canvas
        self.bulb_canvas = tk.Canvas(self.bulb_frame, width=120, height=120,
                                    bg='#f8f9fa', highlightthickness=0)
        self.bulb_canvas.pack()

        # Draw initial neutral bulb
        self.draw_neutral_bulb()

        # Status indicator frame with border
        self.status_frame = tk.Frame(
            self.main_frame,
            bg='#f8f9fa',
            highlightbackground='#6c757d',
            highlightthickness=1,
            bd=0
        )
        self.status_frame.pack(fill=tk.X, pady=20)

        # Status label
        self.status_label = ttk.Label(
            self.status_frame,
            text="Waiting for light status...",
            style='Status.TLabel'
        )
        self.status_label.pack(pady=10)

        # Connection status at bottom
        self.connection_frame = tk.Frame(self.main_frame, bg='#f8f9fa')
        self.connection_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))

        self.connection_dot = tk.Canvas(self.connection_frame, width=10, height=10,
                                       bg='#f8f9fa', highlightthickness=0)
        self.connection_dot.pack(side=tk.RIGHT, padx=(0, 5))
        self.connection_dot.create_oval(2, 2, 8, 8, fill='#dc3545', outline='')

        self.connection_label = ttk.Label(
            self.connection_frame,
            text="Disconnected",
            style='Connection.TLabel'
        )
        self.connection_label.pack(side=tk.RIGHT)

        # Start MQTT client in a separate thread
        self.mqtt_thread = threading.Thread(target=self.start_mqtt_client)
        self.mqtt_thread.daemon = True
        self.mqtt_thread.start()

        # Update connection status
        self.update_connection_status()

        # Reconnect button
        self.reconnect_button = ttk.Button(
            self.main_frame,
            text="Reconnect",
            command=self.reconnect
        )
        self.reconnect_button.pack(side=tk.BOTTOM, pady=10)

        # Request current status button
        self.request_status_button = ttk.Button(
            self.main_frame,
            text="Request Current Status",
            command=self.request_current_status
        )
        self.request_status_button.pack(side=tk.BOTTOM, pady=5)

    def draw_neutral_bulb(self):
        # Clear canvas
        self.bulb_canvas.delete("all")

        # Draw neutral bulb (waiting for status)
        self.bulb_canvas.create_oval(10, 10, 110, 110, fill='#f8f9fa', outline='#6c757d', width=2)
        self.bulb_canvas.create_text(60, 60, text="💡", font=('Segoe UI', 40), fill='#6c757d')

    def draw_bulb(self, status):
        # Clear canvas
        self.bulb_canvas.delete("all")

        # Draw bulb
        if status == "ON":
            # Glowing effect
            self.bulb_canvas.create_oval(10, 10, 110, 110, fill='#4cc9f0', outline='')
            # Light rays
            self.bulb_canvas.create_oval(0, 0, 120, 120, fill='', outline='#4cc9f0', width=2)
            # Bulb icon
            self.bulb_canvas.create_text(60, 60, text="💡", font=('Segoe UI', 40), fill='white')
        elif status == "OFF":
            # Off bulb
            self.bulb_canvas.create_oval(10, 10, 110, 110, fill='#f8f9fa', outline='#adb5bd', width=2)
            # Bulb icon
            self.bulb_canvas.create_text(60, 60, text="💡", font=('Segoe UI', 40), fill='#adb5bd')
        else:
            # Unknown state
            self.draw_neutral_bulb()

    def update_status(self, status):
        self.light_status = status
        if status == "ON":
            self.status_label.config(text="💡 Light is TURNED ON")
            self.status_frame.config(highlightbackground='#4cc9f0')
            self.status_frame.config(bg='#e6f8ff')
            self.draw_bulb("ON")
        elif status == "OFF":
            self.status_label.config(text="💡 Light is TURNED OFF")
            self.status_frame.config(highlightbackground='#3a0ca3')
            self.status_frame.config(bg='#e9ecef')
            self.draw_bulb("OFF")
        else:
            self.status_label.config(text="Waiting for light status...")
            self.status_frame.config(highlightbackground='#6c757d')
            self.status_frame.config(bg='#f8f9fa')
            self.draw_neutral_bulb()

    def update_connection_status(self):
        if hasattr(self, 'client') and self.is_connected:
            self.connection_label.config(text="Connected")
            self.connection_dot.delete("all")
            self.connection_dot.create_oval(2, 2, 8, 8, fill='#198754', outline='')

            # If we're connected but don't have a light status yet, request it
            if self.light_status is None and hasattr(self, 'client'):
                self.request_current_status()
        else:
            self.connection_label.config(text="Disconnected")
            self.connection_dot.delete("all")
            self.connection_dot.create_oval(2, 2, 8, 8, fill='#dc3545', outline='')
        self.root.after(1000, self.update_connection_status)

    def request_current_status(self):
        """Request the current light status by publishing a STATUS_REQUEST message"""
        if hasattr(self, 'client') and self.is_connected:
            try:
                self.client.publish("/raphael/status_request", "REQUEST")
                self.status_label.config(text="Requesting current status...")
            except Exception as e:
                print(f"Error requesting status: {e}")

    def reconnect(self):
        if hasattr(self, 'client'):
            try:
                self.client.disconnect()
            except:
                pass

        # Reset light status
        self.light_status = None
        self.update_status(None)

        # Start a new MQTT client thread
        self.mqtt_thread = threading.Thread(target=self.start_mqtt_client)
        self.mqtt_thread.daemon = True
        self.mqtt_thread.start()

        self.status_label.config(text="Reconnecting...")

    def on_message(self, client, userdata, message):
        topic = message.topic
        msg = message.payload.decode("utf-8")

        print(f"Received message on topic {topic}: {msg}")

        # Handle messages on the light control topic
        if topic == TOPIC:
            if msg == "ON":
                self.root.after(0, self.update_status, "ON")
            elif msg == "OFF":
                self.root.after(0, self.update_status, "OFF")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to broker {BROKER} on port {PORT}")
            self.is_connected = True

            # Subscribe to all topics to catch any status updates
            self.client.subscribe("#")

            # If we have a light status, display it, otherwise show waiting message
            if self.light_status:
                self.root.after(0, lambda: self.status_label.config(text=f"💡 Light is TURNED {self.light_status}"))
            else:
                self.root.after(0, lambda: self.status_label.config(text="Waiting for light status..."))

            # Request current status when connected
            self.root.after(1000, self.request_current_status)
        else:
            print(f"Failed to connect with code: {rc}")
            self.is_connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized"
            }
            error_msg = error_messages.get(rc, f"Unknown error (code {rc})")
            self.root.after(0, lambda: self.status_label.config(text=f"Connection error: {error_msg}"))

    def on_disconnect(self, client, userdata, rc):
        print(f"Disconnected with result code {rc}")
        self.is_connected = False
        if rc != 0:
            self.root.after(0, lambda: self.status_label.config(text="Unexpected disconnection"))

    def start_mqtt_client(self):
        # Create a new client ID each time
        import random
        client_id = f'python_client_{random.randint(0, 1000000)}'

        # Create a new client instance
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311, transport="websockets")

        # Set up SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Set TLS with the SSL context
        self.client.tls_set_context(ssl_context)

        # Set username and password
        self.client.username_pw_set(USERNAME, PASSWORD)

        # Set callbacks
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

        try:
            print(f"Connecting to {BROKER}:{PORT}...")
            self.client.connect(BROKER, PORT, 60)
            self.client.subscribe(TOPIC)
            self.client.loop_forever()
        except Exception as e:
            print(f"Connection error: {e}")
            self.is_connected = False
            self.root.after(0, lambda: self.status_label.config(text=f"Connection error: {str(e)}"))

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = LightSimulationGUI()
    app.run()

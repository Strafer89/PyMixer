import serial
import serial.tools.list_ports
import time
import sys
import threading
import pythoncom
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
import ctypes  # Added for locking the PC
import webbrowser # Added for opening a webpage
from pystray import Icon, Menu, MenuItem
from PIL import Image
import os
import ast
import subprocess
import pygetwindow as gw
import psutil
import win32process

# --- GLOBAL VARIABLES ---
ser = None
running = True
config = {}
config_file_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'config.py')

# --- CONFIGURATION FILE HANDLING ---

def load_config():
    """
    Loads the configuration from config.py into a dictionary, providing defaults
    if the file is not found or fails to parse.
    """
    global config
    
    # Initialize with default values
    config_data = {
        'SERIAL_PORT': 'COM3',
        'BAUD_RATE': 115200,
        'APP_MAPPINGS': {f'K{i+1}': '' for i in range(4)},
        'SLIDER_REVERSE': {f'K{i+1}': False for i in range(4)},
        'SLIDER_SENSITIVITY': {f'K{i+1}': 1.0 for i in range(4)},
        'NUM_KNOBS': 4,
        'NUM_BUTTONS': 4
    }

    if os.path.exists(config_file_path):
        try:
            # Use a simpler, more robust method to load the config file
            local_vars = {}
            with open(config_file_path, 'r') as f:
                exec(f.read(), {}, local_vars)
            
            # Update default values with loaded values
            config_data.update(local_vars)
        except Exception as e:
            print(f"Error parsing config.py: {e}. Using default values.")
    else:
        print("config.py not found. Using default values.")

    # Update the global config dictionary
    config = config_data

# --- AUDIO CONTROL FUNCTIONS ---

def get_audio_session(process_name):
    """
    Finds the audio session for a given process name.
    """
    sessions = AudioUtilities.GetAllSessions()
    for session in sessions:
        if session.Process and session.Process.name() == process_name:
            return session
    return None

def set_app_volume(session, volume_level):
    """
    Sets the volume for a specific application.
    """
    if session:
        volume = session._ctl.QueryInterface(ISimpleAudioVolume)
        volume.SetMasterVolume(volume_level, None)

def toggle_app_mute(session):
    """
    Toggles the mute state of an application.
    """
    if session:
        volume = session._ctl.QueryInterface(ISimpleAudioVolume)
        current_mute = volume.GetMute()
        volume.SetMute(not current_mute, None)
        print(f"Mute for {session.Process.name()} is now {'ON' if not current_mute else 'OFF'}")

def set_master_volume(volume_level):
    """
    Sets the master system volume.
    """
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
    volume_interface.SetMasterVolumeLevelScalar(volume_level, None)

def toggle_master_mute():
    """
    Toggles the mute state of the master audio device.
    """
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
    current_mute = volume_interface.GetMute()
    volume_interface.SetMute(not current_mute, None)
    print(f"Master volume mute is now {'ON' if not current_mute else 'OFF'}")

def get_focused_app_process_name():
    """
    Gets the process name of the currently focused application.
    Returns None if no focused window is found.
    """
    try:
        active_window = gw.getActiveWindow()
        if active_window:
            # Use win32process to get the PID from the window handle
            pid = win32process.GetWindowThreadProcessId(active_window._hWnd)[1]
            if pid:
                return psutil.Process(pid).name()
    except Exception as e:
        print(f"Could not get focused application: {e}")
        return None
    return None

# --- NEW BUTTON ACTION FUNCTIONS ---

def toggle_mic_mute():
    """
    Toggles the mute state of the default microphone.
    """
    try:
        devices = AudioUtilities.GetMicrophone()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
        current_mute = volume_interface.GetMute()
        volume_interface.SetMute(not current_mute, None)
        print(f"Microphone mute is now {'ON' if not current_mute else 'OFF'}")
    except Exception as e:
        print(f"Could not toggle microphone mute: {e}")

def lock_pc():
    """
    Locks the computer using the Windows API.
    """
    try:
        ctypes.windll.user32.LockWorkStation()
        print("PC locked.")
    except Exception as e:
        print(f"Could not lock PC: {e}")

def open_webpage(url):
    """
    Opens a URL in the default web browser.
    """
    try:
        webbrowser.open(url)
        print(f"Opening webpage: {url}")
    except Exception as e:
        print(f"Could not open webpage: {e}")

# --- SERIAL COMMUNICATION THREAD ---

def serial_reader_thread():
    """
    Function to run in a separate thread, continuously reading serial data.
    """
    global ser, running, config
    last_button_state = {}
    last_knob_value = {}
    last_config_load_time = time.time()

    pythoncom.CoInitialize()

    try:
        while running:
            if not ser or not ser.is_open:
                time.sleep(1)
                continue

            # Reload config every 5 seconds to pick up changes from the GUI
            if time.time() - last_config_load_time > 5:
                load_config()
                last_config_load_time = time.time()

            line = ser.readline().decode('utf-8').strip()
            if not line:
                continue

            try:
                data = [int(val) for val in line.split('|')]
            except ValueError:
                continue
            
            num_knobs = config.get('NUM_KNOBS', 4)
            num_buttons = config.get('NUM_BUTTONS', 4)

            if len(data) != num_knobs + num_buttons:
                continue
            
            knob_values = data[:num_knobs]
            button_values = data[num_knobs:]

            for i, knob_value in enumerate(knob_values):
                key = f'K{i + 1}'
                if key not in last_knob_value:
                    last_knob_value[key] = knob_value

                sensitivity = config.get('SLIDER_SENSITIVITY', {}).get(key, 1.0)
                if abs(knob_value - last_knob_value[key]) < 10 / sensitivity:
                    continue

                if key in config.get('APP_MAPPINGS', {}):
                    app_name = config['APP_MAPPINGS'][key]
                    
                    if config.get('SLIDER_REVERSE', {}).get(key, False):
                        scaled_value = 1023.0 - knob_value
                    else:
                        scaled_value = knob_value
                    
                    volume_level = scaled_value / 1023.0
                    
                    if app_name == "focused_app":
                        focused_app_name = get_focused_app_process_name()
                        if focused_app_name:
                            
                            # --- START: MODIFIED LOGIC ---
                            # Check if the focused app already has a dedicated knob
                            all_mappings = config.get('APP_MAPPINGS', {})
                            
                            # Get a list of all *other* knob mappings (excluding this one)
                            other_knob_mappings = [
                                mapped_app for k, mapped_app in all_mappings.items() 
                                if k.startswith('K') and k != key
                            ]

                            if focused_app_name in other_knob_mappings:
                                # This app has its own knob, so the 'focused_app' knob should ignore it.
                                # print(f"Ignoring focused app '{focused_app_name}' as it has a dedicated knob.")
                                pass
                            else:
                                # This app does NOT have a dedicated knob, so control it.
                                session = get_audio_session(focused_app_name)
                                if session:
                                    set_app_volume(session, volume_level)
                            # --- END: MODIFIED LOGIC ---
                                    
                    elif app_name == 'explorer.exe':
                        set_master_volume(volume_level)
                    else:
                        session = get_audio_session(app_name)
                        if session:
                            set_app_volume(session, volume_level)
                
                last_knob_value[key] = knob_value
            
            for i, button_value in enumerate(button_values):
                key = f'B{i + 1}'
                if key in config.get('APP_MAPPINGS', {}):
                    app_command = config['APP_MAPPINGS'][key]
                    
                    if key not in last_button_state:
                        last_button_state[key] = 0

                    if button_value == 1 and last_button_state[key] == 0:
                        # Check for new button actions
                        if app_command == 'toggle_mic_mute':
                            toggle_mic_mute()
                        elif app_command == 'toggle_master_mute':
                            toggle_master_mute()
                        elif app_command == 'lock_pc':
                            lock_pc()
                        elif app_command.startswith('http'):
                            open_webpage(app_command)
                        else:
                            # Default action is to toggle mute for an application
                            session = get_audio_session(app_command)
                            if session:
                                toggle_app_mute(session)
                    
                    last_button_state[key] = button_value
            
            time.sleep(0.01) # Small delay to prevent high CPU usage

    except Exception as e:
        print(f"An error occurred in the serial reader thread: {e}")
    finally:
        pythoncom.CoUninitialize()
        if ser and ser.is_open:
            ser.close()
            print("Serial port closed.")

# --- SYSTEM TRAY ICON FUNCTIONS ---

def open_config_gui(icon, item):
    """
    Function to open the configuration GUI in a new process.
    """
    try:
        # Get the path to the Python executable
        python_executable = sys.executable
        
        # On Windows, prefer pythonw.exe to avoid a console window.
        if sys.platform == "win32" and "python.exe" in python_executable:
            pythonw_path = os.path.join(os.path.dirname(python_executable), "pythonw.exe")
            if os.path.exists(pythonw_path):
                python_executable = pythonw_path
        
        # Construct the full path to the GUI script from the main script's path
        main_script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        gui_script_path = os.path.join(main_script_dir, 'config_gui.py')
        
        # Add debugging prints
        print("Attempting to open configuration GUI...")
        print(f"Python executable path: {python_executable}")
        print(f"GUI script path: {gui_script_path}")
        
        if not os.path.exists(gui_script_path):
            print(f"Error: config_gui.py not found at {gui_script_path}")
            return
            
        subprocess.Popen([python_executable, gui_script_path])
        print("Configuration GUI process started successfully.")
    except Exception as e:
        print(f"Failed to open configuration GUI. An unexpected error occurred: {e}")

def exit_program(icon, item):
    """
    Function to stop the program and close the icon.
    """
    global running
    print("Exiting PyMixer...")
    running = False
    icon.stop()

def setup_and_run_icon():
    """
    Sets up the system tray icon and runs it in detached mode.
    """
    global ser
    load_config()
    print("Configuration loaded from config.py.")

    try:
        ser = serial.Serial(config['SERIAL_PORT'], config['BAUD_RATE'], timeout=1)
        print(f"Connected to ESP32 on port {config['SERIAL_PORT']}")
        
        thread = threading.Thread(target=serial_reader_thread)
        thread.daemon = True
        thread.start()
    except serial.SerialException as e:
        print(f"Error: Could not open serial port {config['SERIAL_PORT']}. Please check the port number.")
        print(f"Details: {e}")
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in sorted(ports):
            print(f"  {port}: {desc} [{hwid}]")
        raise

    icon_image = Image.open("icon.ico")
    menu = (
        MenuItem('PyMixer is Running', None, enabled=False),
        MenuItem('Settings', open_config_gui),
        MenuItem('Exit', exit_program)
    )

    icon = Icon(
        name="PyMixer",
        icon=icon_image,
        title="PyMixer - ESP32 Audio Mixer",
        menu=menu
    )
    
    icon.run_detached()

if __name__ == "__main__":
    try:
        # Check for required libraries
        try:
            import pygetwindow
            import psutil
            import win32process
        except ImportError as e:
            print(f"\nError: A required library is not installed. Details: {e}")
            print("Please install missing libraries by running the following command in your terminal:")
            print("pip install pygetwindow psutil pywin32")
            print("The program will now exit.")
            time.sleep(10)
            sys.exit(1)
            
        setup_and_run_icon()
    except Exception as e:
        print(f"\nFATAL ERROR: The program failed to start. Details: {e}")
        print("This window will close in 10 seconds.")
        time.sleep(10)
        sys.exit()
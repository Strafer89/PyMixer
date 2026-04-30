import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import psutil
import time
import serial.tools.list_ports # Correct import for serial ports

# --- CONFIGURATION FILE HANDLING ---
config_file_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'config.py')

# Map technical action names to user-friendly display names
ACTION_DISPLAY_NAMES = {
    'focused_app': 'Focused Application',
    'explorer.exe': 'Master Volume',
    'toggle_mic_mute': 'Toggle Microphone Mute',
    'toggle_master_mute': 'Toggle Master Mute',
    'lock_pc': 'Lock PC',
    'Open Webpage...': 'Open Webpage...'
}

# Invert the dictionary for easy lookup when saving
DISPLAY_TO_ACTION_NAMES = {v: k for k, v in ACTION_DISPLAY_NAMES.items()}

def load_config():
    """
    Loads the configuration from config.py.
    Returns a dictionary of the configuration.
    """
    config = {
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
            local_vars = {}
            with open(config_file_path, 'r') as f:
                exec(f.read(), {}, local_vars)
            
            config.update(local_vars)
        except Exception as e:
            print(f"Error parsing config.py: {e}. Using default values.")
            messagebox.showerror("Configuration Error", f"Could not parse config.py: {e}\nUsing default values.")
    
    return config

def save_config(config_data):
    """
    Saves the configuration dictionary back to config.py.
    """
    try:
        with open(config_file_path, 'w') as f:
            f.write(f"SERIAL_PORT = '{config_data['SERIAL_PORT']}'\n")
            f.write(f"BAUD_RATE = {config_data['BAUD_RATE']}\n")
            f.write(f"NUM_KNOBS = {config_data['NUM_KNOBS']}\n")
            f.write(f"NUM_BUTTONS = {config_data['NUM_BUTTONS']}\n")
            f.write(f"APP_MAPPINGS = {repr(config_data['APP_MAPPINGS'])}\n")
            f.write(f"SLIDER_REVERSE = {repr(config_data['SLIDER_REVERSE'])}\n")
            f.write(f"SLIDER_SENSITIVITY = {repr(config_data['SLIDER_SENSITIVITY'])}\n")
        messagebox.showinfo("Success", "Configuration saved successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Could not save configuration: {e}")

# --- GUI CLASS ---

class PyMixerConfigApp:
    def __init__(self, master):
        self.master = master
        master.title("PyMixer Configuration")
        master.geometry("600x600")
        
        # Load initial configuration
        self.config = load_config()

        # Get a list of running applications
        self.running_apps = sorted(list({p.name() for p in psutil.process_iter(['name']) if p.name().endswith('.exe')}))
        
        # Build a separate list of options for knob and button dropdowns
        knob_specific_actions = [ACTION_DISPLAY_NAMES['focused_app'], ACTION_DISPLAY_NAMES['explorer.exe']]
        button_specific_actions = [
            ACTION_DISPLAY_NAMES['toggle_mic_mute'],
            ACTION_DISPLAY_NAMES['toggle_master_mute'],
            ACTION_DISPLAY_NAMES['lock_pc']
        ]

        # The knob list only includes volume-related actions and running apps
        self.knob_app_list = sorted(knob_specific_actions + self.running_apps)

        # The button list includes all button actions and running apps
        self.button_app_list = sorted(button_specific_actions + self.running_apps)
        self.button_app_list.extend(['Open Webpage...']) # Always put this at the end

        self.create_widgets()

    def create_widgets(self):
        """Creates all the GUI widgets for the application."""
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # --- KNOB MAPPINGS TAB ---
        knob_tab = ttk.Frame(notebook, padding="10")
        notebook.add(knob_tab, text="Knobs")
        self.create_knob_widgets(knob_tab)

        # --- BUTTON MAPPINGS TAB ---
        button_tab = ttk.Frame(notebook, padding="10")
        notebook.add(button_tab, text="Buttons")
        self.create_button_widgets(button_tab)
        
        # --- GLOBAL SETTINGS TAB ---
        settings_tab = ttk.Frame(notebook, padding="10")
        notebook.add(settings_tab, text="Settings")
        self.create_settings_widgets(settings_tab)

        # --- SAVE BUTTON ---
        save_button = ttk.Button(main_frame, text="Save Configuration", command=self.save_and_reload)
        save_button.pack(pady=10)
    
    def create_knob_widgets(self, parent):
        """Creates the widgets for the Knob Mappings tab."""
        tk.Label(parent, text="Knob Mappings", font=("Helvetica", 14, "bold")).pack(pady=10)
        
        self.knob_vars = {}
        for i in range(self.config['NUM_KNOBS']):
            key = f'K{i + 1}'
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, pady=5)
            
            # Application selection
            tk.Label(frame, text=f"Knob {i+1}:").pack(side=tk.LEFT, padx=5)
            current_value = self.config['APP_MAPPINGS'].get(key, '')
            # Convert technical name to display name for the dropdown
            display_value = ACTION_DISPLAY_NAMES.get(current_value, current_value)
            
            app_var = tk.StringVar(value=display_value)
            # Use the new, specific list for knobs
            app_menu = ttk.Combobox(frame, textvariable=app_var, values=self.knob_app_list)
            app_menu.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
            
            # Sensitivity slider
            tk.Label(frame, text="Sensitivity:").pack(side=tk.LEFT, padx=5)
            sens_var = tk.DoubleVar(value=self.config['SLIDER_SENSITIVITY'].get(key, 1.0))
            sens_slider = ttk.Scale(frame, from_=0.1, to=2.0, orient=tk.HORIZONTAL, variable=sens_var)
            sens_slider.pack(side=tk.LEFT, padx=5)
            sens_label = tk.Label(frame, textvariable=sens_var)
            sens_label.pack(side=tk.LEFT, padx=5)
            
            # Reverse checkbox
            rev_var = tk.BooleanVar(value=self.config['SLIDER_REVERSE'].get(key, False))
            rev_check = ttk.Checkbutton(frame, text="Reverse", variable=rev_var)
            rev_check.pack(side=tk.LEFT, padx=5)

            self.knob_vars[key] = {'app': app_var, 'sens': sens_var, 'rev': rev_var}
    
    def create_button_widgets(self, parent):
        """Creates the widgets for the Button Mappings tab."""
        tk.Label(parent, text="Button Mappings", font=("Helvetica", 14, "bold")).pack(pady=10)
        
        self.button_vars = {}
        self.url_entries = {}
        for i in range(self.config['NUM_BUTTONS']):
            key = f'B{i + 1}'
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, pady=5)

            # Button command selection
            tk.Label(frame, text=f"Button {i+1}:").pack(side=tk.LEFT, padx=5)
            current_value = self.config['APP_MAPPINGS'].get(key, '')
            display_value = ACTION_DISPLAY_NAMES.get(current_value, current_value)
            
            app_var = tk.StringVar(value=display_value)
            # Use the new, specific list for buttons
            app_menu = ttk.Combobox(frame, textvariable=app_var, values=self.button_app_list)
            app_menu.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
            
            # URL entry field for the "Open Webpage" option
            url_entry = ttk.Entry(frame, state='disabled')
            url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
            self.url_entries[key] = url_entry
            
            # Bind the handler to both the Combobox and the URL entry field
            def handler(event, key=key, app_var=app_var, url_entry=url_entry):
                if app_var.get() == 'Open Webpage...':
                    url_entry.config(state='enabled')
                else:
                    url_entry.config(state='disabled')
                    url_entry.delete(0, tk.END)

            app_menu.bind("<<ComboboxSelected>>", handler)
            
            # Check if the initial value is a URL and enable the entry
            if self.config['APP_MAPPINGS'].get(key, '').startswith('http'):
                url_entry.config(state='normal')
                url_entry.delete(0, tk.END)
                url_entry.insert(0, self.config['APP_MAPPINGS'].get(key))
                app_var.set('Open Webpage...')


            self.button_vars[key] = {'app': app_var, 'url_entry': url_entry}

    def create_settings_widgets(self, parent):
        """Creates the widgets for the Global Settings tab."""
        tk.Label(parent, text="Global Settings", font=("Helvetica", 14, "bold")).pack(pady=10)
        
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        tk.Label(frame, text="Serial Port:").pack(side=tk.LEFT, padx=5)
        self.serial_port_var = tk.StringVar(value=self.config['SERIAL_PORT'])
        ports = [p.device for p in serial.tools.list_ports.comports()] # Corrected this line
        ttk.Combobox(frame, textvariable=self.serial_port_var, values=ports).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        tk.Label(frame, text="Baud Rate:").pack(side=tk.LEFT, padx=5)
        self.baud_rate_var = tk.StringVar(value=str(self.config['BAUD_RATE']))
        ttk.Entry(frame, textvariable=self.baud_rate_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    
    def check_url_entry(self, key, selection):
        """Enables/disables the URL entry field based on the combobox selection."""
        if selection == 'Open Webpage...':
            self.url_entries[key].config(state='enabled')
        else:
            self.url_entries[key].config(state='disabled')
            self.url_entries[key].delete(0, tk.END)

    def save_and_reload(self):
        """Gathers data from widgets and saves the new configuration."""
        new_config = self.config.copy()
        
        # Update knob mappings
        for key, vars_dict in self.knob_vars.items():
            selection = vars_dict['app'].get()
            # Convert display name back to technical name for saving
            mapped_value = DISPLAY_TO_ACTION_NAMES.get(selection, selection)
            new_config['APP_MAPPINGS'][key] = mapped_value
            new_config['SLIDER_SENSITIVITY'][key] = vars_dict['sens'].get()
            new_config['SLIDER_REVERSE'][key] = vars_dict['rev'].get()

        # Update button mappings
        for key, vars_dict in self.button_vars.items():
            selection = vars_dict['app'].get()
            if selection == 'Open Webpage...':
                url = vars_dict['url_entry'].get()
                new_config['APP_MAPPINGS'][key] = url if url else ''
            else:
                # Convert display name back to technical name for saving
                mapped_value = DISPLAY_TO_ACTION_NAMES.get(selection, selection)
                new_config['APP_MAPPINGS'][key] = mapped_value
        
        # Update global settings
        new_config['SERIAL_PORT'] = self.serial_port_var.get()
        new_config['BAUD_RATE'] = int(self.baud_rate_var.get())

        save_config(new_config)
        
        # It's good practice to also update the running config for this session
        self.config = new_config

if __name__ == "__main__":
    root = tk.Tk()
    app = PyMixerConfigApp(root)
    root.mainloop()

#!/usr/bin/env python3
"""
Keyboard to Gamepad Mapper
Maps a second keyboard to a virtual Xbox-style gamepad
"""

import evdev
from evdev import UInput, ecodes as e
import sys

# Key mappings - Option A (WASD layout)
KEY_MAP = {
    # D-pad
    e.KEY_UP: ('dpad', e.ABS_HAT0Y, -1),  # Up
    e.KEY_DOWN: ('dpad', e.ABS_HAT0Y, 1),   # Down
    e.KEY_LEFT: ('dpad', e.ABS_HAT0X, -1),  # Left
    e.KEY_RIGHT: ('dpad', e.ABS_HAT0X, 1),   # Right
    
    # Face buttons
    e.KEY_K: ('btn', e.BTN_SOUTH),    # A button
    e.KEY_L: ('btn', e.BTN_EAST),     # B button
    e.KEY_J: ('btn', e.BTN_WEST),     # X button
    e.KEY_I: ('btn', e.BTN_NORTH),    # Y button
    
    # Shoulder buttons
    e.KEY_R: ('btn', e.BTN_TL),  # L1
    e.KEY_O: ('btn', e.BTN_TR),   # R1
    
    # Triggers (using Z and C keys)
    e.KEY_W: ('trigger', e.ABS_Z, 255),  # L2
    e.KEY_R: ('trigger', e.ABS_RZ, 255), # R2
    
    # Start/Select
    e.KEY_SPACE: ('btn', e.BTN_SELECT),    # Select
    e.KEY_ENTER: ('btn', e.BTN_START),   # Start
}

def list_keyboards():
    """List all keyboard devices"""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    keyboards = []
    
    print("\n=== Available Keyboards ===")
    for i, device in enumerate(devices):
        # Check if device has keyboard capabilities
        caps = device.capabilities()
        if e.EV_KEY in caps and e.KEY_A in caps[e.EV_KEY]:
            keyboards.append(device)
            print(f"{i + 1}. {device.name}")
            print(f"   Path: {device.path}")
    
    return keyboards

def create_gamepad():
    """Create a virtual gamepad device"""
    from evdev import AbsInfo
    
    caps = {
        e.EV_KEY: [
            e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST,
            e.BTN_TL, e.BTN_TR,
            e.BTN_SELECT, e.BTN_START, e.BTN_MODE,
            e.BTN_THUMBL, e.BTN_THUMBR,
        ],
        e.EV_ABS: [
            (e.ABS_X, AbsInfo(value=0, min=-32768, max=32767, fuzz=0, flat=0, resolution=0)),
            (e.ABS_Y, AbsInfo(value=0, min=-32768, max=32767, fuzz=0, flat=0, resolution=0)),
            (e.ABS_RX, AbsInfo(value=0, min=-32768, max=32767, fuzz=0, flat=0, resolution=0)),
            (e.ABS_RY, AbsInfo(value=0, min=-32768, max=32767, fuzz=0, flat=0, resolution=0)),
            (e.ABS_Z, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
            (e.ABS_RZ, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
            (e.ABS_HAT0X, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)),
            (e.ABS_HAT0Y, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)),
        ],
    }
    
    return UInput(caps, name='Keyboard-Gamepad', bustype=0x03, vendor=0x045e, product=0x028e, version=0x0110)

def main():
    # Check if running as root
    if os.geteuid() != 0:
        print("Error: This script must be run as root (use sudo)")
        print("Usage: sudo python3 keyboard_gamepad.py")
        sys.exit(1)
    
    # List keyboards and let user choose
    keyboards = list_keyboards()
    
    if not keyboards:
        print("\nNo keyboards found!")
        sys.exit(1)
    
    print("\nWhich keyboard do you want to use as a gamepad?")
    try:
        choice = int(input("Enter number: ")) - 1
        if choice < 0 or choice >= len(keyboards):
            print("Invalid choice!")
            sys.exit(1)
    except (ValueError, KeyboardInterrupt):
        print("\nCancelled")
        sys.exit(1)
    
    keyboard = keyboards[choice]
    print(f"\n✓ Selected: {keyboard.name}")
    print(f"✓ Path: {keyboard.path}")
    
    # Grab the keyboard exclusively
    try:
        keyboard.grab()
        print("✓ Keyboard grabbed exclusively (won't type anymore)")
    except Exception as ex:
        print(f"Error grabbing keyboard: {ex}")
        sys.exit(1)
    
    # Create virtual gamepad
    gamepad = create_gamepad()
    print("✓ Virtual gamepad created")
    print("\n=== Ready! Press Ctrl+C to stop ===\n")
    
    # Track state for D-pad and triggers
    dpad_state = {e.ABS_HAT0X: 0, e.ABS_HAT0Y: 0}
    trigger_state = {e.ABS_Z: 0, e.ABS_RZ: 0}
    
    try:
        for event in keyboard.read_loop():
            if event.type == e.EV_KEY and event.code in KEY_MAP:
                mapping = KEY_MAP[event.code]
                map_type = mapping[0]
                
                if map_type == 'btn':
                    # Simple button press/release
                    gamepad.write(e.EV_KEY, mapping[1], event.value)
                    
                elif map_type == 'dpad':
                    # D-pad (hat switch)
                    axis = mapping[1]
                    direction = mapping[2]
                    
                    if event.value == 1:  # Key pressed
                        dpad_state[axis] = direction
                    elif event.value == 0:  # Key released
                        if dpad_state[axis] == direction:
                            dpad_state[axis] = 0
                    
                    gamepad.write(e.EV_ABS, axis, dpad_state[axis])
                    
                elif map_type == 'trigger':
                    # Analog triggers
                    axis = mapping[1]
                    max_val = mapping[2]
                    
                    if event.value == 1:  # Key pressed
                        trigger_state[axis] = max_val
                    elif event.value == 0:  # Key released
                        trigger_state[axis] = 0
                    
                    gamepad.write(e.EV_ABS, axis, trigger_state[axis])
                
                gamepad.syn()
    
    except KeyboardInterrupt:
        print("\n\n✓ Stopped")
    finally:
        keyboard.ungrab()
        gamepad.close()
        print("✓ Cleaned up")

if __name__ == '__main__':
    import os
    main()

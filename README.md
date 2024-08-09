
## Big links make big chains
BigLinks is a widget in a PyQt app Computinator Code, to help users manage limited file storage more by leveraging symbolic links to keep data on other local drives. (Currently only tested on Windows)

This preserves default install and program locations, at the symbolically linked location, so the OS sees the folder, but the data storage is actually elsewhere.
## Computinator Code?
So I wanted to make a better file explorer that can preview audio clips with arrow keys and can sort by date modified, and a code editor. I already had a PyQt repo set up for BigLinks, so I just built them together; and added a whole bunch of tools and half-baked features.
## What is a Symbolic Link?
A symbolic link (often abbreviated as symlink) is a type of file that serves as a reference or pointer to another file or directory. 

Unlike a shortcut, a symlink acts as a transparent alias to the file or folder it links to, allowing applications and users to access it as if it were located at the symlink's location. 

This feature is incredibly useful for managing files across different partitions or drives, making it seem as if they're located in a single, convenient location.

There are various types of Symbolic Links

This uses soft links.

Soft Links: Pointers to a file or directory's path. If the target is moved or deleted, the link breaks.

## Network Drives Disclaimer: I didn't test it
Compatibility and Accessibility: Symlinks on network drives might not resolve correctly for different users or machines, due to relative paths being based on the host machine's filesystem.
Permissions: Specific permissions may be required to create or access symlinks on network drives.
Security: Exercise caution as symlinks can potentially expose sensitive directories or files outside the intended scope.
Important: Ensure compatibility and test symlinks and this tool in your specific network and OS environment to prevent data loss or unintended access.

## Also haven't tested large folder moves yet or nested symlinks. Nested folders work tho c:

## Framework
BigLinks is built using the PyQt framework; open source and cross-platform.
Build exe with:

```pyinstaller --onefile --uac-admin --manifest=app.manifest main.py```

## Features
Folder Movement: Simplify the process of moving folders from one drive to another.
Directory Picker: Uses selection if selected or nav root of picker for locations. Can also input a path in form: W:\Test3\Test to navigate picker to.
Symlink Creation: Automatically create symbolic links in the original location, pointing to the folder's new location. This maintains direct access to the moved folders without manually navigating to the new location.
Undo Functionality: A safety feature that allows users to revert the move operation if the symlink creation fails.
Drive Space Check: Before moving, the app checks if the target drive has sufficient space for the intended files, preventing failed move operations due to space limitations.
Progress Bar: Provides real-time feedback on the progress of moving folders, enhancing the user experience during longer operations it is count/total, not file progress ;P
Elevated Permissions Handling: Creating symlinks requires elevated permissions on Windows.

## Getting Started
Not yet streamlined..

I use miniconda and python, you might need to pip install pyaudio, pyogg, keyboard, pyautogui, PyQt6, numpy, vosk, dotenv,,, pyserial or serial, threading? openai? difflib? pyinstaller? idk 

pip install keyboard, numpy,  openai, PyAudio, PyAutoGUI, PyOgg, PyQt6-WebEngine, pyserial, PySocks, python-dotenv, serial, sounddevice, vosk

you can run this to create the exe in dist/
pyinstaller --onefile --windowed --manifest=app.manifest main.py

## Contributing
We welcome contributions! Whether you're looking to report a bug, propose a feature, or submit a pull request, your input is valuable. Please refer to our contribution guidelines for more information.

## License
BigLinks is released under a License. See the LICENSE file in the repository for full licensing details.

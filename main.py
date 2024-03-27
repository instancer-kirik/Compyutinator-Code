import os
import sys
if sys.__stdout__ is None or sys.__stderr__ is None:
    os.environ['KIVY_NO_CONSOLELOG'] = '1'
import shutil
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
import threading
from kivy.clock import Clock
import logging


logging.basicConfig(level=logging.INFO)

#  several functionalities:
# Navigating to a path entered by the user.
# Selecting source and target directories for moving contents and creating a symlink.
# Removing a symlink if selected.
# Checking if there's enough space on the destination drive before moving contents.
# Moving contents in a background thread with progress update. Then creating symlink
class BigLinksApp(App):
    def build(self):
        self.screen_manager = ScreenManager()
        linker_screen = Screen(name='BigLinks')
        layout = BoxLayout(orientation='vertical')
        #Horizontal layout for path input and navigation button
        path_navigation_layout = BoxLayout(size_hint_y=None, height=30)
        
        # TextInput for user to enter or paste a path
        self.path_input = TextInput(size_hint_x=0.85, multiline=False)
        path_navigation_layout.add_widget(self.path_input)
        
        # Button to navigate to the entered path
        navigate_button = Button(text='Go', size_hint_x=0.15)
        navigate_button.bind(on_press=self.navigate_to_path)
        path_navigation_layout.add_widget(navigate_button)
        
        
        # Horizontal layout for source and target buttons
        buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)  # Adjust height as needed
        
        # Button for selecting the link source
        btn_select_source = Button(text='Select Link Source')
        btn_select_source.bind(on_press=self.select_link_source)
        buttons_layout.add_widget(btn_select_source)  # Add to the horizontal layout

        # Button for selecting the link target
        btn_select_target = Button(text='Select Link Target')
        btn_select_target.bind(on_press=self.select_link_target)
        buttons_layout.add_widget(btn_select_target)  # Add to the horizontal layout
        
        # Initialize file chooser here to avoid reference before assignment error
        self.file_chooser = FileChooserListView(size_hint=(1, 0.8))
        # Drive selection dropdown
        self.drive_selector = Spinner(
            text='Select Drive',
            values=self.get_drives(),
            size_hint=(1, 0.1)
        )
        self.drive_selector.bind(text=self.on_drive_selection)
        self.progress_bar = ProgressBar(max=100, value=0, size_hint=(1, 0.05))
        layout.add_widget(self.progress_bar)
        layout.add_widget(self.drive_selector)
    
        layout.add_widget(path_navigation_layout)
        
        # File chooser is added to the layout
        layout.add_widget(self.file_chooser)

        # Selected path label, update this based on the file chooser's selection
        self.selected_path_label = Label(text="Selected path: None", size_hint=(1, 0.1))
        layout.add_widget(self.selected_path_label)
        layout.add_widget(buttons_layout)  # Add the horizontal layout to the main vertical layout
       
        # Inside your build method, after initializing other UI components
        self.remove_symlink_button = Button(text="Remove Symlink (does not move files)", size_hint=(1, 0.1), disabled=True)
        self.remove_symlink_button.bind(on_press=self.remove_symlink)
        layout.add_widget(self.remove_symlink_button)
        self.undo_move_button = Button(text="Undo Move (in the event of failed symlink creation)", size_hint=(1, 0.1), disabled=True)
        self.undo_move_button.bind(on_press=self.undo_move)
        layout.add_widget(self.undo_move_button)


        # Button to move folder and create symlink, with its event handler
        btn_move_and_link = Button(text='Move Folder Contents and Create Symlink', size_hint=(1, 0.1))
        btn_move_and_link.bind(on_press=self.move_contents_and_create_symlink)
        layout.add_widget(btn_move_and_link)

        # Adding layout to the screen
        linker_screen.add_widget(layout)

        # Adding screen to the screen manager
        self.screen_manager.add_widget(linker_screen)
# Variables to store source and target paths
        self.source_path = None
        self.target_path = None
        # Return the screen manager from the build method
        return self.screen_manager
    def navigate_to_path(self, instance):
        """Navigate the file chooser to the path entered by the user."""
        path = self.path_input.text.strip()
        if os.path.isdir(path):
            self.file_chooser.path = path
        else:
            self.selected_path_label.text = "Invalid path. Please enter a valid directory path."
    def select_link_source(self, instance):
        selected = self.file_chooser.selection[0] if self.file_chooser.selection else self.file_chooser.path
        if os.path.islink(selected):
            print(f"Selected simlink: {selected}")
            self.symlink_source = selected
            # Show that the source is a symlink and display its target
            symlink_target = os.readlink(selected)
            self.selected_path_label.text = f"Source is a symlink pointing to: {symlink_target}\nConsider removing the symlink."
            self.remove_symlink_button.disabled = False  # Enable the button to remove the symlink
        else:
            self.source_path = selected
            self.update_path_label()
            self.remove_symlink_button.disabled = True  # Disable the button as it's not a symlink
        
  
    def select_link_target(self, instance):
        # Similar logic applied to selecting the target
        selected = self.file_chooser.selection[0] if self.file_chooser.selection else self.file_chooser.path
    # Check if the selected path is a symlink
        if os.path.islink(selected):
            # Update the UI or notify the user that the selected source is a symlink
            # and suggest removing the link
            print(f"Selected source directory: {selected}")
            self.selected_path_label.text = "Selected target is a symlink. Consider removing the link."
            # Optionally, store the symlink path or set a flag here if you need to act on this information later
            self.symlink_source = selected
        else:
             # Update the target path
            self.target_path = selected
            self.update_path_label()
       
        
    def update_path_label(self):
        # Update the label to show the selected source and target paths
        self.selected_path_label.text = f"Source: {self.source_path or 'Not selected'}\nTarget: {self.target_path or 'Not selected'}"
        # Additional UI feedback for confirmation, if necessary
        if self.source_path:
            print(f"Selected source directory: {self.source_path}")
        if self.target_path:
            print(f"Selected target directory: {self.target_path}")
    def get_drives(self):
        """List all available drives on Windows."""
        drives = [f"{drive}:\\" for drive in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists(f"{drive}:\\")]
        return drives

    def on_drive_selection(self, spinner, text):
        """Update the file chooser path based on selected drive."""
        if text:  # Ensure the text is not empty
            #print(f"Attempting to set file chooser path to: {text}")
            try:
                # Attempt to change the directory to verify the path
                os.chdir(text)  # Use the text directly since it's already correctly formatted
                # If successful, update the file chooser's path
                self.file_chooser.path = text
                #print(f"Successfully updated file chooser path to: {text}")
            except FileNotFoundError:
                print(f"The drive or path {text} does not exist.")
            except Exception as e:
                print(f"Error changing directory: {e}")
        else:
            print("No drive selected.")
    def update_selected_path_label(self, instance):
        # Update the label based on selection
        if self.file_chooser.selection:
            selected_path = self.file_chooser.selection[0]
            if os.path.islink(selected_path):
                target_path = os.readlink(selected_path)
                self.selected_path_label.text = f"Symlink target: {target_path}"
            else:
                self.selected_path_label.text = f"Selected path: {selected_path}"
        else:
            self.selected_path_label.text = "Selected path: None"
    
   
    def get_directory_size(start_path):
        """Returns the total size of all files in start_path and its subdirectories."""
        total_size = 0
        for dirpath, _dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # Skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size
    def get_free_space(path):
        """Returns the free space of the drive containing 'path'."""
        _total, _used, free = shutil.disk_usage(os.path.dirname(path))
        return free
    def prompt_for_new_location(self):
        # Implement UI logic to prompt the user for a new location and return it
        # Placeholder: actual implementation will depend on your UI design
        return '/new/path/to/location'
    def move_contents_and_create_symlink(self, instance):
        # Check if paths are set
        if not self.source_path or not self.target_path:
            self.selected_path_label.text = "Please select both source and target directories."
            return

        self.source_size = self.get_directory_size(self.source_path)
        free_space = self.get_free_space(self.target_path)

        if self.source_size > free_space:
            self.selected_path_label.text = "Not enough space on the destination drive."
            return
        
        # If there's enough space, proceed with the operation in a background thread
        threading.Thread(target=self._move_contents_thread).start()
   
    def _move_contents_thread(self):
        self.moved_files = []  # Initialize/reset the list of moved files
        total_files = len(os.listdir(self.source_path))
        moved_files_count = 0
        for item in os.listdir(self.source_path):
            source_item_path = os.path.join(self.source_path, item)
            target_item_path = os.path.join(self.target_path, item)
            shutil.move(source_item_path, target_item_path)
            self.moved_files.append(item)  # Track the moved item
            moved_files_count+=1
            progress = (moved_files_count / total_files) * 100
            Clock.schedule_once(lambda dt: self._update_progress(progress))

        # Attempt to remove the source directory and create a symlink
        try:
            os.rmdir(self.source_path)
            os.symlink(self.target_path, self.source_path)
            Clock.schedule_once(lambda dt: self._finalize_operation("Contents moved and symlink created."))
        except OSError as e:
            Clock.schedule_once(lambda dt: self._finalize_operation(f"Error: {e}"))
            Clock.schedule_once(lambda dt: self._enable_undo_button())
    def _update_progress(self, progress):
        self.progress_bar.value = progress
    def _enable_undo_button(self, *_args):
        self.undo_move_button.disabled = False
    def _finalize_operation(self, message):
        # Reset progress bar for next operation
        self.progress_bar.value = 0
        self.selected_path_label.text = message 
        # Your logic to remove the directory and create a symlink here
    def undo_move(self, instance):
        if not self.source_path or not self.target_path or not hasattr(self, 'moved_files'):
            self.selected_path_label.text = "Cannot undo move: missing source, target, or moved files list."
            return

        try:
            os.makedirs(self.source_path, exist_ok=True)  # Ensure the source directory exists
            
            # Move only the tracked files back to the source directory
            for item in self.moved_files:
                target_item_path = os.path.join(self.target_path, item)
                source_item_path = os.path.join(self.source_path, item)
                if os.path.exists(target_item_path):  # Check if the item still exists in the target
                    shutil.move(target_item_path, source_item_path)
            
            self.selected_path_label.text = "Move operation undone successfully."
        except OSError as e:
            self.selected_path_label.text = f"Failed to undo move: {e}"
        finally:
            self.undo_move_button.disabled = True  # Disable the undo button to prevent repeated undos
    def remove_symlink(self, instance):
        if self.source_path and os.path.islink(self.source_path):
            try:
                os.unlink(self.source_path)
                self.selected_path_label.text = "Symlink removed successfully."
                self.remove_symlink_button.disabled = True  # Disable the button after removal
                self.source_path = None  # Clear the source path
            except OSError as e:
                self.selected_path_label.text = f"Failed to remove symlink: {e}"
        else:
            self.selected_path_label.text = "No symlink selected."
if __name__ == '__main__':
    BigLinksApp().run()
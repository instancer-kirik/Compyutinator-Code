class ActionHandlers:
    def __init__(self, cccore):
        self.cccore = cccore

    def new_file(self):
        self.cccore.editor_manager.new_document()

    def open_file(self):
        self.cccore.file_manager.open_file()

    def save_file(self):
        self.cccore.file_manager.save_file()

    def save_file_as(self):
        self.cccore.file_manager.save_file_as()

    def close_file(self):
        self.cccore.editor_manager.close_tab(self.cccore.auratext_window.tab_widget.currentIndex())

    def close_all_files(self):
        while self.cccore.auratext_window.tab_widget.count() > 0:
            self.cccore.editor_manager.close_tab(0)

    def cut_document(self):
        if self.cccore.editor_manager.current_editor:
            self.cccore.editor_manager.current_editor.cut()

    def copy_document(self):
        if self.cccore.editor_manager.current_editor:
            self.cccore.editor_manager.current_editor.copy()

    def paste_document(self):
        if self.cccore.editor_manager.current_editor:
            self.cccore.editor_manager.current_editor.paste()

    def undo(self):
        if self.cccore.editor_manager.current_editor:
            self.cccore.editor_manager.current_editor.undo()

    def redo(self):
        if self.cccore.editor_manager.current_editor:
            self.cccore.editor_manager.current_editor.redo()

    def duplicate_line(self):
        self.cccore.editor_manager.duplicate_line()

    def pastebin(self):
        self.cccore.editor_manager.pastebin()

    def code_formatting(self):
        self.cccore.editor_manager.code_formatting()

    def goto_line(self):
        self.cccore.editor_manager.goto_line()

    def git_commit(self):
        self.cccore.git_manager.show_commit_dialog()

    def git_push(self):
        self.cccore.git_manager.push()

    def show_plugin_manager(self):
        # Implement show plugin manager functionality
        pass

    def show_settings(self):
        # Implement show settings functionality
        pass

    def show_theme_manager(self):
        # Implement show theme manager functionality
        pass

    def show_workspace_manager(self):
        # Implement show workspace manager functionality
        pass

    def show_model_manager(self):
        # Implement show model manager functionality
        pass

    def show_download_manager(self):
        # Implement show download manager functionality
        pass

    def load_layout(self):
        # Implement load layout functionality
        pass

    def show_about(self):
        # Implement show about functionality
        pass

    def add_vault_directory(self):
        self.cccore.vault_manager.add_vault_directory()

    def remove_vault_directory(self):
        self.cccore.vault_manager.remove_vault_directory()

    def set_default_vault(self):
        self.cccore.vault_manager.set_default_vault()
    def setup_powershell(self):
        # Implement the setup for Powershell
        pass
    def create_snippet(self):
        # Implement the create snippet functionality
        pass
    def edit_snippet(self):
        # Implement the edit snippet functionality
        pass
    def delete_snippet(self):
        # Implement the delete snippet functionality
        pass
    def import_snippet(self):
        # Implement the import snippet functionality
        pass
    def boilerplates(self):
        # Implement the boilerplates functionality
        pass
    def show_shortcuts(self):
        # Implement the show shortcuts functionality
        pass
    def getting_started(self):
        # Implement the getting started functionality
        pass
    def bug_report(self):
        # Implement the bug report functionality
        pass
    def discord(self):
        # Implement the discord functionality
        pass
    def buymeacoffee(self):
        # Implement the buymeacoffee functionality
        pass
    def about_github(self):
        # Implement the about github functionality
        pass
    def contribute(self):
        # Implement the contribute functionality
        pass
    def code_jokes(self):
        # Implement the code jokes functionality
        pass
    def version(self):
        # Implement the version functionality
        pass
    def notes(self):
        self.cccore.sticky_note_manager.show()
    def apply_workspace(self):
        self.cccore.widget_manager.apply_workspace() 
 

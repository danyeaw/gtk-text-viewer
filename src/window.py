from gi.repository import Gio, GLib, Gtk, GtkSource


@Gtk.Template(resource_path='/com/example/TextViewer/window.ui')
class TextViewerWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'TextViewerWindow'

    main_text_view = Gtk.Template.Child()
    open_button = Gtk.Template.Child()
    cursor_pos = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        css_provider = Gtk.CssProvider()
        css = b"""
        textview {
            font-size: 14pt;
        }
        """
        css_provider.load_from_data(css, -1)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        open_action = Gio.SimpleAction(name="open")
        open_action.connect("activate", self.open_file_dialog)
        self.add_action(open_action)

        save_action = Gio.SimpleAction(name="save-as")
        save_action.connect("activate", self.save_file_dialog)
        self.add_action(save_action)

        buffer = self.main_text_view.get_buffer()
        buffer.connect("notify::cursor-position", self.update_cursor_position)

        # Store language and style scheme managers for later use
        self.language_manager = GtkSource.LanguageManager.get_default()
        self.style_scheme_manager = GtkSource.StyleSchemeManager.get_default()
        
        # Set up initial style scheme based on dark mode
        self.settings = Gio.Settings(schema_id="com.example.TextViewer")
        self.update_style_scheme()
        
        # Connect to dark mode changes
        self.settings.connect("changed::dark-mode", self.on_dark_mode_changed)
        
        self.settings.bind("window-width", self, "default-width",
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("window-height", self, "default-height",
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("window-maximized", self, "maximized",
                           Gio.SettingsBindFlags.DEFAULT)
        
        # Store current file for language detection
        self.current_file = None
        
        # Toast message queue
        self._toast_timeout = None
        self._toast_revealer = None

    def update_style_scheme(self):
        """Update the style scheme based on current dark mode setting."""
        buffer = self.main_text_view.get_buffer()
        dark_mode = self.settings.get_boolean("dark-mode")
        if dark_mode:
            scheme = self.style_scheme_manager.get_scheme('Adwaita-dark')
        else:
            scheme = self.style_scheme_manager.get_scheme('Adwaita')
        if scheme:
            buffer.set_style_scheme(scheme)
    
    def on_dark_mode_changed(self, settings, key):
        """Called when dark mode setting changes."""
        self.update_style_scheme()
    
    def detect_language(self, file):
        """Detect and set the language based on file extension."""
        buffer = self.main_text_view.get_buffer()
        if file:
            # Get file extension
            basename = file.get_basename()
            if basename:
                # Try to guess language from filename
                language = self.language_manager.guess_language(basename, None)
                if language:
                    buffer.set_language(language)
                else:
                    buffer.set_language(None)
            else:
                buffer.set_language(None)
        else:
            buffer.set_language(None)

    def update_cursor_position(self, buffer, _):
        # Retrieve the value of the "cursor-position" property
        cursor_pos = buffer.props.cursor_position
        # Construct the text iterator for the position of the cursor
        iter = buffer.get_iter_at_offset(cursor_pos)
        line = iter.get_line() + 1
        column = iter.get_line_offset() + 1
        # Set the new contents of the label
        self.cursor_pos.set_text(f"Ln {line}, Col {column}")

    def show_toast(self, message):
        """Show a toast notification message."""
        # Remove existing toast if any
        if self._toast_timeout:
            GLib.source_remove(self._toast_timeout)
            self._toast_timeout = None
        
        # Remove existing toast widget
        if self._toast_revealer:
            self.toast_overlay.remove(self._toast_revealer)
            self._toast_revealer = None
        
        # Create toast widget
        toast_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        toast_box.set_margin_top(12)
        toast_box.set_margin_bottom(12)
        toast_box.set_margin_start(12)
        toast_box.set_margin_end(12)
        toast_box.add_css_class("toast")
        
        label = Gtk.Label(label=message)
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        toast_box.append(label)
        
        revealer = Gtk.Revealer()
        revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        revealer.set_transition_duration(200)
        revealer.set_child(toast_box)
        revealer.set_halign(Gtk.Align.CENTER)
        revealer.set_valign(Gtk.Align.END)
        revealer.set_vexpand(False)
        revealer.set_hexpand(False)
        
        self.toast_overlay.add_overlay(revealer)
        revealer.set_reveal_child(True)
        self._toast_revealer = revealer
        
        # Auto-hide after 3 seconds
        def hide_toast():
            revealer.set_reveal_child(False)
            def remove_toast():
                if self._toast_revealer == revealer:
                    self.toast_overlay.remove(revealer)
                    self._toast_revealer = None
                self._toast_timeout = None
                return False
            GLib.timeout_add(300, remove_toast)
            return False
        
        self._toast_timeout = GLib.timeout_add(3000, hide_toast)

    def open_file_dialog(self, action, _):
        # Create a new file selection dialog, using the "open" mode
        # and keep a reference to it
        self._native = Gtk.FileChooserNative(
            title="Open File",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="_Open",
            cancel_label="_Cancel",
        )
        # Connect the "response" signal of the file selection dialog;
        # this signal is emitted when the user selects a file, or when
        # they cancel the operation
        self._native.connect("response", self.on_open_response)
        # Present the dialog to the user
        self._native.show()

    def on_open_response(self, dialog, response):
        # If the user selected a file...
        if response == Gtk.ResponseType.ACCEPT:
            # ... retrieve the location from the dialog and open it
            self.open_file(dialog.get_file())
        # Release the reference on the file selection dialog now that we
        # do not need it any more
        self._native = None

    def open_file(self, file):
        file.load_contents_async(None, self.open_file_complete)

    def open_file_complete(self, file, result):
        contents = file.load_contents_finish(result)

        info = file.query_info("standard::display-name", Gio.FileQueryInfoFlags.NONE)
        if info:
            display_name = info.get_attribute_string("standard::display-name")
        else:
            display_name = file.get_basename()

        # In case of error, show a toast
        if not contents[0]:
            self.show_toast(f"Unable to open “{display_name}”")
            return

        try:
            text = contents[1].decode('utf-8')
        except UnicodeError as err:
            self.show_toast(f"Invalid text encoding for “{display_name}”")
            return

        buffer = self.main_text_view.get_buffer()
        buffer.set_text(text)
        start = buffer.get_start_iter()
        buffer.place_cursor(start)

        # Detect and set language based on file
        self.current_file = file
        self.detect_language(file)

        self.set_title(display_name)

        # Show a toast for the successful loading
        self.show_toast(f"Opened “{display_name}”")

    def save_file_dialog(self, action, _):
        self._native = Gtk.FileChooserNative(
            title="Save File As",
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
            accept_label="_Save",
            cancel_label="_Cancel",
        )
        self._native.connect("response", self.on_save_response)
        self._native.show()

    def on_save_response(self, native, response):
        if response == Gtk.ResponseType.ACCEPT:
            self.save_file(native.get_file())
        self._native = None

    def save_file(self, file):
        buffer = self.main_text_view.get_buffer()

        # Retrieve the iterator at the start of the buffer
        start = buffer.get_start_iter()
        # Retrieve the iterator at the end of the buffer
        end = buffer.get_end_iter()
        # Retrieve all the visible text between the two bounds
        text = buffer.get_text(start, end, False)

        # If there is nothing to save, return early
        if not text:
            return

        bytes = GLib.Bytes.new(text.encode('utf-8'))

        # Start the asynchronous operation to save the data into the file
        file.replace_contents_bytes_async(bytes,
                                          None,
                                          False,
                                          Gio.FileCreateFlags.NONE,
                                          None,
                                          self.save_file_complete)

    def save_file_complete(self, file, result):
        res = file.replace_contents_finish(result)
        info = file.query_info("standard::display-name",
                               Gio.FileQueryInfoFlags.NONE)
        if info:
            display_name = info.get_attribute_string("standard::display-name")
        else:
            display_name = file.get_basename()

        if not res:
            msg = f"Unable to save as “{display_name}”"
        else:
            msg = f"Saved as “{display_name}”"
        self.show_toast(msg)


class AboutDialog(Gtk.AboutDialog):

    def __init__(self, parent):
        Gtk.AboutDialog.__init__(self)
        self.props.program_name = 'text-viewer'
        self.props.version = "0.1.0"
        self.props.authors = ['Example Author']
        self.props.copyright = '2022 Example Author'
        self.props.logo_icon_name = 'com.example.TextViewer'
        self.props.modal = True
        self.set_transient_for(parent)

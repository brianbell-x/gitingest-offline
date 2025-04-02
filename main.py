import sys
import os
import shutil
import tempfile
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QTextEdit, QFileDialog, QMessageBox, QLabel,
    QSplitter, QFrame, QGroupBox, QLineEdit
)
from PyQt6.QtCore import Qt
from gitingest import ingest

class NoPartialCheckUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("No Partial Check Example")
        self.resize(900, 600)

        # --- Top row: just a "Select Directory" button ---
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(10, 10, 10, 10)

        self.btn_select_directory = QPushButton("Select Directory")
        self.btn_select_directory.clicked.connect(self.on_select_directory)
        top_layout.addWidget(self.btn_select_directory)
        top_layout.addStretch()
        self.setMenuWidget(top_widget)

        # --- Main splitter: left (directory) / right (output) ---
        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # --- Left column ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)

        # Exclusion patterns section
        exclude_layout = QHBoxLayout()
        exclude_label = QLabel("Exclude patterns:")
        self.exclude_input = QLineEdit("__pycache__, .git, .venv")
        self.exclude_input.setToolTip("Comma-separated list of directories/files to exclude")
        exclude_layout.addWidget(exclude_label)
        exclude_layout.addWidget(self.exclude_input, 1)
        left_layout.addLayout(exclude_layout)
        
        self.btn_toggle_all = QPushButton("Select All")
        self.btn_toggle_all.setCheckable(True)
        self.btn_toggle_all.setEnabled(False)
        self.btn_toggle_all.clicked.connect(self.on_toggle_all)
        left_layout.addWidget(self.btn_toggle_all, 0, Qt.AlignmentFlag.AlignLeft)

        group_directory = QGroupBox("Directory")
        group_layout = QVBoxLayout(group_directory)
        group_layout.setContentsMargins(6, 6, 6, 6)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Directory Structure")
        self.tree.itemChanged.connect(self.on_item_changed)
        self.tree.setEnabled(False)
        group_layout.addWidget(self.tree)

        left_layout.addWidget(group_directory, 1)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(separator)

        self.btn_create_ingest = QPushButton("Create Ingest")
        self.btn_create_ingest.setEnabled(False)
        self.btn_create_ingest.clicked.connect(self.on_create_ingest)
        left_layout.addWidget(self.btn_create_ingest, 0, Qt.AlignmentFlag.AlignLeft)

        splitter.addWidget(left_panel)

        # --- Right column ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)

        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(6, 6, 6, 6)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text, 1)

        copy_layout = QHBoxLayout()
        copy_layout.addStretch()
        self.btn_copy = QPushButton("Copy")
        self.btn_copy.setEnabled(False)
        self.btn_copy.clicked.connect(self.on_copy)
        copy_layout.addWidget(self.btn_copy)
        output_layout.addLayout(copy_layout)

        right_layout.addWidget(output_group, 1)
        splitter.addWidget(right_panel)

        splitter.setSizes([300, 600])
        self.selected_directory = None

    # ----------------------
    #     EVENT HANDLERS
    # ----------------------

    def on_select_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory", str(Path.home()))
        if not folder:
            return
        self.selected_directory = Path(folder)
        self.tree.clear()
        self.output_text.clear()

        self.populate_tree(folder)
        self.tree.setEnabled(True)
        self.btn_toggle_all.setEnabled(True)
        self.btn_toggle_all.setChecked(False)
        self.btn_toggle_all.setText("Select All")
        self.btn_create_ingest.setEnabled(True)
        self.btn_copy.setEnabled(False)

    def populate_tree(self, start_path):
        self.tree.blockSignals(True)
        root_item = self.create_tree_item(self.tree, start_path)
        self.traverse_dir(root_item, Path(start_path))
        self.tree.expandItem(root_item)
        self.tree.blockSignals(False)

    def create_tree_item(self, parent, path):
        name = os.path.basename(path)
        if not name:
            name = str(path)
        item = QTreeWidgetItem(parent, [name])
        item.setData(0, Qt.ItemDataRole.UserRole, str(path))
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked)
        return item

    def get_excluded_patterns(self):
        """Get the list of excluded patterns from the input field."""
        patterns = self.exclude_input.text().strip()
        if not patterns:
            return []
        return [p.strip() for p in patterns.split(',')]
    
    def is_excluded(self, path):
        """Check if a path matches any of the excluded patterns."""
        name = path.name
        excluded_patterns = self.get_excluded_patterns()
        return any(re.search(pattern, name) for pattern in excluded_patterns)
    
    def traverse_dir(self, parent_item, folder: Path):
        try:
            for entry in sorted(folder.iterdir()):
                # Skip excluded directories/files
                if self.is_excluded(entry):
                    continue
                    
                if entry.is_dir():
                    # Check for double nesting (directory with same name as parent)
                    if entry.name == folder.name:
                        # Skip the intermediate directory and add contents directly to parent
                        self.traverse_dir(parent_item, entry)
                    else:
                        child_item = self.create_tree_item(parent_item, entry)
                        self.traverse_dir(child_item, entry)
                else:
                    self.create_tree_item(parent_item, entry)
        except PermissionError:
            pass

    def on_toggle_all(self, checked):
        if checked:
            self.btn_toggle_all.setText("Deselect All")
            self.set_all_states(Qt.CheckState.Checked)
        else:
            self.btn_toggle_all.setText("Select All")
            self.set_all_states(Qt.CheckState.Unchecked)

    def set_all_states(self, state: Qt.CheckState):
        self.tree.blockSignals(True)
        root = self.tree.invisibleRootItem()
        stack = [root]
        while stack:
            parent = stack.pop()
            for i in range(parent.childCount()):
                child = parent.child(i)
                child.setCheckState(0, state)
                stack.append(child)
        self.tree.blockSignals(False)

    def on_item_changed(self, item, col):
        if col != 0:
            return
        # If the user changed a child's check state, re-sync up the tree
        state = item.checkState(0)
        self.propagate_down(item, state)
        self.propagate_up(item)

    def propagate_down(self, parent_item, state):
        """Force children to match parent's check state (no partial)."""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            child.setCheckState(0, state)
            self.propagate_down(child, state)

    def propagate_up(self, item):
        """Allow partial selection of folders."""
        parent = item.parent()
        if not parent:
            return

        # Count checked and unchecked children
        child_count = parent.childCount()
        checked_count = 0
        
        for i in range(child_count):
            st = parent.child(i).checkState(0)
            if st == Qt.CheckState.Checked:
                checked_count += 1
        
        # If ALL children are checked => parent is checked
        # Otherwise, parent stays in its current state
        if checked_count == child_count:
            parent.setCheckState(0, Qt.CheckState.Checked)
        
        # Continue propagating up the tree
        self.propagate_up(parent)

    def on_create_ingest(self):
        if not self.selected_directory:
            QMessageBox.warning(self, "No Directory", "No directory selected.")
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)
            # Get the root item (first item in tree) rather than the invisible root
            if self.tree.topLevelItemCount() > 0:
                root_item = self.tree.topLevelItem(0)
                self.copy_checked(root_item, temp_path)
                
            # Post-process to ensure no double nesting in the copied files
            self.fix_double_nesting(temp_path)
            try:
                # Run the ingest function
                _, tree_text, content_text = ingest(str(temp_path))
                
                # Now scan for unreadable files and add to the content
                unreadable_files = self.find_unreadable_files(temp_path)
                if unreadable_files:
                    content_text += "\n\n# UNREADABLE FILES\nThe following files could not be read but are included for reference:\n\n"
                    for file_path in unreadable_files:
                        rel_path = file_path.relative_to(temp_path)
                        content_text += f"- {rel_path}\n"
            except Exception as ex:
                QMessageBox.critical(self, "Ingest Error", str(ex))
                return

            final = "<codebase>\n\n" + tree_text + "\n\n" + content_text + "</codebase>"
            self.output_text.setPlainText(final)
            self.btn_copy.setEnabled(True)

    def find_unreadable_files(self, directory: Path):
        """Find files that cannot be read as text.
        
        Args:
            directory: The directory to scan for unreadable files
            
        Returns:
            List of Path objects for files that cannot be read as text
        """
        unreadable_files = []
        
        # Skip these extensions that are known to be binary files
        binary_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.zip', 
                             '.exe', '.dll', '.bin', '.dat', '.db', '.sqlite',
                             '.pyc', '.pyo', '.so', '.o', '.a', '.lib', '.dylib']
        
        for file_path in directory.glob('**/*'):
            if file_path.is_file():
                # Skip files with known binary extensions
                if file_path.suffix.lower() in binary_extensions:
                    unreadable_files.append(file_path)
                    continue
                    
                # Try to read the file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        # Just read a small part to check if it's readable
                        f.read(1024)
                except (UnicodeDecodeError, PermissionError):
                    unreadable_files.append(file_path)
        
        return unreadable_files
    
    def copy_checked(self, parent_item, dest: Path):
        """Copy only checked items to `dest`."""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            path_str = child.data(0, Qt.ItemDataRole.UserRole)
            if not path_str:
                continue
            orig_path = Path(path_str)
            if child.checkState(0) == Qt.CheckState.Unchecked:
                continue

            rel = orig_path.relative_to(self.selected_directory)
            
            # Check if this directory would create a double nesting
            if orig_path.is_dir() and orig_path.name == orig_path.parent.name:
                # If so, flatten the path by removing the duplicate directory name
                parts = list(rel.parts)
                # Find the duplicate name and skip it in the path construction
                for j in range(1, len(parts)):
                    if parts[j] == parts[j-1]:
                        # Create a new path without the duplicate part
                        rel = Path(*parts[:j] + parts[j+1:]) if j+1 < len(parts) else Path(*parts[:j])
                        break
            
            target = dest / rel
            if orig_path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                self.copy_checked(child, target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(orig_path, target)

    def fix_double_nesting(self, directory: Path):
        """Recursively scan for and fix double-nested directories.
        
        Args:
            directory: The root directory to scan for double nesting
        """
        # Get all subdirectories
        subdirs = [d for d in directory.iterdir() if d.is_dir()]
        
        for subdir in subdirs:
            # Check if this directory contains a nested directory with the same name
            nested_same_name = subdir / subdir.name
            if nested_same_name.exists() and nested_same_name.is_dir():
                # Found a double-nested directory - move all its contents to parent
                for item in nested_same_name.iterdir():
                    # Determine target path in the parent directory
                    target = subdir / item.name
                    
                    # Handle name conflicts
                    if target.exists():
                        # If target already exists and is a directory, merge the contents
                        if target.is_dir() and item.is_dir():
                            # Recursively copy contents
                            for nested_item in item.iterdir():
                                nested_target = target / nested_item.name
                                if nested_item.is_dir():
                                    shutil.copytree(nested_item, nested_target, dirs_exist_ok=True)
                                else:
                                    shutil.copy2(nested_item, nested_target)
                        # Otherwise (file or different type), add a suffix to avoid conflicts
                        else:
                            counter = 1
                            while target.exists():
                                new_name = f"{item.stem}_{counter}{item.suffix}"
                                target = subdir / new_name
                                counter += 1
                            # Now target doesn't exist, so we can copy/move
                            if item.is_dir():
                                shutil.copytree(item, target)
                            else:
                                shutil.copy2(item, target)
                    else:
                        # No conflict, directly move the item
                        if item.is_dir():
                            shutil.copytree(item, target, dirs_exist_ok=True)
                        else:
                            shutil.copy2(item, target)
                
                # Remove the now-processed nested directory
                shutil.rmtree(nested_same_name)
            
            # Recursively process all subdirectories
            if subdir.exists():  # Check it still exists (might have been removed in processing)
                self.fix_double_nesting(subdir)

    def on_copy(self):
        txt = self.output_text.toPlainText().strip()
        if not txt:
            QMessageBox.warning(self, "Nothing to Copy", "No output to copy.")
            return
        QApplication.clipboard().setText(txt)
        QMessageBox.information(self, "Copied", "Output has been copied to clipboard.")

def main():
    app = QApplication(sys.argv)
    window = NoPartialCheckUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

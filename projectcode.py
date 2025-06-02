import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pymongo
from pymongo import MongoClient
import pandas as pd
from cryptography.fernet import Fernet
import datetime
import win32api
import win32con
from pathlib import Path

class ImprovedFileManager:
    def __init__(self):
        # Initialize database connection
        self.mongodb_password = "see@mongodb"
        try:
            self.client = MongoClient('mongodb://localhost:27017/')           
            self.db = self.client['file_manager']
            self.collection = self.db['renamed_files']
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not connect to MongoDB: {str(e)}")
        
        # Initialize or load encryption key
        key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.encryption_key')
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(self.key)
        
        self.cipher_suite = Fernet(self.key)
        
        # Initialize main window
        self.root = tk.Tk()
        self.root.title("Improved File Manager")
        self.root.geometry("600x400")
        
        # Current folder variables
        self.current_folder = tk.StringVar()
        self.folder_password = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Folder selection
        ttk.Label(main_frame, text="Current Folder:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(main_frame, textvariable=self.current_folder, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.select_folder).grid(row=0, column=2)
        
        # Action buttons frame
        actions_frame = ttk.LabelFrame(main_frame, text="Actions", padding="10")
        actions_frame.grid(row=1, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        # File operations
        ttk.Button(actions_frame, text="Lock Folder", command=self.lock_folder).grid(row=0, column=0, padx=5)
        ttk.Button(actions_frame, text="Unlock Folder", command=self.unlock_folder_dialog).grid(row=0, column=1, padx=5)
        ttk.Button(actions_frame, text="Change Password", command=self.change_password_dialog).grid(row=0, column=2, padx=5)
        ttk.Button(actions_frame, text="Rename Files", command=self.show_rename_dialog).grid(row=0, column=3, padx=5)
        ttk.Button(actions_frame, text="View History", command=self.view_history).grid(row=0, column=4, padx=5)
        
        # Status frame
        self.status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        self.status_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.grid(row=0, column=0)
        
    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            self.current_folder.set(folder)
            self.check_folder_status()
    
    def check_folder_status(self):
        folder = self.current_folder.get()
        if not folder:
            return
            
        password_file = os.path.join(folder, '.password')
        if os.path.exists(password_file):
            self.status_label.config(text="Folder is password protected")
        else:
            self.status_label.config(text="Folder is not protected")
    
    def set_folder_password(self, password):
        folder = self.current_folder.get()
        if not folder:
            messagebox.showerror("Error", "No folder selected!")
            return False
            
        try:
            with open(os.path.join(folder, '.password'), 'wb') as f:
                encrypted_password = self.cipher_suite.encrypt(password.encode())
                f.write(encrypted_password)
            self.folder_password = password
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Could not set password: {str(e)}")
            return False
    
    def verify_folder_password(self, password):
        folder = self.current_folder.get()
        try:
            with open(os.path.join(folder, '.password'), 'rb') as f:
                stored_password = self.cipher_suite.decrypt(f.read()).decode()
                return stored_password == password
        except:
            return False
    
    def lock_folder(self):
        folder = self.current_folder.get()
        if not folder:
            messagebox.showerror("Error", "No folder selected!")
            return
            
        if not os.path.exists(os.path.join(folder, '.password')):
            self.set_initial_password()
            return
            
        try:
            win32api.SetFileAttributes(folder, 
                                     win32con.FILE_ATTRIBUTE_HIDDEN | 
                                     win32con.FILE_ATTRIBUTE_SYSTEM)
            self.status_label.config(text="Folder locked successfully")
            messagebox.showinfo("Success", "Folder locked successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not lock folder: {str(e)}")
    
    def set_initial_password(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Set Folder Password")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        
        frame = ttk.Frame(dialog, padding="20")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(frame, text="New Password:").grid(row=0, column=0, pady=5)
        password = ttk.Entry(frame, show="*")
        password.grid(row=0, column=1, pady=5)
        
        ttk.Label(frame, text="Confirm Password:").grid(row=1, column=0, pady=5)
        confirm = ttk.Entry(frame, show="*")
        confirm.grid(row=1, column=1, pady=5)
        
        def save_password():
            if len(password.get()) < 4:
                messagebox.showerror("Error", "Password must be at least 4 characters!")
                return
                
            if password.get() != confirm.get():
                messagebox.showerror("Error", "Passwords do not match!")
                return
                
            if self.set_folder_password(password.get()):
                self.lock_folder()
                dialog.destroy()
        
        ttk.Button(frame, text="Set Password", command=save_password).grid(row=2, column=0, columnspan=2, pady=10)
        
        dialog.grab_set()
        password.focus()
    
    def unlock_folder_dialog(self):
        folder = self.current_folder.get()
        if not folder:
            messagebox.showerror("Error", "No folder selected!")
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Unlock Folder")
        dialog.geometry("300x120")
        dialog.transient(self.root)
        
        frame = ttk.Frame(dialog, padding="20")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(frame, text="Password:").grid(row=0, column=0, pady=5)
        password = ttk.Entry(frame, show="*")
        password.grid(row=0, column=1, pady=5)
        
        def unlock():
            if self.verify_folder_password(password.get()):
                try:
                    win32api.SetFileAttributes(folder, win32con.FILE_ATTRIBUTE_NORMAL)
                    self.status_label.config(text="Folder unlocked successfully")
                    messagebox.showinfo("Success", "Folder unlocked successfully!")
                    dialog.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Could not unlock folder: {str(e)}")
            else:
                messagebox.showerror("Error", "Incorrect password!")
        
        ttk.Button(frame, text="Unlock", command=unlock).grid(row=1, column=0, columnspan=2, pady=10)
        
        dialog.grab_set()
        password.focus()
    
    def change_password_dialog(self):
        folder = self.current_folder.get()
        if not folder:
            messagebox.showerror("Error", "No folder selected!")
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Change Password")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        
        frame = ttk.Frame(dialog, padding="20")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Current password frame
        current_frame = ttk.LabelFrame(frame, text="Current Password", padding="10")
        current_frame.grid(row=0, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Label(current_frame, text="Password:").grid(row=0, column=0, pady=5)
        current_password = ttk.Entry(current_frame, show="*")
        current_password.grid(row=0, column=1, pady=5)
        
        # New password frame
        new_frame = ttk.LabelFrame(frame, text="New Password", padding="10")
        new_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Label(new_frame, text="New Password:").grid(row=0, column=0, pady=5)
        new_password = ttk.Entry(new_frame, show="*")
        new_password.grid(row=0, column=1, pady=5)
        
        ttk.Label(new_frame, text="Confirm:").grid(row=1, column=0, pady=5)
        confirm_password = ttk.Entry(new_frame, show="*")
        confirm_password.grid(row=1, column=1, pady=5)
        
        def change():
            if not self.verify_folder_password(current_password.get()):
                messagebox.showerror("Error", "Current password is incorrect!")
                return
                
            if new_password.get() != confirm_password.get():
                messagebox.showerror("Error", "New passwords do not match!")
                return
                
            if self.set_folder_password(new_password.get()):
                messagebox.showinfo("Success", "Password changed successfully!")
                dialog.destroy()

        def forgot_password():
            # Create forgot password dialog
            forgot_dialog = tk.Toplevel(dialog)
            forgot_dialog.title("Reset Password")
            forgot_dialog.geometry("300x180")
            forgot_dialog.transient(dialog)
            
            forgot_frame = ttk.Frame(forgot_dialog, padding="20")
            forgot_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            ttk.Label(forgot_frame, text="Database Password:").grid(row=0, column=0, pady=5)
            db_password = ttk.Entry(forgot_frame, show="*")
            db_password.grid(row=0, column=1, pady=5)
            
            ttk.Label(forgot_frame, text="New Password:").grid(row=1, column=0, pady=5)
            reset_password = ttk.Entry(forgot_frame, show="*")
            reset_password.grid(row=1, column=1, pady=5)
            
            ttk.Label(forgot_frame, text="Confirm Password:").grid(row=2, column=0, pady=5)
            reset_confirm = ttk.Entry(forgot_frame, show="*")
            reset_confirm.grid(row=2, column=1, pady=5)
            
            def reset():
                if db_password.get() != self.mongodb_password:
                    messagebox.showerror("Error", "Incorrect database password!")
                    return
                    
                if reset_password.get() != reset_confirm.get():
                    messagebox.showerror("Error", "New passwords do not match!")
                    return
                    
                if self.set_folder_password(reset_password.get()):
                    messagebox.showinfo("Success", "Password reset successfully!")
                    forgot_dialog.destroy()
                    dialog.destroy()

            # Add Enter key bindings for reset password dialog
            def on_reset_enter(event):
                reset()

            db_password.bind('<Return>', lambda e: reset_password.focus())
            reset_password.bind('<Return>', lambda e: reset_confirm.focus())
            reset_confirm.bind('<Return>', on_reset_enter)
            
            ttk.Button(forgot_frame, text="Reset Password", command=reset).grid(row=3, column=0, columnspan=2, pady=10)
            forgot_dialog.grab_set()
            db_password.focus()
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Change Password", command=change).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Forgot Password", command=forgot_password).grid(row=0, column=1, padx=5)

        # Add Enter key bindings for change password dialog
        def on_change_enter(event):
            change()

        current_password.bind('<Return>', lambda e: new_password.focus())
        new_password.bind('<Return>', lambda e: confirm_password.focus())
        confirm_password.bind('<Return>', on_change_enter)
        
        dialog.grab_set()
        current_password.focus()
    
    def show_rename_dialog(self):
        folder = self.current_folder.get()
        if not folder:
            messagebox.showerror("Error", "No folder selected!")
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Rename Files")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        
        frame = ttk.Frame(dialog, padding="20")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(frame, text="Prefix:").grid(row=0, column=0, pady=5)
        prefix = ttk.Entry(frame)
        prefix.grid(row=0, column=1, pady=5)
        
        ttk.Label(frame, text="Suffix:").grid(row=1, column=0, pady=5)
        suffix = ttk.Entry(frame)
        suffix.grid(row=1, column=1, pady=5)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(frame, text="Preview", padding="10")
        preview_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        preview_text = tk.Text(preview_frame, height=8, width=40)
        preview_text.grid(row=0, column=0)
        
        def update_preview(*args):
            preview_text.delete(1.0, tk.END)
            try:
                files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f != '.password']
                for i, filename in enumerate(files[:5]):
                    name, ext = os.path.splitext(filename)
                    new_name = f"{prefix.get()}{name}{suffix.get()}{ext}"
                    preview_text.insert(tk.END, f"{filename} → {new_name}\n")
                if len(files) > 5:
                    preview_text.insert(tk.END, f"\n... and {len(files)-5} more files")
            except Exception as e:
                preview_text.insert(tk.END, f"Error: {str(e)}")
        
        prefix.bind('<KeyRelease>', update_preview)
        suffix.bind('<KeyRelease>', update_preview)
        update_preview()
        
        def rename_files():
            try:
                renamed = []
                files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f != '.password']
                for filename in files:
                    name, ext = os.path.splitext(filename)
                    new_name = f"{prefix.get()}{name}{suffix.get()}{ext}"
                    old_path = os.path.join(folder, filename)
                    new_path = os.path.join(folder, new_name)
                    
                    os.rename(old_path, new_path)
                    
                    file_info = {
                        "original_name": filename,
                        "new_name": new_name,
                        "timestamp": datetime.datetime.now(),
                        "folder_path": folder
                    }
                    renamed.append(file_info)
                
                if renamed:
                    self.collection.insert_many(renamed)
                    messagebox.showinfo("Success", f"Renamed {len(renamed)} files successfully!")
                    dialog.destroy()
                else:
                    messagebox.showinfo("Info", "No files to rename!")
            except Exception as e:
                messagebox.showerror("Error", f"Error renaming files: {str(e)}")
        
        ttk.Button(frame, text="Rename Files", command=rename_files).grid(row=3, column=0, columnspan=2, pady=10)
  
        dialog.grab_set()

    def view_history(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("View History")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        
        frame = ttk.Frame(dialog, padding="20")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(frame, text="Database Password:").grid(row=0, column=0, pady=5)
        password = ttk.Entry(frame, show="*")
        password.grid(row=0, column=1, pady=5)
        
        # Create treeview
        columns = ("Original Name", "New Name", "Timestamp", "Folder")
        tree = ttk.Treeview(frame, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        tree.grid(row=1, column=0, columnspan=2, pady=10)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.grid(row=1, column=2, sticky='ns')
        tree.configure(yscrollcommand=scrollbar.set)
        
        def view_records():
            if password.get() != self.mongodb_password:
                messagebox.showerror("Error", "Incorrect database password!")
                return
                
            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)
                
            try:
                data = list(self.collection.find({}, {'_id': 0}))
                for record in data:
                    tree.insert('', tk.END, values=(
                        record['original_name'],
                        record['new_name'],
                        record['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                        record['folder_path']
                    ))
            except Exception as e:
                messagebox.showerror("Error", f"Could not fetch records: {str(e)}")
        
        ttk.Button(frame, text="View Records", command=view_records).grid(row=2, column=0, columnspan=2, pady=10)
        
        dialog.grab_set()
        password.focus()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ImprovedFileManager()
    app.run()

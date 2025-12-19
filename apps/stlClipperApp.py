import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
import os

# Import your STLClipper class here (assume it's in the same file or import as needed)
from stlClipper import STLClipper  # Make sure stlClipper.py with STLClipper class is available in the same directory

class STLClipperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("STL Clipper")
        self.root.geometry("800x400")
        self.root.minsize(600, 300)
        
        # Configure root grid weights for responsiveness
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        self.clipper = STLClipper()
        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.clip_bounds = [tk.StringVar() for _ in range(6)]
        self.output_ascii = tk.BooleanVar(value=False)

        # Configure ttk style for modern appearance
        self.style = ttk.Style()
        self.configure_styles()
        
        self.build_gui()

    def configure_styles(self):
        """Configure modern ttk styles"""
        self.style.theme_use('clam')  # Use a modern theme
        
        # Configure custom styles
        self.style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        self.style.configure('Action.TButton', font=('Arial', 10, 'bold'))
        
    def build_gui(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure main frame grid weights
        main_frame.columnconfigure(1, weight=1)  # Entry column expands
        
        # Title
        title_label = ttk.Label(main_frame, text="STL Clipper", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Input file section
        input_frame = ttk.LabelFrame(main_frame, text="Input File", padding="10")
        input_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)
        
        ttk.Label(input_frame, text="STL file:").grid(row=0, column=0, sticky="e", padx=(0, 5))
        input_entry = ttk.Entry(input_frame, textvariable=self.input_file)
        input_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        ttk.Button(input_frame, text="Browse...", command=self.browse_input).grid(row=0, column=2)

        # Output file section
        output_frame = ttk.LabelFrame(main_frame, text="Output File", padding="10")
        output_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="STL file:").grid(row=0, column=0, sticky="e", padx=(0, 5))
        output_entry = ttk.Entry(output_frame, textvariable=self.output_file)
        output_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        ttk.Button(output_frame, text="Browse...", command=self.browse_output).grid(row=0, column=2)

        # Clipping bounds section
        bounds_frame = ttk.LabelFrame(main_frame, text="Clipping Bounds", padding="10")
        bounds_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        # Configure bounds frame for responsive layout
        for i in range(6):
            bounds_frame.columnconfigure(i, weight=1)

        # Bounds labels and entries
        bounds_labels = ["X Min", "Y Min", "Z Min", "X Max", "Y Max", "Z Max"]
        
        # Create a sub-frame for better organization
        bounds_grid = ttk.Frame(bounds_frame)
        bounds_grid.grid(row=0, column=0, sticky="ew")
        bounds_frame.columnconfigure(0, weight=1)
        
        for i in range(6):
            bounds_grid.columnconfigure(i, weight=1)
            
        for i, label_text in enumerate(bounds_labels):
            col = i % 3
            row = i // 3
            
            # Label
            ttk.Label(bounds_grid, text=label_text).grid(
                row=row*2, column=col, sticky="ew", padx=2, pady=(0, 2)
            )
            
            # Entry
            entry = ttk.Entry(bounds_grid, textvariable=self.clip_bounds[i], width=12)
            entry.grid(row=row*2+1, column=col, sticky="ew", padx=2, pady=(0, 5))

        # Options section
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        ttk.Checkbutton(options_frame, text="Output ASCII STL format", 
                       variable=self.output_ascii).grid(row=0, column=0, sticky="w")

        # Action buttons section
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=5, column=0, columnspan=3, pady=(10, 0))
        
        # Progress bar (initially hidden)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(action_frame, variable=self.progress_var, 
                                          mode='indeterminate')
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.progress_bar.grid_remove()  # Hide initially
        
        # Buttons
        button_frame = ttk.Frame(action_frame)
        button_frame.grid(row=1, column=0, columnspan=2)
        
        ttk.Button(button_frame, text="Clear All", command=self.clear_all).grid(
            row=0, column=0, padx=(0, 10))
        
        clip_button = ttk.Button(button_frame, text="Clip STL", command=self.run_clipping, 
                               style='Action.TButton')
        clip_button.grid(row=0, column=1)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(20, 0))
        status_frame.columnconfigure(0, weight=1)
        
        ttk.Separator(status_frame, orient='horizontal').grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ttk.Label(status_frame, textvariable=self.status_var, relief='sunken', 
                 padding="5").grid(row=1, column=0, sticky="ew")

    def update_status(self, message):
        """Update status bar message"""
        self.status_var.set(message)
        self.root.update_idletasks()

    def show_progress(self, show=True):
        """Show or hide progress bar"""
        if show:
            self.progress_bar.grid()
            self.progress_bar.start(10)
        else:
            self.progress_bar.stop()
            self.progress_bar.grid_remove()

    def clear_all(self):
        """Clear all input fields"""
        self.input_file.set("")
        self.output_file.set("")
        for var in self.clip_bounds:
            var.set("")
        self.output_ascii.set(False)
        self.update_status("Fields cleared")

    def browse_input(self):
        filename = filedialog.askopenfilename(
            title="Select Input STL File",
            filetypes=[("STL files", "*.stl"), ("All files", "*.*")]
        )
        if filename:
            self.input_file.set(filename)
            self.update_status(f"Input file selected: {os.path.basename(filename)}")

    def browse_output(self):
        filename = filedialog.asksaveasfilename(
            title="Save Clipped STL File",
            defaultextension=".stl",
            filetypes=[("STL files", "*.stl"), ("All files", "*.*")]
        )
        if filename:
            self.output_file.set(filename)
            self.update_status(f"Output file set: {os.path.basename(filename)}")

    def validate_inputs(self):
        """Validate all inputs before processing"""
        input_path = self.input_file.get().strip()
        output_path = self.output_file.get().strip()
        
        if not input_path:
            messagebox.showerror("Error", "Please select an input STL file.")
            return False
            
        if not output_path:
            messagebox.showerror("Error", "Please specify an output STL file.")
            return False
        
        if not os.path.exists(input_path):
            messagebox.showerror("Error", f"Input file not found:\n{input_path}")
            return False
            
        # Validate bounds
        try:
            bounds = []
            for i, var in enumerate(self.clip_bounds):
                value = var.get().strip()
                if not value:
                    messagebox.showerror("Error", f"Please enter a value for bound {i+1}.")
                    return False
                bounds.append(float(value))
            
            # Check if bounds make sense
            if bounds[0] >= bounds[3] or bounds[1] >= bounds[4] or bounds[2] >= bounds[5]:
                messagebox.showerror("Error", "Invalid bounds: min values must be less than max values.")
                return False
                
        except ValueError:
            messagebox.showerror("Error", "All clipping bounds must be valid numbers.")
            return False
            
        return True

    def run_clipping(self):
        if not self.validate_inputs():
            return
            
        input_path = self.input_file.get().strip()
        output_path = self.output_file.get().strip()
        bounds = [float(var.get().strip()) for var in self.clip_bounds]
        
        try:
            self.show_progress(True)
            self.update_status("Reading STL file...")
            
            if not self.clipper.read_stl(input_path):
                messagebox.showerror("Error", "Failed to read input STL file.")
                return

            self.update_status("Clipping triangles...")
            clip_min = np.array(bounds[:3])
            clip_max = np.array(bounds[3:])
            self.clipper.clip_to_bounds(clip_min, clip_max)

            if len(self.clipper.triangles) == 0:
                messagebox.showwarning("Warning", "No triangles remain after clipping!")
                self.update_status("Warning: No triangles after clipping")
                return

            self.update_status("Writing output file...")
            if self.output_ascii.get():
                success = self.clipper.write_stl_ascii(output_path)
            else:
                success = self.clipper.write_stl_binary(output_path)

            if success:
                remaining_triangles = len(self.clipper.triangles)
                message = f"Successfully clipped STL!\n\nOutput: {output_path}\nTriangles remaining: {remaining_triangles}"
                messagebox.showinfo("Success", message)
                self.update_status(f"Success: {remaining_triangles} triangles written to {os.path.basename(output_path)}")
            else:
                messagebox.showerror("Error", "Failed to write output STL file.")
                self.update_status("Error: Failed to write output file")
                
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred:\n{str(e)}")
            self.update_status(f"Error: {str(e)}")
        finally:
            self.show_progress(False)

if __name__ == "__main__":
    root = tk.Tk()
    app = STLClipperApp(root)
    root.mainloop()
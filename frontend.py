import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import automate
import os
import shutil
import clustering
import threading

class SEOAppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SEO CSV Processor")

        self.step1_files = []
        self.step2_files = []

        self.merged_blob = None

        # === Step 1 UI ===
        tk.Label(root, text="Step 1: Upload Google Ads + Search Console CSVs").pack(pady=5)

        self.step1_btn = tk.Button(root, text="Select 2 CSVs", command=self.select_step1_files)
        self.step1_btn.pack()

        self.upload_merge_btn = tk.Button(root, text="Upload and Merge", command=self.upload_and_merge)
        self.upload_merge_btn.pack(pady=5)

        self.download_btn = tk.Button(root, text="Download Merged File", command=self.download_merged_file)
        self.download_btn.pack(pady=5)
        self.download_btn.config(state='disabled')
        

        # === Step 2 UI ===
        tk.Label(root, text="Step 2: Upload Merged File + Volume CSV").pack(pady=10)

        self.step2_btn = tk.Button(root, text="Select Merged + Volume CSV", command=self.select_step2_files)
        self.step2_btn.pack()

        self.generate_btn = tk.Button(root, text="Generate Prompts", command=self.generate_prompts)
        self.generate_btn.pack(pady=5)

        # === TreeView Output ===
        self.tree = ttk.Treeview(root)
        self.tree["columns"] = ("Prompt",)
        self.tree.column("#0", width=200)
        self.tree.column("Prompt", width=500)
        self.tree.heading("#0", text="Term")
        self.tree.heading("Prompt", text="Prompt")
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)
        self.tree.bind("<Double-1>", self.copy_prompt)
        tk.Label(root, text="Step 3: Cluster, Split, Zip merged CSV").pack(pady=10)
        self.cluster_split_btn = tk.Button(root, text="Cluster + Split + Zip", command=self.cluster_and_split)
        self.cluster_split_btn.pack(pady=5)
        self.zip_path = None

        self.save_zip_btn = tk.Button(root, text="Save Cluster ZIP", command=self.save_zip_file)
        self.save_zip_btn.pack(pady=5)
        self.save_zip_btn.config(state='disabled')

        # Add Step 4 UI (select split CSV files, generate prompts)
        tk.Label(root, text="Step 4: Select cluster CSVs and generate prompts").pack(pady=10)
        self.select_cluster_files_btn = tk.Button(root, text="Select Cluster CSV Files", command=self.select_cluster_files)
        self.select_cluster_files_btn.pack()
        self.cluster_files = []
    def cluster_and_split(self):
        if not self.merged_blob:
            messagebox.showerror("Error", "No merged CSV loaded yet.")
            return

        temp_merged_path = "temp_merged.csv"
        with open(temp_merged_path, "wb") as f:
            f.write(self.merged_blob)

        automate.split_by_clinic_and_zip(temp_merged_path)

        self.zip_path = 'clinic_location_files.zip'
        self.save_zip_btn.config(state='normal')
        messagebox.showinfo("Done", "Clustered, split and zipped merged CSV!")

    def save_zip_file(self):
        if not self.zip_path or not os.path.exists(self.zip_path):
            messagebox.showerror("Error", "No ZIP file found.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP files", "*.zip")])
        if path:
            shutil.copy(self.zip_path, path)
            messagebox.showinfo("Saved", f"ZIP saved to {path}")

    def select_cluster_files(self):
        files = filedialog.askopenfilenames(filetypes=[("CSV Files", "*.csv")])
        if not files:
            return
        self.cluster_files = list(files)
        self.generate_prompts_for_clusters()

    def generate_prompts_for_clusters(self):
        if not self.cluster_files:
            messagebox.showerror("Error", "No cluster CSV files selected.")
            return
        def worker():
            self.tree.delete(*self.tree.get_children())
            print("Worker started generating prompts...")
            for file in self.cluster_files:
                try:
                    print(f"Processing file: {file}")
                    with open(file, "rb") as f:
                        content_bytes = f.read()
                        prompt_text = clustering.process_file(content_bytes)
                        print(f"Generated prompt for {file}: {prompt_text[:60]}...")  # print start of prompt
                        self.root.after(0, lambda t=os.path.basename(file), p=prompt_text: self.tree.insert("", "end", text=t, values=(p,)))
                except Exception as e:
                    print(f"Error processing {file}: {e}")
                    self.root.after(0, lambda f=file, e=e: self.tree.insert("", "end", text=f"Error in {os.path.basename(f)}", values=(str(e),)))
                    print("Worker finished.")
        threading.Thread(target=worker).start()


    def select_step1_files(self):
        self.step1_files = list(filedialog.askopenfilenames(filetypes=[("CSV Files", "*.csv")]))
        if len(self.step1_files) != 2:
            messagebox.showerror("Error", "Please select exactly 2 CSV files.")
            self.step1_files = []
        

    def upload_and_merge(self):
        if len(self.step1_files) != 2:
            messagebox.showerror("Error", "Select files first.")
            return None  # Early return on error 
        merged_file_path = automate.merge_and_categorize(self.step1_files[0], self.step1_files[1])
        with open(merged_file_path, "rb") as f:
            self.merged_blob = f.read()
        self.download_btn.config(state='normal')
        return merged_file_path

        

    def download_merged_file(self):
        if not self.merged_blob:
            messagebox.showerror("Error", "No merged file to download.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if path:
            with open(path, "wb") as f:
                f.write(self.merged_blob)
                messagebox.showinfo("Saved", f"Merged file saved to {path}")

    def select_step2_files(self):
        self.step2_files = filedialog.askopenfilenames(filetypes=[("CSV Files", "*.csv")])
        if len(self.step2_files) != 2:
            messagebox.showerror("Error", "Select merged + volume CSV.")
            self.step2_files = []

    def generate_prompts(self):
        if len(self.step2_files) != 2:
            messagebox.showerror("Error", "Upload both required files first.")
            return

        # Fake prompts for demonstration
        data = [
            {"term": "Dental Implants", "prompt": "Create a blog on dental implants benefits."},
            {"term": "Teeth Whitening", "prompt": "Add a meta title focused on results."}
        ]

        self.tree.delete(*self.tree.get_children())
        for item in data:
            self.tree.insert("", "end", text=item["term"], values=(item["prompt"],))

    def copy_prompt(self, event):
        selected_item = self.tree.focus()
        if selected_item:
            prompt = self.tree.item(selected_item, "values")[0]
            self.root.clipboard_clear()
            self.root.clipboard_append(prompt)
            messagebox.showinfo("Copied", "Prompt copied to clipboard!")

if __name__ == "__main__":
    root = tk.Tk()
    app = SEOAppGUI(root)
    root.mainloop()

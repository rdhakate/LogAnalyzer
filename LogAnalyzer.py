## Copyright 2025
## Authour: Rahul A. Dhakate
## Created for Log analysis and CSV file log parsing for Amla Commerce. 
##
##


import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import re
import os
from collections import defaultdict
import csv
from tkinter import scrolledtext
from fpdf import FPDF
from datetime import datetime
from difflib import SequenceMatcher

class LogAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Log Analyzer")
        self.root.geometry("1000x700")
        self.issues = []
        self.issue_counts = defaultdict(int)
        self.issue_dates = {}
        self.unique_issues = []
        self.similarity_threshold = 0.85

        self.create_menu()
        self.create_widgets()
        self.create_status_bar()

    #Creating menu bar
    def create_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open", command=self.load_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        export_menu = tk.Menu(menubar, tearoff=0)
        export_menu.add_command(label="Export RCA as CSV", command=self.export_rca_csv)
        export_menu.add_command(label="Export RCA as Text", command=self.export_rca_text)
        export_menu.add_command(label="Export RCA as PDF", command=self.export_rca_pdf)
        menubar.add_cascade(label="Export", menu=export_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    # Creating widgets through tk
    def create_widgets(self):
        main_pane = ttk.Panedwindow(self.root, orient=tk.VERTICAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        top_pane = ttk.Panedwindow(main_pane, orient=tk.HORIZONTAL)
        main_pane.add(top_pane, weight=3)

        bottom_frame = ttk.Frame(main_pane)
        main_pane.add(bottom_frame, weight=1)

        left_frame = ttk.Frame(top_pane)
        top_pane.add(left_frame, weight=2)

        columns = ("Issue", "Priority", "Count", "Date")
        self.tree = ttk.Treeview(left_frame, columns=columns, show='headings')
        for col in columns:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_tree(_col, False))
            self.tree.column(col, anchor=tk.W)

        tree_scroll_y = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(left_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.tree.pack(fill=tk.BOTH, expand=True, pady=5, side=tk.LEFT)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<<TreeviewSelect>>", self.on_issue_select)

        right_frame = ttk.Frame(top_pane)
        top_pane.add(right_frame, weight=3)

        ttk.Label(right_frame, text="Issue Details:").pack(anchor='w', padx=5, pady=5)
        self.details_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, height=10)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(bottom_frame, text="Root Cause Analysis:").pack(anchor='w', padx=5, pady=5)
        self.rca_text = scrolledtext.ScrolledText(bottom_frame, wrap=tk.WORD, height=10, bg="white")
        self.rca_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def create_status_bar(self):
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.progress_analysis = ttk.Progressbar(self.status_frame, orient='horizontal', mode='determinate')
        self.progress_analysis.pack(fill=tk.X, padx=5, pady=2, expand=True)

        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)

    def show_about(self):
        messagebox.showinfo("About", "Log Analyzer\nVersion 1.0\n(c) 2025 Made for Amla Commerce\nAuthor: Rahul Arun Dhakate")

    #Opening the file using wildcards for only .log and .csv
    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Log and CSV files", "*.log *.csv")])
        if file_path:
            threading.Thread(target=self.analyze_file, args=(file_path,), daemon=True).start()

    def is_similar(self, a, b):
        return SequenceMatcher(None, a, b).ratio() > self.similarity_threshold

    def analyze_file(self, file_path):
        try:
            self.update_status("Analyzing file...")
            self.progress_analysis["value"] = 0
            self.clear_tree()
            self.details_text.delete(1.0, tk.END)
            self.rca_text.delete(1.0, tk.END)
            self.issue_counts.clear()
            self.issues.clear()
            self.issue_dates.clear()
            self.unique_issues.clear()

            error_patterns = [
                (r"Exception", "High"),
                (r"ERROR", "High"),
                (r"Critical", "High"),
                (r"Warning", "Medium"),
                (r"Timeout", "Medium"),
                (r"Failed", "Medium"),
                (r"Info", "Low"),
            ]

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                total_lines = len(lines)

                for index, line in enumerate(lines):
                    timestamp = datetime.now().strftime("%Y-%m-%d")
                    for pattern, priority in error_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            cleaned = line.strip()
                            found_similar = False
                            for (existing, existing_priority) in self.unique_issues:
                                if self.is_similar(existing, cleaned):
                                    self.issue_counts[(existing, existing_priority)] += 1
                                    found_similar = True
                                    break
                            if not found_similar:
                                self.unique_issues.append((cleaned, priority))
                                self.issue_counts[(cleaned, priority)] = 1
                                self.issue_dates[(cleaned, priority)] = timestamp
                            break
                    self.update_progress(index + 1, total_lines)

            self.display_issues()
            self.update_status(f"Analysis complete. Found {len(self.issue_counts)} unique issues.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.update_status("Error during analysis.")

    def update_progress(self, current, total):
        percent = (current / total) * 100
        self.progress_analysis["value"] = percent
        self.root.update_idletasks()

    def update_status(self, message):
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def clear_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

    def display_issues(self):
        for (issue, priority), count in self.issue_counts.items():
            tag = f"priority_{priority.lower()}"
            date = self.issue_dates.get((issue, priority), "N/A")
            self.tree.insert("", tk.END, values=(issue, priority, count, date), tags=(tag,))

        self.tree.tag_configure("priority_high", background="#ffcccc")
        self.tree.tag_configure("priority_medium", background="#fff2cc")
        self.tree.tag_configure("priority_low", background="#ccffcc")

    def on_issue_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            issue_text, priority, count, *_ = item['values']
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, issue_text)
            self.rca_text.delete(1.0, tk.END)
            self.rca_text.insert(tk.END, self.generate_rca(issue_text, priority))

    def generate_rca(self, issue_text, priority):
        rca = f"Issue: {issue_text}\n"
        rca += f"Priority: {priority}\n\n"
        if "Exception" in issue_text or "ERROR" in issue_text:
            rca += "Root Cause: Likely caused by an unhandled exception or failure in a service/component.\n"
            rca += "Suggested Action: Check stack trace and component/service mentioned in the log. Ensure exception handling is implemented.\n"
            rca += "Next Steps: Review error context, reproduce if possible, verify resolution.\n"
        elif "Timeout" in issue_text:
            rca += "Root Cause: Operation exceeded the expected time, possibly due to network or backend delays.\n"
            rca += "Suggested Action: Check response times and increase timeout if necessary. Look into backend service performance.\n"
            rca += "Next Steps: Log performance metrics, test alternative paths, investigate backend latency.\n"
        elif "Warning" in issue_text:
            rca += "Root Cause: A potential issue that may not impact functionality immediately.\n"
            rca += "Suggested Action: Monitor this warning for recurrence. Review application logs for more context.\n"
            rca += "Next Steps: Add alerts, ensure monitoring is in place.\n"
        elif "Failed" in issue_text:
            rca += "Root Cause: Operation or process did not complete successfully.\n"
            rca += "Suggested Action: Identify the step or dependency that caused the failure. Check configurations and dependencies.\n"
            rca += "Next Steps: Retry operation, inspect failure logs, escalate if recurring.\n"
        else:
            rca += "Root Cause: Informational message or less severe issue.\n"
            rca += "Suggested Action: No action needed unless correlated with other issues.\n"
            rca += "Next Steps: Continue monitoring.\n"
        return rca

    def sort_tree(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            l.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        self.tree.heading(col, command=lambda: self.sort_tree(col, not reverse))

    def export_rca_csv(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Issue", "Priority", "Count", "Date"])
                for (issue, priority), count in self.issue_counts.items():
                    writer.writerow([issue, priority, count, self.issue_dates.get((issue, priority), "N/A")])

    def export_rca_text(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            with open(file_path, mode='w', encoding='utf-8') as f:
                for (issue, priority), count in self.issue_counts.items():
                    rca = self.generate_rca(issue, priority)
                    f.write(f"{rca}\n{'-'*40}\n")

    def export_rca_pdf(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if file_path:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", style="B", size=12)
            pdf.cell(200, 10, txt="Root Cause Analysis For Logs", ln=1, align='C')

            sorted_issues = sorted(self.issue_counts.items(), key=lambda x: (x[0][1], -x[1]), reverse=True)

            pdf.set_font("Arial", size=10)
            for idx, ((issue, priority), count) in enumerate(sorted_issues, 1):
                date = self.issue_dates.get((issue, priority), "N/A")
                rca = self.generate_rca(issue, priority)
                pdf.set_font("Arial", style="B", size=10)
                pdf.cell(0, 10, f"{idx}. {priority} Priority | Count: {count} | Date: {date}", ln=True)
                pdf.set_font("Arial", size=10)
                for line in rca.split("\n"):
                    pdf.multi_cell(0, 8, txt=line)
                pdf.cell(0, 10, txt="", ln=True)
            pdf.output(file_path)

if __name__ == "__main__":
    root = tk.Tk()
    app = LogAnalyzerApp(root)
    root.mainloop()

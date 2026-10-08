## Copyright 2025
## Author: Rahul A. Dhakate
## Created for Log analysis and CSV file log parsing for Amla Commerce. 

# Enhanced version with:
# - Multiple issue types classification
# - Additional "Type" column in TreeView
# - More analytical RCAs
# - KPI Dashboard tab with charts
# - Vertical scroll bar for table
# - Improved issue grouping and counting
# - Enhanced RCA analysis with real-time term detection
# - Count statistics in Dashboard

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import re
import os
from collections import defaultdict, Counter
import csv
from tkinter import scrolledtext
from fpdf import FPDF
from datetime import datetime
from difflib import SequenceMatcher
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import webbrowser

class LogAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(".NET Log Analyzer Pro")
        self.root.geometry("1200x800")

        self.issues = []
        self.issue_counts = defaultdict(int)
        self.issue_dates = {}
        self.issue_types = {}
        self.unique_issues = []
        self.similarity_threshold = 0.85
        self.log_levels = ['Error', 'Warning', 'Info', 'Debug', 'Trace', 'Critical', 'Fail']
        self.log_level_counts = Counter()

        self.create_menu()
        self.create_status_bar()  # Moved this after all method definitions
        self.create_tabs()
        self.create_main_widgets()
        self.create_dashboard_widgets()

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

    def create_status_bar(self):
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.progress_analysis = ttk.Progressbar(self.status_frame, orient='horizontal', mode='determinate')
        self.progress_analysis.pack(fill=tk.X, padx=5, pady=2, expand=True)

        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)

    def create_tabs(self):
        self.tab_control = ttk.Notebook(self.root)

        self.analysis_tab = ttk.Frame(self.tab_control)
        self.dashboard_tab = ttk.Frame(self.tab_control)

        self.tab_control.add(self.analysis_tab, text='Log Analysis')
        self.tab_control.add(self.dashboard_tab, text='Dashboard')
        self.tab_control.pack(expand=1, fill="both")

    def create_main_widgets(self):
        main_pane = ttk.Panedwindow(self.analysis_tab, orient=tk.VERTICAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        top_pane = ttk.Panedwindow(main_pane, orient=tk.HORIZONTAL)
        main_pane.add(top_pane, weight=3)

        bottom_frame = ttk.Frame(main_pane)
        main_pane.add(bottom_frame, weight=1)

        left_frame = ttk.Frame(top_pane)
        top_pane.add(left_frame, weight=2)

        # Create a frame for the Treeview and scrollbars
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Issue", "Priority", "Type", "Count", "Date")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Configure columns and headings
        for col in columns:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_tree(_col, False))
            self.tree.column(col, anchor=tk.W, width=150, stretch=True)

        # Vertical scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        # Horizontal scrollbar
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=hsb.set)

        # Grid layout for proper scrollbar placement
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self.on_issue_select)

        right_frame = ttk.Frame(top_pane)
        top_pane.add(right_frame, weight=3)

        ttk.Label(right_frame, text="Issue Details:").pack(anchor='w', padx=5, pady=5)
        self.details_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, height=10)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(bottom_frame, text="Root Cause Analysis:").pack(anchor='w', padx=5, pady=5)
        self.rca_text = scrolledtext.ScrolledText(bottom_frame, wrap=tk.WORD, height=10, bg="white")
        self.rca_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def create_dashboard_widgets(self):
        # Create a container frame for better organization
        dashboard_frame = ttk.Frame(self.dashboard_tab)
        dashboard_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Statistics frame
        stats_frame = ttk.LabelFrame(dashboard_frame, text="Log Statistics")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        # Create labels for statistics
        self.total_issues_label = ttk.Label(stats_frame, text="Total Issues: 0")
        self.total_issues_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.high_priority_label = ttk.Label(stats_frame, text="High Priority: 0", foreground="red")
        self.high_priority_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.medium_priority_label = ttk.Label(stats_frame, text="Medium Priority: 0", foreground="orange")
        self.medium_priority_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.low_priority_label = ttk.Label(stats_frame, text="Low Priority: 0", foreground="green")
        self.low_priority_label.pack(side=tk.LEFT, padx=10, pady=5)

        # Log level distribution frame
        log_level_frame = ttk.LabelFrame(dashboard_frame, text="Log Level Distribution")
        log_level_frame.pack(fill=tk.X, padx=5, pady=5)

        self.log_level_labels = {}
        for level in self.log_levels:
            self.log_level_labels[level] = ttk.Label(log_level_frame, text=f"{level}: 0")
            self.log_level_labels[level].pack(side=tk.LEFT, padx=10, pady=5)

        # Charts frame
        charts_frame = ttk.Frame(dashboard_frame)
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.figure = plt.Figure(figsize=(10, 6), dpi=100)
        self.ax1 = self.figure.add_subplot(121)
        self.ax2 = self.figure.add_subplot(122)
        self.canvas = FigureCanvasTkAgg(self.figure, master=charts_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_dashboard(self):
        # Update statistics labels
        total_issues = sum(self.issue_counts.values())
        high_priority = sum(count for (_, priority), count in self.issue_counts.items() if priority == "High")
        medium_priority = sum(count for (_, priority), count in self.issue_counts.items() if priority == "Medium")
        low_priority = sum(count for (_, priority), count in self.issue_counts.items() if priority == "Low")

        self.total_issues_label.config(text=f"Total Issues: {total_issues}")
        self.high_priority_label.config(text=f"High Priority: {high_priority}")
        self.medium_priority_label.config(text=f"Medium Priority: {medium_priority}")
        self.low_priority_label.config(text=f"Low Priority: {low_priority}")

        # Update log level distribution
        for level in self.log_levels:
            self.log_level_labels[level].config(text=f"{level}: {self.log_level_counts.get(level, 0)}")

        # Update charts
        type_counter = Counter(self.issue_types.values())
        priority_counter = Counter(priority for _, priority in self.issue_counts.keys())

        self.ax1.clear()
        self.ax1.set_title("Issues by Type")
        if type_counter:
            self.ax1.bar(type_counter.keys(), type_counter.values(), color='skyblue')
            self.ax1.tick_params(axis='x', rotation=45)
        else:
            self.ax1.text(0.5, 0.5, 'No data', ha='center', va='center')

        self.ax2.clear()
        self.ax2.set_title("Issues by Priority")
        if priority_counter:
            self.ax2.pie(priority_counter.values(), labels=priority_counter.keys(), autopct='%1.1f%%')
        else:
            self.ax2.text(0.5, 0.5, 'No data', ha='center', va='center')

        self.figure.tight_layout()
        self.canvas.draw()

    def classify_issue_type(self, line):
        patterns = {
            "Cache": r"cache|redis",
            "File System": r"file not found|access denied|disk|ioerror",
            "Resources": r"resource|limit|thread|pool",
            "Memory": r"outofmemory|memory leak",
            "Network": r"timeout|unreachable|dns|connection refused",
            "Firewall": r"blocked|firewall|port",
            "ReactJS/JS": r"react|javascript|webpack|npm|jsx",
            "Database": r"sql|database|query|timeout|connection",
            "Authentication": r"auth|login|password|credentials",
            "Configuration": r"config|setting|parameter|missing|invalid"
        }
        for issue_type, pattern in patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                return issue_type
        return "Other"

    def detect_log_level(self, line):
        log_level_patterns = {
            'Error': r'\bError\b',
            'Warning': r'\bWarning\b',
            'Info': r'\bInfo\b',
            'Debug': r'\bDebug\b',
            'Trace': r'\bTrace\b',
            'Critical': r'\bCritical\b',
            'Fail': r'\bFail\b'
        }
        
        for level, pattern in log_level_patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                self.log_level_counts[level] += 1
                return level
        return None

    def show_about(self):
        about_text = """
        .NET Log Analyzer Pro
        
        Version: 2.0
        Created By: Rahul Arun Dhakate
        
        Features:
        - Analyze .NET application logs
        - CSV file import and analysis
        - Priority-based issue detection with color coding
        - Root cause analysis with online references
        - Progress tracking with status bar
        - Vertical and horizontal scrolling for large datasets
        - Export issues to CSV, TXT & PDF
        - Comprehensive dashboard with statistics
        
        This tool helps identify and prioritize issues in .NET application logs (.log) and csv files containing log data.
        """
        messagebox.showinfo("About .NET Log Analyzer Pro", about_text)
        
    def generate_rca(self, issue_text, priority):
        rca = f"Issue: {issue_text}\nPriority: {priority}\n\n"
        issue_type = self.classify_issue_type(issue_text)
        log_level = self.detect_log_level(issue_text)
        
        if log_level:
            rca += f"Log Level: {log_level}\n"
        
        if issue_type == "Cache":
            rca += "Root Cause: Likely related to Redis/memory cache failures.\n"
            rca += "Suggested Action: Verify caching server health. Flush stale keys if needed.\n"
            rca += "Reference: https://redis.io/topics/problems\n"
        elif issue_type == "File System":
            rca += "Root Cause: File access or directory read/write failure.\n"
            rca += "Suggested Action: Check permissions, disk space and paths.\n"
            rca += "Reference: https://docs.microsoft.com/en-us/dotnet/standard/io/\n"
        elif issue_type == "Resources":
            rca += "Root Cause: App thread, connection or system resource exhaustion.\n"
            rca += "Suggested Action: Tune thread pool and monitor resource usage.\n"
            rca += "Reference: https://docs.microsoft.com/en-us/dotnet/standard/threading/\n"
        elif issue_type == "Memory":
            rca += "Root Cause: Memory exhaustion or leak.\n"
            rca += "Suggested Action: Run profiling and apply GC tuning.\n"
            rca += "Reference: https://docs.microsoft.com/en-us/dotnet/standard/garbage-collection/\n"
        elif issue_type == "Network":
            rca += "Root Cause: Network connection failure or latency.\n"
            rca += "Suggested Action: Ping endpoints, verify host availability and routes.\n"
            rca += "Reference: https://docs.microsoft.com/en-us/dotnet/framework/network-programming/\n"
        elif issue_type == "Firewall":
            rca += "Root Cause: Port blocked or rule restriction by firewall.\n"
            rca += "Suggested Action: Check firewall rules and open required ports.\n"
            rca += "Reference: https://docs.microsoft.com/en-us/windows/security/\n"
        elif issue_type == "ReactJS/JS":
            rca += "Root Cause: Frontend React or JS code issue.\n"
            rca += "Suggested Action: Run linter, inspect webpack logs and fix component errors.\n"
            rca += "Reference: https://reactjs.org/docs/error-boundaries.html\n"
        elif issue_type == "Database":
            rca += "Root Cause: Database connection or query execution issue.\n"
            rca += "Suggested Action: Check database server status, connection strings, and query performance.\n"
            rca += "Reference: https://docs.microsoft.com/en-us/sql/relational-databases/performance/\n"
        elif issue_type == "Authentication":
            rca += "Root Cause: Authentication or authorization failure.\n"
            rca += "Suggested Action: Verify credentials, tokens, and authentication configuration.\n"
            rca += "Reference: https://docs.microsoft.com/en-us/aspnet/core/security/\n"
        elif issue_type == "Configuration":
            rca += "Root Cause: Missing or invalid configuration setting.\n"
            rca += "Suggested Action: Check configuration files and environment variables.\n"
            rca += "Reference: https://docs.microsoft.com/en-us/aspnet/core/fundamentals/configuration/\n"
        else:
            rca += "Root Cause: General failure.\nSuggested Action: Review full logs for specifics.\n"
        
        # Add clickable links for common patterns
        if re.search(r"NullReferenceException", issue_text, re.IGNORECASE):
            rca += "\nNull Reference Help: https://docs.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-messages/cs0165\n"
        elif re.search(r"TimeoutException", issue_text, re.IGNORECASE):
            rca += "\nTimeout Help: https://docs.microsoft.com/en-us/dotnet/api/system.timeoutexception\n"
        elif re.search(r"SqlException", issue_text, re.IGNORECASE):
            rca += "\nSQL Exception Help: https://docs.microsoft.com/en-us/dotnet/api/system.data.sqlclient.sqlexception\n"
        
        return rca

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Log and CSV files", "*.log *.csv")])
        if file_path:
            # Reset counters
            self.log_level_counts = Counter()
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
            self.issue_types.clear()
            self.unique_issues.clear()

            error_patterns = [
                (r"Exception|Critical|Fail", "High"),
                (r"ERROR", "High"),
                (r"Warning", "Medium"),
                (r"Timeout", "Medium"),
                (r"Failed", "Medium"),
                (r"Info", "Low"),
                (r"Debug", "Low"),
                (r"Trace", "Low"),
            ]

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                total_lines = len(lines)

                for index, line in enumerate(lines):
                    timestamp = datetime.now().strftime("%Y-%m-%d")
                    # Detect log level for statistics
                    self.detect_log_level(line)
                    
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
                                self.issue_types[(cleaned, priority)] = self.classify_issue_type(cleaned)
                            break
                    self.update_progress(index + 1, total_lines)

            self.display_issues()
            self.update_dashboard()
            self.update_status(f"Analysis complete. Found {len(self.issue_counts)} unique issues.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.update_status("Error during analysis.")

    def display_issues(self):
        # Sort issues by count (descending) and priority (High first)
        sorted_issues = sorted(self.issue_counts.items(), 
                              key=lambda x: (-x[1], x[0][1] == "High", x[0][1] == "Medium", x[0][1] == "Low"))

        for (issue, priority), count in sorted_issues:
            issue_type = self.issue_types.get((issue, priority), "Other")
            tag = f"priority_{priority.lower()}"
            date = self.issue_dates.get((issue, priority), "N/A")
            self.tree.insert("", tk.END, values=(issue[:200] + "..." if len(issue) > 200 else issue, 
                                            priority, issue_type, count, date), tags=(tag,))

        self.tree.tag_configure("priority_high", background="#ffcccc")
        self.tree.tag_configure("priority_medium", background="#fff2cc")
        self.tree.tag_configure("priority_low", background="#ccffcc")

    def on_issue_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            issue_text, priority, *_ = item['values']
            self.details_text.delete(1.0, tk.END)
            # Find the full issue text from unique_issues
            full_text = next((text for text, pri in self.unique_issues 
                            if self.is_similar(text, issue_text) and pri == priority), issue_text)
            self.details_text.insert(tk.END, full_text)
            self.rca_text.delete(1.0, tk.END)
            self.rca_text.insert(tk.END, self.generate_rca(full_text, priority))

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

    def sort_tree(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            l.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            l.sort(key=lambda t: t[0], reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        self.tree.heading(col, command=lambda: self.sort_tree(col, not reverse))

    def export_rca_csv(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Issue", "Priority", "Type", "Count", "Date"])
                for (issue, priority), count in self.issue_counts.items():
                    writer.writerow([issue, priority, self.issue_types[(issue, priority)], count, self.issue_dates.get((issue, priority), "N/A")])

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

            # Add summary statistics
            pdf.set_font("Arial", style="B", size=10)
            pdf.cell(0, 10, txt="Summary Statistics", ln=1)
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 8, txt=f"Total Issues: {sum(self.issue_counts.values())}", ln=1)
            pdf.cell(0, 8, txt=f"High Priority Issues: {sum(count for (_, priority), count in self.issue_counts.items() if priority == 'High')}", ln=1)
            pdf.cell(0, 8, txt=f"Medium Priority Issues: {sum(count for (_, priority), count in self.issue_counts.items() if priority == 'Medium')}", ln=1)
            pdf.cell(0, 8, txt=f"Low Priority Issues: {sum(count for (_, priority), count in self.issue_counts.items() if priority == 'Low')}", ln=1)
            pdf.cell(0, 10, txt="", ln=1)

            # Add log level distribution
            pdf.set_font("Arial", style="B", size=10)
            pdf.cell(0, 10, txt="Log Level Distribution", ln=1)
            pdf.set_font("Arial", size=10)
            for level, count in self.log_level_counts.items():
                pdf.cell(0, 8, txt=f"{level}: {count}", ln=1)
            pdf.cell(0, 10, txt="", ln=1)

            # Add detailed issues
            pdf.set_font("Arial", style="B", size=10)
            pdf.cell(0, 10, txt="Detailed Issues:", ln=1)
            
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
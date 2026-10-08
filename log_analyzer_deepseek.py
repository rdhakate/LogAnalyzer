import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import re
import csv
import os
import threading
import queue
from datetime import datetime

class LogAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(".NET Log Analyzer Pro")
        self.root.geometry("1200x900")
        self.root.minsize(1000, 700)
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure("Treeview", font=('Segoe UI', 10), rowheight=25)
        self.style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))
        self.style.configure("TNotebook", font=('Segoe UI', 9, 'bold'))
        self.style.configure("TNotebook.Tab", font=('Segoe UI', 9, 'bold'))
        self.style.configure("Critical.Treeview", background='#ffcccc')
        self.style.configure("High.Treeview", background='#ffdddd')
        self.style.configure("Medium.Treeview", background='#ffffcc')
        self.style.configure("Low.Treeview", background='#e6f7ff')
        
        # Priority configuration with root cause analysis
        self.priority_config = {
            'Critical': {
                'keywords': ['error', 'exception', 'fatal', 'fail', 'critical', 'crash', 'unhandled'],
                'color': '#ffcccc',
                'root_cause': {
                    'exception': 'Unhandled exception in application code',
                    'error': 'Runtime error requiring immediate attention',
                    'fatal': 'Application failure causing shutdown',
                    'crash': 'Application process termination',
                    'unhandled': 'Unhandled exception leading to application instability'
                }
            },
            'High': {
                'keywords': ['deadlock', 'timeout', 'connection failed', 'database down', 'unauthorized', 'access denied'],
                'color': '#ffdddd',
                'root_cause': {
                    'deadlock': 'Resource contention in database access',
                    'timeout': 'Service unresponsive or network issue',
                    'connection failed': 'Network or service availability problem',
                    'database down': 'Database server unavailable',
                    'unauthorized': 'Authentication or permission issue'
                }
            },
            'Medium': {
                'keywords': ['warn', 'retry', 'slow', 'degraded', 'fallback', 'retrying'],
                'color': '#ffffcc',
                'root_cause': {
                    'warn': 'Potential issue that needs monitoring',
                    'retry': 'Transient failure requiring retries',
                    'slow': 'Performance degradation',
                    'degraded': 'Service operating below optimal level'
                }
            },
            'Low': {
                'keywords': ['info', 'debug', 'trace', 'notice', 'starting', 'stopping'],
                'color': '#e6f7ff',
                'root_cause': {
                    'info': 'Informational message only',
                    'debug': 'Diagnostic information for debugging',
                    'trace': 'Detailed execution tracing',
                    'notice': 'Normal but significant condition'
                }
            }
        }

        # Create UI elements
        self.create_widgets()
        self.create_menu()
        
        # CSV data storage
        self.csv_data = []
        self.csv_columns = []
        self.csv_issues = {}
        
        # Log analysis storage
        self.current_issues = {}
        
        # Queue for progress updates
        self.progress_queue = queue.Queue()
        
        # Bind queue checker
        self.root.after(100, self.process_queue)

    def create_menu(self):
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Open Log File", command=self.open_file)
        file_menu.add_command(label="Open CSV File", command=self.open_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Export Issues to CSV", command=self.export_issues)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

    def create_widgets(self):
        # File selection frame
        file_frame = ttk.Frame(self.root, padding=(10, 10, 10, 5))
        file_frame.pack(fill=tk.X)
        
        self.btn_open = ttk.Button(
            file_frame, 
            text="Open Log File", 
            command=self.open_file,
            width=15
        )
        self.btn_open.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_csv = ttk.Button(
            file_frame, 
            text="Open CSV File", 
            command=self.open_csv,
            width=15
        )
        self.btn_csv.pack(side=tk.LEFT, padx=(0, 10))
        
        self.file_label = ttk.Label(file_frame, text="No file selected")
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Create paned window for resizable sections
        paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(paned)
        paned.add(self.notebook, weight=5)
        
        # Tab 1: Issues
        issues_frame = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(issues_frame, text="Issues")
        
        # Tab 2: CSV Data
        csv_frame = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(csv_frame, text="Raw Data")
        
        # Tab 3: Root Cause Analysis
        analysis_frame = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(analysis_frame, text="Root Cause")
        
        # Tab 4: CSV Issues
        csv_issues_frame = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(csv_issues_frame, text="CSV Issues")
        
        # Issues treeview with horizontal scrolling
        issues_container = ttk.Frame(issues_frame)
        issues_container.pack(fill=tk.BOTH, expand=True)
        
        # Create horizontal scrollbar first
        h_scrollbar = ttk.Scrollbar(issues_container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create vertical scrollbar
        v_scrollbar = ttk.Scrollbar(issues_container, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create treeview
        columns = ('priority', 'issue', 'count', 'first_occurrence', 'root_cause')
        self.tree = ttk.Treeview(
            issues_container, 
            columns=columns, 
            show='headings',
            selectmode='browse',
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure scrollbars
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
        
        # Configure columns
        self.tree.heading('priority', text='Priority', anchor=tk.W)
        self.tree.heading('issue', text='Issue', anchor=tk.W)
        self.tree.heading('count', text='Count', anchor=tk.W)
        self.tree.heading('first_occurrence', text='First Occurrence', anchor=tk.W)
        self.tree.heading('root_cause', text='Root Cause', anchor=tk.W)
        
        self.tree.column('priority', width=100, minwidth=80, stretch=False)
        self.tree.column('issue', width=300, minwidth=150, stretch=False)
        self.tree.column('count', width=80, minwidth=60, stretch=False)
        self.tree.column('first_occurrence', width=180, minwidth=120, stretch=False)
        self.tree.column('root_cause', width=350, minwidth=200, stretch=False)
        
        # Create CSV treeview with horizontal scrolling
        csv_container = ttk.Frame(csv_frame)
        csv_container.pack(fill=tk.BOTH, expand=True)
        
        # Create horizontal scrollbar first
        csv_h_scrollbar = ttk.Scrollbar(csv_container, orient=tk.HORIZONTAL)
        csv_h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create vertical scrollbar
        csv_v_scrollbar = ttk.Scrollbar(csv_container, orient=tk.VERTICAL)
        csv_v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create treeview
        self.csv_tree = ttk.Treeview(
            csv_container,
            yscrollcommand=csv_v_scrollbar.set,
            xscrollcommand=csv_h_scrollbar.set
        )
        self.csv_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure scrollbars
        csv_v_scrollbar.config(command=self.csv_tree.yview)
        csv_h_scrollbar.config(command=self.csv_tree.xview)
        
        # Create CSV Issues treeview with horizontal scrolling
        csv_issues_container = ttk.Frame(csv_issues_frame)
        csv_issues_container.pack(fill=tk.BOTH, expand=True)
        
        # Create horizontal scrollbar first
        csv_issues_h_scrollbar = ttk.Scrollbar(csv_issues_container, orient=tk.HORIZONTAL)
        csv_issues_h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create vertical scrollbar
        csv_issues_v_scrollbar = ttk.Scrollbar(csv_issues_container, orient=tk.VERTICAL)
        csv_issues_v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create treeview
        csv_columns = ('priority', 'issue', 'row', 'timestamp', 'root_cause')
        self.csv_issues_tree = ttk.Treeview(
            csv_issues_container, 
            columns=csv_columns, 
            show='headings',
            yscrollcommand=csv_issues_v_scrollbar.set,
            xscrollcommand=csv_issues_h_scrollbar.set
        )
        self.csv_issues_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure scrollbars
        csv_issues_v_scrollbar.config(command=self.csv_issues_tree.yview)
        csv_issues_h_scrollbar.config(command=self.csv_issues_tree.xview)
        
        # Configure columns
        self.csv_issues_tree.heading('priority', text='Priority', anchor=tk.W)
        self.csv_issues_tree.heading('issue', text='Issue', anchor=tk.W)
        self.csv_issues_tree.heading('row', text='Row', anchor=tk.W)
        self.csv_issues_tree.heading('timestamp', text='Timestamp', anchor=tk.W)
        self.csv_issues_tree.heading('root_cause', text='Root Cause', anchor=tk.W)
        
        self.csv_issues_tree.column('priority', width=100, minwidth=80, stretch=False)
        self.csv_issues_tree.column('issue', width=300, minwidth=150, stretch=False)
        self.csv_issues_tree.column('row', width=80, minwidth=60, stretch=False)
        self.csv_issues_tree.column('timestamp', width=180, minwidth=120, stretch=False)
        self.csv_issues_tree.column('root_cause', width=350, minwidth=200, stretch=False)
        
        # Root Cause Analysis text area
        self.analysis_text = scrolledtext.ScrolledText(
            analysis_frame, 
            wrap=tk.WORD, 
            font=('Segoe UI', 10),
            padx=10,
            pady=10
        )
        self.analysis_text.pack(fill=tk.BOTH, expand=True)
        self.analysis_text.insert(tk.END, "Root cause analysis will appear here after log processing")
        self.analysis_text.config(state=tk.DISABLED)
        
        # Bind selection events
        self.tree.bind('<<TreeviewSelect>>', self.on_issue_select)
        self.csv_issues_tree.bind('<<TreeviewSelect>>', self.on_csv_issue_select)
        
        # Details panel
        detail_frame = ttk.LabelFrame(paned, text="Issue Details", padding=(10, 5, 10, 10))
        paned.add(detail_frame, weight=2)
        
        self.detail_text = scrolledtext.ScrolledText(
            detail_frame, 
            wrap=tk.WORD, 
            font=('Consolas', 9),
            padx=10,
            pady=10
        )
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar with progress
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Status label
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_label = ttk.Label(
            status_frame, 
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        )
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Progress bar
        self.progress = ttk.Progressbar(
            status_frame, 
            orient=tk.HORIZONTAL, 
            mode='determinate',
            length=200
        )
        self.progress.pack(side=tk.RIGHT, padx=(0, 5))

    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Log File",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        self.file_label.config(text=file_path)
        self.status_var.set("Starting log file analysis...")
        self.progress['value'] = 0
        self.root.update()
        
        # Clear previous data
        for tab in [self.tree, self.csv_tree, self.csv_issues_tree]:
            for item in tab.get_children():
                tab.delete(item)
                
        self.analysis_text.config(state=tk.NORMAL)
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, "Analyzing log file...")
        self.analysis_text.config(state=tk.DISABLED)
        
        # Switch to Issues tab
        self.notebook.select(0)
        
        # Start analysis in a separate thread
        threading.Thread(
            target=self.analyze_log, 
            args=(file_path,),
            daemon=True
        ).start()

    def open_csv(self):
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        self.file_label.config(text=file_path)
        self.status_var.set("Starting CSV file loading...")
        self.progress['value'] = 0
        self.root.update()
        
        # Clear previous data
        for item in self.csv_tree.get_children():
            self.csv_tree.delete(item)
        for item in self.csv_issues_tree.get_children():
            self.csv_issues_tree.delete(item)
            
        self.analysis_text.config(state=tk.NORMAL)
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, "Analyzing CSV file...")
        self.analysis_text.config(state=tk.DISABLED)
        
        try:
            self.notebook.select(1)  # Switch to Raw Data tab
            # Start CSV loading in a separate thread
            threading.Thread(
                target=self.load_csv, 
                args=(file_path,),
                daemon=True
            ).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV:\n{str(e)}")
            self.status_var.set("Error loading CSV")

    def load_csv(self, file_path):
        try:
            # Clear previous data
            self.csv_data = []
            self.csv_columns = []
            
            # Get file size for progress calculation
            file_size = os.path.getsize(file_path)
            processed_size = 0
            
            # Read CSV file
            with open(file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                header = next(csv_reader)
                self.csv_columns = header
                
                # Configure treeview columns
                self.csv_tree['columns'] = header
                for col in header:
                    self.csv_tree.heading(col, text=col)
                    self.csv_tree.column(col, width=100, minwidth=50, stretch=False)
                
                # Get total lines for progress calculation
                file.seek(0)
                total_lines = sum(1 for _ in csv_reader) - 1  # exclude header
                file.seek(0)
                next(csv_reader)  # skip header again
                
                # Add data to treeview
                for i, row in enumerate(csv_reader):
                    processed_size += len(','.join(row).encode('utf-8'))
                    progress = int((processed_size / file_size) * 100)
                    self.progress_queue.put(("progress", progress))
                    self.progress_queue.put(("status", f"Loading CSV: {i+1}/{total_lines} rows"))
                    
                    self.csv_tree.insert('', tk.END, values=row)
                    self.csv_data.append(row)
            
            # Analyze CSV for issues
            self.progress_queue.put(("status", "Analyzing CSV content..."))
            self.progress['value'] = 0  # Reset progress for analysis phase
            self.analyze_csv_content(total_lines)
            
            self.progress_queue.put(("progress", 100))
            self.progress_queue.put(("status", "CSV analysis complete"))
        except Exception as e:
            self.progress_queue.put(("error", f"CSV Error: {str(e)}"))

    def analyze_csv_content(self, total_rows):
        self.csv_issues = {}
        timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[\.,]\d{3})')
        
        # Find columns that might contain log messages
        log_columns = []
        for col in self.csv_columns:
            if 'message' in col.lower() or 'log' in col.lower() or 'text' in col.lower():
                log_columns.append(col)
        
        if not log_columns:
            self.progress_queue.put(("error", "No log message columns found in CSV"))
            return
        
        # Priority occurrence counts
        priority_counts = {
            'Critical': 0,
            'High': 0,
            'Medium': 0,
            'Low': 0
        }
        
        # Analyze each row
        for row_idx, row in enumerate(self.csv_data):
            progress = int((row_idx / total_rows) * 100)
            self.progress_queue.put(("progress", progress))
            self.progress_queue.put(("status", f"Analyzing CSV: {row_idx+1}/{total_rows} rows"))
                
            # Extract timestamp if available
            timestamp = ""
            for i, col in enumerate(self.csv_columns):
                if 'time' in col.lower() or 'date' in col.lower():
                    timestamp_match = timestamp_pattern.search(row[i])
                    if timestamp_match:
                        timestamp = timestamp_match.group(1)
                        break
            
            # Check log columns for issues
            for col in log_columns:
                col_idx = self.csv_columns.index(col)
                if col_idx < len(row):
                    line = row[col_idx]
                    
                    # Skip empty lines
                    if not line.strip():
                        continue
                        
                    # Identify issues
                    found_issue = None
                    issue_priority = None
                    root_cause = None
                    
                    for priority, config in self.priority_config.items():
                        for keyword in config['keywords']:
                            if re.search(rf'\b{keyword}\b', line, re.IGNORECASE):
                                found_issue = keyword
                                issue_priority = priority
                                priority_counts[priority] += 1
                                
                                # Get root cause explanation
                                root_cause = config['root_cause'].get(
                                    keyword, 
                                    f"{priority} issue detected"
                                )
                                
                                # Add to CSV issues treeview
                                item_id = self.csv_issues_tree.insert('', tk.END, values=(
                                    issue_priority,
                                    f"{keyword.upper()} detected",
                                    row_idx + 1,
                                    timestamp or "N/A",
                                    root_cause
                                ))
                                
                                # Apply color coding
                                self.csv_issues_tree.item(item_id, tags=(f"{issue_priority}.Treeview",))
                                
                                # Store for root cause analysis
                                key = f"{issue_priority}:{keyword}"
                                if key not in self.csv_issues:
                                    self.csv_issues[key] = {
                                        'count': 0,
                                        'priority': issue_priority,
                                        'root_cause': root_cause
                                    }
                                self.csv_issues[key]['count'] += 1
                                break
                        if found_issue:
                            break
        
        # Generate root cause analysis for CSV
        root_cause_summary = {}
        for issue, details in self.csv_issues.items():
            root_cause_summary[details['root_cause']] = root_cause_summary.get(details['root_cause'], 0) + details['count']
        
        # Create priority summary
        priority_summary = (
            f"Critical: {priority_counts['Critical']}, "
            f"High: {priority_counts['High']}, "
            f"Medium: {priority_counts['Medium']}, "
            f"Low: {priority_counts['Low']}"
        )
        
        self.progress_queue.put(("csv_analysis", root_cause_summary, priority_summary))

    def analyze_log(self, file_path):
        try:
            # Get file size for progress calculation
            file_size = os.path.getsize(file_path)
            processed_size = 0
            
            issues = {}
            timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[\.,]\d{3})')
            
            # Root cause analysis summary
            root_cause_summary = {}
            
            # Priority occurrence counts
            priority_counts = {
                'Critical': 0,
                'High': 0,
                'Medium': 0,
                'Low': 0
            }
            
            # First pass: count lines for progress
            with open(file_path, 'r', encoding='utf-8') as file:
                total_lines = sum(1 for _ in file)
            
            # Second pass: process file
            with open(file_path, 'r', encoding='utf-8') as file:
                for i, line in enumerate(file):
                    processed_size += len(line.encode('utf-8'))
                    progress = min(100, int((processed_size / file_size) * 100))
                    self.progress_queue.put(("progress", progress))
                    self.progress_queue.put(("status", f"Analyzing log: {i+1}/{total_lines} lines"))
                    
                    # Extract timestamp if present
                    timestamp = ""
                    timestamp_match = timestamp_pattern.search(line)
                    if timestamp_match:
                        timestamp = timestamp_match.group(1)
                    
                    # Skip empty lines
                    if not line.strip():
                        continue
                        
                    # Identify issues
                    found_issue = None
                    issue_priority = None
                    root_cause = None
                    
                    for priority, config in self.priority_config.items():
                        for keyword in config['keywords']:
                            if re.search(rf'\b{keyword}\b', line, re.IGNORECASE):
                                found_issue = keyword
                                issue_priority = priority
                                priority_counts[priority] += 1
                                
                                # Get root cause explanation
                                root_cause = config['root_cause'].get(
                                    keyword, 
                                    f"{priority} issue detected"
                                )
                                
                                # Update root cause summary
                                root_cause_summary[root_cause] = root_cause_summary.get(root_cause, 0) + 1
                                
                                # Normalize issue name
                                issue_name = f"{found_issue.upper()} detected"
                                
                                if issue_name not in issues:
                                    issues[issue_name] = {
                                        'priority': issue_priority,
                                        'count': 0,
                                        'first_occurrence': timestamp if timestamp else "N/A",
                                        'examples': [],
                                        'root_cause': root_cause
                                    }
                                
                                issues[issue_name]['count'] += 1
                                if len(issues[issue_name]['examples']) < 3:
                                    issues[issue_name]['examples'].append(line.strip())
                                break
                        if found_issue:
                            break
            
            # Create priority summary
            priority_summary = (
                f"Critical: {priority_counts['Critical']}, "
                f"High: {priority_counts['High']}, "
                f"Medium: {priority_counts['Medium']}, "
                f"Low: {priority_counts['Low']}"
            )
            
            # Update UI with results
            self.progress_queue.put(("results", issues, root_cause_summary, priority_summary))
            self.progress_queue.put(("progress", 100))
            self.progress_queue.put(("status", "Log analysis complete"))
            
        except UnicodeDecodeError:
            # Try Latin-1 encoding if UTF-8 fails
            with open(file_path, 'r', encoding='latin-1') as file:
                processed_size = 0
                total_lines = sum(1 for _ in file)
                file.seek(0)
                
                issues = {}
                root_cause_summary = {}
                priority_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}
                
                for i, line in enumerate(file):
                    processed_size += len(line.encode('latin-1'))
                    progress = min(100, int((processed_size / file_size) * 100))
                    self.progress_queue.put(("progress", progress))
                    self.progress_queue.put(("status", f"Analyzing log (Latin-1): {i+1}/{total_lines} lines"))
                    
                    timestamp = ""
                    timestamp_match = timestamp_pattern.search(line)
                    if timestamp_match:
                        timestamp = timestamp_match.group(1)
                    
                    if not line.strip():
                        continue
                        
                    found_issue = None
                    issue_priority = None
                    root_cause = None
                    
                    for priority, config in self.priority_config.items():
                        for keyword in config['keywords']:
                            if re.search(rf'\b{keyword}\b', line, re.IGNORECASE):
                                found_issue = keyword
                                issue_priority = priority
                                priority_counts[priority] += 1
                                
                                root_cause = config['root_cause'].get(
                                    keyword, 
                                    f"{priority} issue detected"
                                )
                                
                                root_cause_summary[root_cause] = root_cause_summary.get(root_cause, 0) + 1
                                
                                issue_name = f"{found_issue.upper()} detected"
                                
                                if issue_name not in issues:
                                    issues[issue_name] = {
                                        'priority': issue_priority,
                                        'count': 0,
                                        'first_occurrence': timestamp if timestamp else "N/A",
                                        'examples': [],
                                        'root_cause': root_cause
                                    }
                                
                                issues[issue_name]['count'] += 1
                                if len(issues[issue_name]['examples']) < 3:
                                    issues[issue_name]['examples'].append(line.strip())
                                break
                        if found_issue:
                            break
            
            priority_summary = (
                f"Critical: {priority_counts['Critical']}, "
                f"High: {priority_counts['High']}, "
                f"Medium: {priority_counts['Medium']}, "
                f"Low: {priority_counts['Low']}"
            )
            
            self.progress_queue.put(("results", issues, root_cause_summary, priority_summary))
            self.progress_queue.put(("progress", 100))
            self.progress_queue.put(("status", "Log analysis complete (Latin-1)"))
            
        except Exception as e:
            self.progress_queue.put(("error", str(e)))

    def display_results(self, issues, root_cause_summary, priority_summary):
        # Store issues for detail view
        self.current_issues = issues
        
        # Clear existing results
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Sort issues by priority
        priority_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
        sorted_issues = sorted(
            issues.items(),
            key=lambda x: (priority_order[x[1]['priority']], x[0])
        )
        
        # Add to treeview with color coding
        for issue, details in sorted_issues:
            priority = details['priority']
            item_id = self.tree.insert('', tk.END, values=(
                priority,
                issue,
                details['count'],
                details['first_occurrence'] or "N/A",
                details['root_cause']
            ), tags=(f"{priority}.Treeview",))
        
        # Update root cause analysis tab
        self.analysis_text.config(state=tk.NORMAL)
        self.analysis_text.delete(1.0, tk.END)
        
        if root_cause_summary:
            self.analysis_text.insert(tk.END, "ROOT CAUSE ANALYSIS SUMMARY\n\n")
            self.analysis_text.insert(tk.END, "Based on the log analysis, the main issues are:\n\n")
            
            # Sort root causes by occurrence count
            sorted_causes = sorted(
                root_cause_summary.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for cause, count in sorted_causes:
                self.analysis_text.insert(tk.END, f"- {cause} (occurred {count} times)\n")
                
            # Add recommendations
            self.analysis_text.insert(tk.END, "\nRECOMMENDED ACTIONS:\n")
            self.analysis_text.insert(tk.END, "1. Investigate critical errors immediately\n")
            self.analysis_text.insert(tk.END, "2. Check database connections and performance\n")
            self.analysis_text.insert(tk.END, "3. Review exception stack traces for code issues\n")
            self.analysis_text.insert(tk.END, "4. Monitor system resources and network connectivity\n")
            self.analysis_text.insert(tk.END, "5. Verify authentication and authorization mechanisms\n")
        else:
            self.analysis_text.insert(tk.END, "No significant issues found in the logs")
            
        self.analysis_text.config(state=tk.DISABLED)
        
        # Switch to root cause tab
        self.notebook.select(2)
        
        # Return priority summary for status bar
        return priority_summary

    def on_issue_select(self, event):
        selected = self.tree.focus()
        if not selected:
            return
            
        item = self.tree.item(selected)
        issue_name = item['values'][1]
        
        if hasattr(self, 'current_issues') and issue_name in self.current_issues:
            details = self.current_issues[issue_name]
            
            self.detail_text.config(state=tk.NORMAL)
            self.detail_text.delete(1.0, tk.END)
            
            self.detail_text.insert(tk.END, f"PRIORITY: {details['priority']}\n")
            self.detail_text.insert(tk.END, f"OCCURRENCES: {details['count']}\n")
            self.detail_text.insert(tk.END, f"FIRST OCCURRENCE: {details['first_occurrence']}\n")
            self.detail_text.insert(tk.END, f"ROOT CAUSE: {details['root_cause']}\n\n")
            self.detail_text.insert(tk.END, "EXAMPLE ENTRIES:\n\n")
            
            for example in details['examples']:
                self.detail_text.insert(tk.END, f"- {example}\n\n")
            
            self.detail_text.config(state=tk.DISABLED)

    def on_csv_issue_select(self, event):
        selected = self.csv_issues_tree.focus()
        if not selected:
            return
            
        item = self.csv_issues_tree.item(selected)
        values = item['values']
        row_index = int(values[2]) - 1  # Convert to 0-based index
        
        if 0 <= row_index < len(self.csv_data):
            row_data = self.csv_data[row_index]
            
            self.detail_text.config(state=tk.NORMAL)
            self.detail_text.delete(1.0, tk.END)
            
            self.detail_text.insert(tk.END, f"CSV ROW DETAILS (Row {row_index + 1})\n\n")
            self.detail_text.insert(tk.END, f"PRIORITY: {values[0]}\n")
            self.detail_text.insert(tk.END, f"ISSUE: {values[1]}\n")
            self.detail_text.insert(tk.END, f"TIMESTAMP: {values[3]}\n")
            self.detail_text.insert(tk.END, f"ROOT CAUSE: {values[4]}\n\n")
            self.detail_text.insert(tk.END, "FULL ROW DATA:\n\n")
            
            for i, col in enumerate(self.csv_columns):
                self.detail_text.insert(tk.END, f"{col}: {row_data[i]}\n")
            
            self.detail_text.config(state=tk.DISABLED)

    def process_queue(self):
        try:
            while True:
                message = self.progress_queue.get_nowait()
                if message[0] == "progress":
                    self.progress['value'] = min(100, message[1])
                elif message[0] == "status":
                    self.status_var.set(message[1])
                elif message[0] == "results":
                    priority_summary = self.display_results(message[1], message[2], message[3])
                    self.status_var.set(f"Analysis complete. Issues: {priority_summary}")
                elif message[0] == "csv_analysis":
                    self.display_csv_analysis(message[1], message[2])
                    self.status_var.set(f"CSV analysis complete. Issues: {message[2]}")
                elif message[0] == "error":
                    messagebox.showerror("Error", message[1])
                    self.status_var.set("Error occurred")
                self.root.update()
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_queue)

    def display_csv_analysis(self, root_cause_summary, priority_summary):
        # Update root cause analysis tab
        self.analysis_text.config(state=tk.NORMAL)
        self.analysis_text.delete(1.0, tk.END)
        
        if root_cause_summary:
            self.analysis_text.insert(tk.END, "CSV ROOT CAUSE ANALYSIS SUMMARY\n\n")
            self.analysis_text.insert(tk.END, "Based on the CSV analysis, the main issues are:\n\n")
            
            # Sort root causes by occurrence count
            sorted_causes = sorted(
                root_cause_summary.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for cause, count in sorted_causes:
                self.analysis_text.insert(tk.END, f"- {cause} (occurred {count} times)\n")
                
            # Add recommendations
            self.analysis_text.insert(tk.END, "\nRECOMMENDED ACTIONS:\n")
            self.analysis_text.insert(tk.END, "1. Investigate critical issues in the CSV data\n")
            self.analysis_text.insert(tk.END, "2. Correlate issues with timestamps for patterns\n")
            self.analysis_text.insert(tk.END, "3. Review source systems for data quality issues\n")
            self.analysis_text.insert(tk.END, "4. Validate data transformation processes\n")
        else:
            self.analysis_text.insert(tk.END, "No significant issues found in the CSV data")
            
        self.analysis_text.config(state=tk.DISABLED)
        
        # Switch to CSV Issues tab
        self.notebook.select(3)
        
        # Return priority summary for status bar
        return priority_summary

    def export_issues(self):
        file_path = filedialog.asksaveasfilename(
            title="Export Issues to CSV",
            filetypes=[("CSV files", "*.csv")],
            defaultextension=".csv"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['Priority', 'Issue', 'Count', 'First Occurrence', 'Root Cause'])
                
                # Get all issues from the treeview
                for item in self.tree.get_children():
                    values = self.tree.item(item)['values']
                    writer.writerow(values)
                
                # Also include CSV issues if available
                if self.csv_issues_tree.get_children():
                    writer.writerow([])
                    writer.writerow(['CSV Issues'])
                    writer.writerow(['Priority', 'Issue', 'Row', 'Timestamp', 'Root Cause'])
                    for item in self.csv_issues_tree.get_children():
                        values = self.csv_issues_tree.item(item)['values']
                        writer.writerow(values)
            
            self.status_var.set(f"Issues exported to {file_path}")
            messagebox.showinfo("Export Successful", "Issues have been exported to CSV")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export issues:\n{str(e)}")

    def show_about(self):
        about_text = """
        .NET Log Analyzer Pro
        
        Version: 2.0
        Created By: DeepSeek
        
        Features:
        - Analyze .NET application logs
        - CSV file import and analysis
        - Priority-based issue detection with color coding
        - Root cause analysis
        - Progress tracking with status bar
        - Horizontal scrolling for large datasets
        - Export issues to CSV
        
        This tool helps identify and prioritize issues in .NET application logs
        and CSV files containing log data.
        """
        messagebox.showinfo("About .NET Log Analyzer Pro", about_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = LogAnalyzerApp(root)
    root.mainloop()
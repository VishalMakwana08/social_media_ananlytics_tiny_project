import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import re
import urllib.request
import urllib.error
from urllib.parse import urlparse
import threading
from datetime import datetime
import json
import os
import html
from html.parser import HTMLParser

# ----------------------------- Configuration -----------------------------
APP_TITLE = "SEO Page Optimization Dashboard"
APP_SIZE = "1100x750"
HISTORY_FILE = "seo_history.json"

# ----------------------------- HTML Analyzer -----------------------------
class SEOHTMLParser(HTMLParser):
    """Parses HTML and extracts SEO-relevant data."""
    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta_description = ""
        self.meta_keywords = ""
        self.meta_robots = ""
        self.canonical = ""
        self.h1 = []
        self.h2 = []
        self.h3 = []
        self.images = []          # list of dicts: {src, alt}
        self.links = []           # list of dicts: {href, text}
        self.word_count = 0
        self._in_title = False
        self._in_script = False
        self._in_style = False
        self._current_text = []
        self._current_tag = None
        self._in_body = False
        self._collect_text = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
            self._current_text = []
        elif tag == "meta":
            name = attrs.get("name", "").lower()
            if name == "description":
                self.meta_description = attrs.get("content", "")
            elif name == "keywords":
                self.meta_keywords = attrs.get("content", "")
            elif name == "robots":
                self.meta_robots = attrs.get("content", "")
        elif tag == "link":
            if attrs.get("rel", "").lower() == "canonical":
                self.canonical = attrs.get("href", "")
        elif tag == "h1":
            self._current_tag = "h1"; self._current_text = []
        elif tag == "h2":
            self._current_tag = "h2"; self._current_text = []
        elif tag == "h3":
            self._current_tag = "h3"; self._current_text = []
        elif tag == "img":
            self.images.append({"src": attrs.get("src", ""), "alt": attrs.get("alt", "")})
        elif tag == "a":
            self._current_tag = "a"
            self._current_text = []
            self._current_href = attrs.get("href", "")
        elif tag == "body":
            self._in_body = True
        elif tag == "script":
            self._in_script = True
        elif tag == "style":
            self._in_style = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.title = "".join(self._current_text).strip()
            self._in_title = False
        elif tag in ("h1", "h2", "h3"):
            text = "".join(self._current_text).strip()
            if tag == "h1":
                self.h1.append(text)
            elif tag == "h2":
                self.h2.append(text)
            else:
                self.h3.append(text)
            self._current_tag = None
            self._current_text = []
        elif tag == "a":
            text = "".join(self._current_text).strip()
            if text:
                self.links.append({"href": getattr(self, "_current_href", ""), "text": text})
            self._current_tag = None
            self._current_text = []
        elif tag == "script":
            self._in_script = False
        elif tag == "style":
            self._in_style = False
        elif tag == "body":
            self._in_body = False

    def handle_data(self, data):
        if self._in_title:
            self._current_text.append(data)
        elif self._current_tag in ("h1", "h2", "h3", "a"):
            self._current_text.append(data)
        elif self._in_body and not self._in_script and not self._in_style:
            # count words for body text
            words = re.findall(r"\b[\w'-]+\b", data)
            self.word_count += len(words)


# ----------------------------- SEO Engine -----------------------------
def fetch_url(url, timeout=15):
    """Fetch HTML content from URL."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (SEO Dashboard Bot)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        # Try decoding
        encoding = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(encoding, errors="replace")


def analyze_seo(html_content, url=""):
    """Run all SEO checks and return a dict of results."""
    parser = SEOHTMLParser()
    parser.feed(html_content)

    results = {
        "url": url,
        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "score": 0,
        "checks": [],
        "stats": {
            "title": parser.title,
            "title_length": len(parser.title),
            "meta_description": parser.meta_description,
            "meta_description_length": len(parser.meta_description),
            "meta_keywords": parser.meta_keywords,
            "canonical": parser.canonical,
            "h1_count": len(parser.h1),
            "h2_count": len(parser.h2),
            "h3_count": len(parser.h3),
            "images_total": len(parser.images),
            "images_missing_alt": sum(1 for i in parser.images if not i["alt"].strip()),
            "links_total": len(parser.links),
            "word_count": parser.word_count,
        },
        "details": {
            "h1": parser.h1,
            "h2": parser.h2[:20],
            "images": parser.images[:30],
            "links": parser.links[:30],
        }
    }

    checks = []

    def add_check(name, status, message, weight):
        """status: 'pass', 'warn', 'fail'"""
        checks.append({
            "name": name,
            "status": status,
            "message": message,
            "weight": weight,
        })

    # 1. Title
    tl = len(parser.title)
    if not parser.title:
        add_check("Title Tag", "fail", "Missing <title> tag.", 10)
    elif 30 <= tl <= 60:
        add_check("Title Tag", "pass", f"Good length ({tl} chars).", 10)
    elif tl < 30:
        add_check("Title Tag", "warn", f"Too short ({tl} chars). Recommended 30-60.", 10)
    else:
        add_check("Title Tag", "warn", f"Too long ({tl} chars). Recommended 30-60.", 10)

    # 2. Meta Description
    md = len(parser.meta_description)
    if not parser.meta_description:
        add_check("Meta Description", "fail", "Missing meta description.", 10)
    elif 120 <= md <= 160:
        add_check("Meta Description", "pass", f"Good length ({md} chars).", 10)
    elif md < 120:
        add_check("Meta Description", "warn", f"Too short ({md} chars). Recommended 120-160.", 10)
    else:
        add_check("Meta Description", "warn", f"Too long ({md} chars). Recommended 120-160.", 10)

    # 3. H1
    if len(parser.h1) == 0:
        add_check("H1 Heading", "fail", "No H1 heading found.", 10)
    elif len(parser.h1) == 1:
        add_check("H1 Heading", "pass", "Exactly one H1 heading.", 10)
    else:
        add_check("H1 Heading", "warn", f"Multiple H1 headings ({len(parser.h1)}).", 10)

    # 4. Image Alt
    if parser.images:
        missing = sum(1 for i in parser.images if not i["alt"].strip())
        if missing == 0:
            add_check("Image Alt Text", "pass", f"All {len(parser.images)} images have alt text.", 10)
        else:
            add_check("Image Alt Text", "warn",
                      f"{missing}/{len(parser.images)} images missing alt text.", 10)
    else:
        add_check("Image Alt Text", "warn", "No images found.", 10)

    # 5. Word count
    wc = parser.word_count
    if wc >= 300:
        add_check("Content Length", "pass", f"{wc} words. Good length.", 10)
    elif wc >= 150:
        add_check("Content Length", "warn", f"{wc} words. Consider more content (300+).", 10)
    else:
        add_check("Content Length", "fail", f"Only {wc} words. Too thin.", 10)

    # 6. Canonical
    if parser.canonical:
        add_check("Canonical Tag", "pass", "Canonical URL set.", 10)
    else:
        add_check("Canonical Tag", "warn", "No canonical tag.", 10)

    # 7. Robots
    if "noindex" in parser.meta_robots.lower():
        add_check("Robots Meta", "fail", "Page is set to noindex.", 10)
    elif parser.meta_robots:
        add_check("Robots Meta", "pass", f"Robots: {parser.meta_robots}", 10)
    else:
        add_check("Robots Meta", "pass", "No restrictive robots meta (default index).", 10)

    # 8. HTTPS
    if url:
        scheme = urlparse(url).scheme.lower()
        if scheme == "https":
            add_check("HTTPS", "pass", "Page served over HTTPS.", 10)
        else:
            add_check("HTTPS", "fail", "Page not served over HTTPS.", 10)
    else:
        add_check("HTTPS", "warn", "No URL provided for HTTPS check.", 10)

    # Compute score
    total_weight = sum(c["weight"] for c in checks)
    earned = 0
    for c in checks:
        if c["status"] == "pass":
            earned += c["weight"]
        elif c["status"] == "warn":
            earned += c["weight"] * 0.5
    score = int((earned / total_weight) * 100) if total_weight else 0

    results["checks"] = checks
    results["score"] = score
    return results


# ----------------------------- History -----------------------------
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-50:], f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ----------------------------- GUI -----------------------------
class SEODashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(APP_SIZE)
        self.minsize(900, 600)
        self.configure(bg="#0f172a")

        self.history = load_history()
        self.current_result = None

        self._setup_styles()
        self._build_ui()

    # ---------- Styles ----------
    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        bg = "#0f172a"
        card = "#1e293b"
        accent = "#38bdf8"
        text = "#e2e8f0"
        muted = "#94a3b8"

        style.configure("TFrame", background=bg)
        style.configure("Card.TFrame", background=card)
        style.configure("TLabel", background=bg, foreground=text, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=bg, foreground=muted, font=("Segoe UI", 9))
        style.configure("Card.TLabel", background=card, foreground=text, font=("Segoe UI", 10))
        style.configure("CardMuted.TLabel", background=card, foreground=muted, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=bg, foreground=accent,
                        font=("Segoe UI", 20, "bold"))
        style.configure("Heading.TLabel", background=card, foreground=accent,
                        font=("Segoe UI", 12, "bold"))
        style.configure("Score.TLabel", background=card, foreground="#22c55e",
                        font=("Segoe UI", 36, "bold"))

        style.configure("Accent.TButton",
                        background=accent, foreground="#0f172a",
                        font=("Segoe UI", 10, "bold"),
                        borderwidth=0, padding=10)
        style.map("Accent.TButton",
                  background=[("active", "#0ea5e9"), ("pressed", "#0284c7")])

        style.configure("Ghost.TButton",
                        background=card, foreground=text,
                        font=("Segoe UI", 10),
                        borderwidth=0, padding=8)
        style.map("Ghost.TButton",
                  background=[("active", "#334155")])

        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", background=card, foreground=muted,
                        padding=[16, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", accent)],
                  foreground=[("selected", "#0f172a")])

        style.configure("Treeview",
                        background=card, fieldbackground=card,
                        foreground=text, rowheight=26,
                        borderwidth=0, font=("Segoe UI", 9))
        style.configure("Treeview.Heading",
                        background="#0b1220", foreground=accent,
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", accent)],
                  foreground=[("selected", "#0f172a")])

        style.configure("TProgressbar", troughcolor=card,
                        background=accent, borderwidth=0)

    # ---------- UI Build ----------
    def _build_ui(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(18, 8))

        ttk.Label(header, text="🔍 SEO Page Optimization Dashboard",
                  style="Title.TLabel").pack(side="left")

        ttk.Label(header, text="Analyze on-page SEO factors instantly",
                  style="Muted.TLabel").pack(side="left", padx=(14, 0), pady=(8, 0))

        # URL input row
        input_card = tk.Frame(self, bg="#1e293b", bd=0, highlightthickness=0)
        input_card.pack(fill="x", padx=20, pady=8)
        inner = tk.Frame(input_card, bg="#1e293b")
        inner.pack(fill="x", padx=14, pady=12)

        ttk.Label(inner, text="Page URL:", style="Card.TLabel").pack(side="left")

        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(
            inner, textvariable=self.url_var,
            bg="#0b1220", fg="#e2e8f0", insertbackground="#38bdf8",
            relief="flat", font=("Segoe UI", 11), bd=0
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=10, ipady=8)
        self.url_entry.insert(0, "https://example.com")
        self.url_entry.bind("<Return>", lambda e: self.start_analysis())

        self.analyze_btn = ttk.Button(inner, text="Analyze",
                                      style="Accent.TButton",
                                      command=self.start_analysis)
        self.analyze_btn.pack(side="left", padx=(0, 6))

        ttk.Button(inner, text="Load HTML",
                   style="Ghost.TButton",
                   command=self.load_local_html).pack(side="left")

        # Progress bar
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=20, pady=(0, 4))

        # Notebook (tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(8, 18))

        # Tab 1: Overview
        self.overview_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_tab, text="Overview")
        self._build_overview_tab()

        # Tab 2: Details
        self.details_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.details_tab, text="Page Details")
        self._build_details_tab()

        # Tab 3: History
        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="History")
        self._build_history_tab()

        # Status bar
        self.status_var = tk.StringVar(value="Ready.")
        status = ttk.Label(self, textvariable=self.status_var,
                           style="Muted.TLabel")
        status.pack(fill="x", padx=20, pady=(0, 10))

    # ---------- Overview Tab ----------
    def _build_overview_tab(self):
        container = tk.Frame(self.overview_tab, bg="#0f172a")
        container.pack(fill="both", expand=True, padx=8, pady=8)

        # Top: score + checks
        top = tk.Frame(container, bg="#0f172a")
        top.pack(fill="both", expand=True)

        # Score card
        score_card = tk.Frame(top, bg="#1e293b")
        score_card.pack(side="left", fill="y", padx=(0, 10))

        tk.Label(score_card, text="Overall Score",
                 bg="#1e293b", fg="#94a3b8",
                 font=("Segoe UI", 10, "bold")).pack(padx=24, pady=(18, 2))

        self.score_label = tk.Label(score_card, text="--",
                                    bg="#1e293b", fg="#38bdf8",
                                    font=("Segoe UI", 48, "bold"))
        self.score_label.pack(padx=24)

        self.score_grade = tk.Label(score_card, text="Awaiting analysis",
                                    bg="#1e293b", fg="#94a3b8",
                                    font=("Segoe UI", 10))
        self.score_grade.pack(pady=(0, 8))

        self.score_bar = ttk.Progressbar(score_card, length=180, mode="determinate",
                                         maximum=100)
        self.score_bar.pack(padx=24, pady=(0, 20))

        # Checks card
        checks_card = tk.Frame(top, bg="#1e293b")
        checks_card.pack(side="left", fill="both", expand=True)

        tk.Label(checks_card, text="SEO Checks",
                 bg="#1e293b", fg="#38bdf8",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(14, 6))

        columns = ("status", "check", "message")
        self.checks_tree = ttk.Treeview(checks_card, columns=columns,
                                        show="headings", height=12)
        self.checks_tree.heading("status", text="")
        self.checks_tree.heading("check", text="Check")
        self.checks_tree.heading("message", text="Result")
        self.checks_tree.column("status", width=40, anchor="center", stretch=False)
        self.checks_tree.column("check", width=160, anchor="w")
        self.checks_tree.column("message", width=380, anchor="w")
        self.checks_tree.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.checks_tree.tag_configure("pass", foreground="#22c55e")
        self.checks_tree.tag_configure("warn", foreground="#f59e0b")
        self.checks_tree.tag_configure("fail", foreground="#ef4444")

        # Stats row
        stats_row = tk.Frame(container, bg="#0f172a")
        stats_row.pack(fill="x", pady=(10, 0))

        self.stat_cards = {}
        labels = [
            ("words", "Word Count"),
            ("images", "Images"),
            ("links", "Links"),
            ("h1", "H1 Tags"),
            ("h2", "H2 Tags"),
            ("alt", "Missing Alt"),
        ]
        for key, label in labels:
            card = tk.Frame(stats_row, bg="#1e293b")
            card.pack(side="left", fill="x", expand=True, padx=4)
            tk.Label(card, text=label, bg="#1e293b", fg="#94a3b8",
                     font=("Segoe UI", 9)).pack(pady=(10, 0))
            val = tk.Label(card, text="--", bg="#1e293b", fg="#e2e8f0",
                           font=("Segoe UI", 16, "bold"))
            val.pack(pady=(0, 10))
            self.stat_cards[key] = val

    # ---------- Details Tab ----------
    def _build_details_tab(self):
        container = tk.Frame(self.details_tab, bg="#0f172a")
        container.pack(fill="both", expand=True, padx=8, pady=8)

        # Left: meta info
        left = tk.Frame(container, bg="#1e293b")
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        tk.Label(left, text="Meta Information", bg="#1e293b", fg="#38bdf8",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(12, 4))

        self.meta_text = scrolledtext.ScrolledText(
            left, wrap="word", bg="#0b1220", fg="#e2e8f0",
            insertbackground="#38bdf8", relief="flat",
            font=("Consolas", 10), height=20
        )
        self.meta_text.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # Right: structure
        right = tk.Frame(container, bg="#1e293b")
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))

        tk.Label(right, text="Page Structure", bg="#1e293b", fg="#38bdf8",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(12, 4))

        self.structure_text = scrolledtext.ScrolledText(
            right, wrap="word", bg="#0b1220", fg="#e2e8f0",
            insertbackground="#38bdf8", relief="flat",
            font=("Consolas", 10), height=20
        )
        self.structure_text.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    # ---------- History Tab ----------
    def _build_history_tab(self):
        container = tk.Frame(self.history_tab, bg="#0f172a")
        container.pack(fill="both", expand=True, padx=8, pady=8)

        top = tk.Frame(container, bg="#0f172a")
        top.pack(fill="x", pady=(0, 6))

        tk.Label(top, text="Recent Analyses", bg="#0f172a", fg="#38bdf8",
                 font=("Segoe UI", 12, "bold")).pack(side="left")

        ttk.Button(top, text="Clear History", style="Ghost.TButton",
                   command=self.clear_history).pack(side="right")

        columns = ("time", "url", "score", "issues")
        self.history_tree = ttk.Treeview(container, columns=columns,
                                         show="headings", height=14)
        self.history_tree.heading("time", text="Time")
        self.history_tree.heading("url", text="URL")
        self.history_tree.heading("score", text="Score")
        self.history_tree.heading("issues", text="Issues")
        self.history_tree.column("time", width=150, anchor="w")
        self.history_tree.column("url", width=450, anchor="w")
        self.history_tree.column("score", width=80, anchor="center")
        self.history_tree.column("issues", width=80, anchor="center")
        self.history_tree.pack(fill="both", expand=True)
        self.history_tree.bind("<Double-1>", self.load_history_entry)

        self.refresh_history()

    # ---------- Actions ----------
    def start_analysis(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a URL.")
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self.url_var.set(url)

        self.analyze_btn.config(state="disabled")
        self.progress.start(10)
        self.status_var.set(f"Fetching {url} ...")

        threading.Thread(target=self._analyze_thread, args=(url,), daemon=True).start()

    def _analyze_thread(self, url):
        try:
            html_content = fetch_url(url)
            result = analyze_seo(html_content, url)
            self.after(0, lambda: self._on_analysis_done(result))
        except urllib.error.HTTPError as e:
            self.after(0, lambda: self._on_analysis_error(f"HTTP Error {e.code}: {e.reason}"))
        except urllib.error.URLError as e:
            self.after(0, lambda: self._on_analysis_error(f"URL Error: {e.reason}"))
        except Exception as e:
            self.after(0, lambda: self._on_analysis_error(f"Error: {e}"))

    def _on_analysis_done(self, result):
        self.progress.stop()
        self.analyze_btn.config(state="normal")
        self.current_result = result

        score = result["score"]
        self.score_label.config(text=str(score))
        if score >= 80:
            color = "#22c55e"; grade = "Excellent"
        elif score >= 60:
            color = "#f59e0b"; grade = "Needs Work"
        else:
            color = "#ef4444"; grade = "Poor"
        self.score_label.config(fg=color)
        self.score_grade.config(text=grade)
        self.score_bar["value"] = score

        # Clear and fill checks
        for row in self.checks_tree.get_children():
            self.checks_tree.delete(row)
        for c in result["checks"]:
            icon = {"pass": "✓", "warn": "!", "fail": "✗"}[c["status"]]
            self.checks_tree.insert("", "end",
                                    values=(icon, c["name"], c["message"]),
                                    tags=(c["status"],))

        # Stats
        s = result["stats"]
        self.stat_cards["words"].config(text=str(s["word_count"]))
        self.stat_cards["images"].config(text=str(s["images_total"]))
        self.stat_cards["links"].config(text=str(s["links_total"]))
        self.stat_cards["h1"].config(text=str(s["h1_count"]))
        self.stat_cards["h2"].config(text=str(s["h2_count"]))
        self.stat_cards["alt"].config(text=str(s["images_missing_alt"]))

        # Details
        self._fill_details(result)

        # Save to history
        issues = sum(1 for c in result["checks"] if c["status"] != "pass")
        self.history.append({
            "time": result["analyzed_at"],
            "url": result["url"],
            "score": score,
            "issues": issues,
            "result": result,
        })
        save_history(self.history)
        self.refresh_history()

        self.status_var.set(f"Analysis complete for {result['url']}")

    def _on_analysis_error(self, msg):
        self.progress.stop()
        self.analyze_btn.config(state="normal")
        self.status_var.set("Analysis failed.")
        messagebox.showerror("Analysis Error", msg)

    def _fill_details(self, result):
        s = result["stats"]
        d = result["details"]

        meta = []
        meta.append(f"URL: {s.get('url') or result['url']}\n")
        meta.append(f"Analyzed: {result['analyzed_at']}\n")
        meta.append("=" * 50 + "\n")
        meta.append(f"TITLE ({s['title_length']} chars):\n{s['title'] or '(none)'}\n\n")
        meta.append(f"META DESCRIPTION ({s['meta_description_length']} chars):\n"
                    f"{s['meta_description'] or '(none)'}\n\n")
        meta.append(f"META KEYWORDS:\n{s['meta_keywords'] or '(none)'}\n\n")
        meta.append(f"CANONICAL:\n{s['canonical'] or '(none)'}\n\n")
        self.meta_text.delete("1.0", "end")
        self.meta_text.insert("1.0", "".join(meta))

        struct = []
        struct.append(f"H1 HEADINGS ({s['h1_count']}):\n")
        for h in d["h1"]:
            struct.append(f"  • {h}\n")
        struct.append(f"\nH2 HEADINGS ({s['h2_count']}):\n")
        for h in d["h2"]:
            struct.append(f"  • {h}\n")
        struct.append(f"\nIMAGES ({s['images_total']}, {s['images_missing_alt']} missing alt):\n")
        for img in d["images"][:15]:
            alt = img["alt"] or "(no alt)"
            src = img["src"][:60]
            struct.append(f"  • {src}  [alt: {alt}]\n")
        struct.append(f"\nLINKS ({s['links_total']}):\n")
        for ln in d["links"][:15]:
            struct.append(f"  • {ln['text'][:40]} → {ln['href'][:50]}\n")
        self.structure_text.delete("1.0", "end")
        self.structure_text.insert("1.0", "".join(struct))

    # ---------- Local HTML ----------
    def load_local_html(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select HTML file",
            filetypes=[("HTML files", "*.html *.htm"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                html_content = f.read()
            result = analyze_seo(html_content, url="file://" + path)
            self.url_var.set("file://" + path)
            self._on_analysis_done(result)
        except Exception as e:
            messagebox.showerror("File Error", str(e))

    # ---------- History ----------
    def refresh_history(self):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        for entry in reversed(self.history[-30:]):
            self.history_tree.insert("", "end",
                                     values=(entry["time"], entry["url"],
                                             entry["score"], entry["issues"]))

    def load_history_entry(self, event):
        sel = self.history_tree.selection()
        if not sel:
            return
        idx = self.history_tree.index(sel[0])
        # reversed index
        entry = list(reversed(self.history[-30:]))[idx]
        result = entry.get("result")
        if result:
            self._on_analysis_done(result)
            self.notebook.select(self.overview_tab)

    def clear_history(self):
        if messagebox.askyesno("Clear History", "Delete all analysis history?"):
            self.history = []
            save_history(self.history)
            self.refresh_history()


# ----------------------------- Main -----------------------------
if __name__ == "__main__":
    app = SEODashboard()
    app.mainloop()
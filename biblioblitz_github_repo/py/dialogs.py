#!/usr/bin/env python3
"""
dialogs.py - Reusable Selector Dialog Widgets
"""

import tkinter as tk
import tkinter.ttk as ttk
import webbrowser
import customtkinter as ctk

from py.config import (
    FONT_FAMILY, FONT_LABEL_SZ, FONT_ENTRY_SZ,
    BG_PANEL, BG_CARD, BG_ENTRY,
    BORDER_CLR, ACCENT_BLUE, ACCENT_TEAL,
    TEXT_BRIGHT, TEXT_MID,
)
from py.utils import bind_mouse_wheel


def _raise_window(win):
    """Force a CTkToplevel to appear on top and grab focus reliably."""
    win.lift()
    win.attributes("-topmost", True)
    win.after(50, lambda: win.attributes("-topmost", False))
    win.focus_force()


# ── YesNoDialog ───────────────────────────────────────────────────────────────

class YesNoDialog(ctk.CTkToplevel):
    """
    Simple Yes / No prompt.
    .result = True (Yes), False (No), None (closed without choosing).
    """

    def __init__(self, parent, title_text, message):
        super().__init__(parent)
        self.title(title_text)
        self.geometry("420x210")
        self.resizable(False, False)
        self.configure(fg_color=BG_PANEL)
        self.result = None
        self.protocol("WM_DELETE_WINDOW", self._cancelled)

        try:
            if hasattr(parent, '_icon_img'):
                self.wm_iconphoto(True, parent._icon_img)
        except Exception:
            pass

        ctk.CTkLabel(
            self, text=message,
            font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ),
            text_color=TEXT_BRIGHT, wraplength=340
        ).pack(padx=20, pady=(24, 16))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(padx=20, pady=(0, 20), fill="x")

        ctk.CTkButton(
            btn_row, text="Yes",
            fg_color=ACCENT_TEAL, text_color=BG_ENTRY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
            command=self._yes
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="No",
            fg_color=ACCENT_BLUE, text_color=BG_ENTRY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
            command=self._no
        ).pack(side="left", expand=True, fill="x")

        self.grab_set()
        self.after(10, lambda: _raise_window(self))

    def _yes(self):
        self.result = True
        self.destroy()

    def _no(self):
        self.result = False
        self.destroy()

    def _cancelled(self):
        self.result = None
        self.destroy()


# ── GenericSelectorDialog ─────────────────────────────────────────────────────

class GenericSelectorDialog(ctk.CTkToplevel):
    def __init__(self, parent, title_text, items_list, current_selections):
        super().__init__(parent)
        self.title(title_text)
        self.geometry("520x600")
        self.configure(fg_color=BG_PANEL)

        try:
            if hasattr(parent, '_icon_img'):
                self.wm_iconphoto(True, parent._icon_img)
        except Exception:
            pass

        self._all_items = items_list
        self._vars = {c: tk.BooleanVar(value=True)
                      for c in current_selections if c in items_list}
        self._last_q = None
        self._build()

        self.grab_set()
        self.after(10, lambda: _raise_window(self))

    def _var_for(self, item):
        if item not in self._vars:
            self._vars[item] = tk.BooleanVar(value=False)
        return self._vars[item]

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(top, text="🔍 Filter:",
                     font=ctk.CTkFont(family=FONT_FAMILY,
                                      size=FONT_LABEL_SZ, weight="bold"),
                     text_color=TEXT_BRIGHT).pack(side="left", padx=(0, 8))

        self._s_var = tk.StringVar()
        self._s_var.trace_add("write", self._on_filter)
        ctk.CTkEntry(top, textvariable=self._s_var, height=34,
                     fg_color=BG_ENTRY, border_color=BORDER_CLR,
                     text_color=TEXT_BRIGHT).pack(side="left", fill="x", expand=True)

        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_CARD, corner_radius=8,
            scrollbar_button_color=BORDER_CLR)
        self._scroll.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        bind_mouse_wheel(self._scroll, self._scroll)

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=14, pady=12)
        ctk.CTkButton(
            bf, text="✔ Lock Parameters", fg_color=ACCENT_BLUE,
            text_color=BG_ENTRY,
            font=ctk.CTkFont(family=FONT_FAMILY,
                             size=FONT_LABEL_SZ, weight="bold"),
            command=self._confirm
        ).pack(fill="x")
        self._render()

    def _render(self):
        q = self._s_var.get().lower() if hasattr(self, "_s_var") else ""
        if q == self._last_q:
            return
        self._last_q = q

        for w in self._scroll.winfo_children():
            w.destroy()

        for item in sorted(self._all_items, key=str.lower):
            if q and q not in item.lower():
                continue
            cb = ctk.CTkCheckBox(
                self._scroll, text=item,
                variable=self._var_for(item),
                font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ),
                text_color=TEXT_BRIGHT, fg_color=ACCENT_TEAL,
                border_color=BORDER_CLR)
            cb.pack(anchor="w", padx=8, pady=3)
            bind_mouse_wheel(cb, self._scroll)

    def _on_filter(self, *_):
        if hasattr(self, "_filter_job"):
            self.after_cancel(self._filter_job)
        self._filter_job = self.after(300, self._render)

    def _confirm(self):
        self._selected = [c for c, v in self._vars.items() if v.get()]
        self.destroy()

    def get_selected(self):
        return getattr(self, "_selected", [])


# ── GroupedJournalSelectorDialog ──────────────────────────────────────────────

class GroupedJournalSelectorDialog(ctk.CTkToplevel):

    def __init__(self, parent, title_text, journal_items, current_selections):
        super().__init__(parent)
        self.title(title_text)
        self.geometry("780x580")
        self.minsize(640, 460)
        self.configure(fg_color=BG_PANEL)

        try:
            if hasattr(parent, '_icon_img'):
                self.wm_iconphoto(True, parent._icon_img)
        except Exception:
            pass

        self._journal_items = journal_items
        self._all_items = sorted([
            f"{j.get('publisher') or 'Other journals'} :: {j['journal']}"
            for j in journal_items
        ], key=str.lower)

        self._selected_set = set(current_selections)
        self._last_q = None
        self._selection_changed = True
        self._filter_job = None
        self._selected = []

        self._build()

        self.grab_set()
        self.after(10, lambda: _raise_window(self))

    def _build(self):
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(
            search_frame, text="🔍 Search:",
            font=ctk.CTkFont(family=FONT_FAMILY,
                             size=FONT_LABEL_SZ, weight="bold"),
            text_color=TEXT_BRIGHT
        ).pack(side="left", padx=(0, 8))

        self._s_var = tk.StringVar()
        self._s_var.trace_add("write", self._on_filter)
        ctk.CTkEntry(
            search_frame, textvariable=self._s_var, height=34,
            fg_color=BG_ENTRY, border_color=BORDER_CLR, text_color=TEXT_BRIGHT
        ).pack(side="left", fill="x", expand=True)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=4)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=0)
        body.rowconfigure(1, weight=1)
        body.rowconfigure(2, weight=0)

        ctk.CTkLabel(body, text="Available Journals",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
                     text_color=TEXT_BRIGHT).grid(row=0, column=0, pady=(4, 2))
        ctk.CTkLabel(body, text="Selected Journals",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
                     text_color=TEXT_BRIGHT).grid(row=0, column=1, pady=(4, 2))

        avail_frame = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=6)
        avail_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 4))
        avail_scroll = tk.Scrollbar(avail_frame)
        avail_scroll.pack(side="right", fill="y")
        self.available_list = tk.Listbox(
            avail_frame, selectmode=tk.EXTENDED,
            yscrollcommand=avail_scroll.set,
            bg=BG_CARD, fg=TEXT_BRIGHT,
            selectbackground=ACCENT_TEAL, selectforeground=BG_ENTRY,
            font=(FONT_FAMILY, FONT_ENTRY_SZ),
            relief="flat", bd=0, activestyle="none", highlightthickness=0)
        self.available_list.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        avail_scroll.config(command=self.available_list.yview)
        self.available_list.bind("<Double-Button-1>", lambda e: self._add_selected())

        sel_frame = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=6)
        sel_frame.grid(row=1, column=1, sticky="nsew", padx=(4, 0))
        sel_scroll = tk.Scrollbar(sel_frame)
        sel_scroll.pack(side="right", fill="y")
        self.selected_list = tk.Listbox(
            sel_frame, selectmode=tk.EXTENDED,
            yscrollcommand=sel_scroll.set,
            bg=BG_CARD, fg=TEXT_BRIGHT,
            selectbackground=ACCENT_BLUE, selectforeground=BG_ENTRY,
            font=(FONT_FAMILY, FONT_ENTRY_SZ),
            relief="flat", bd=0, activestyle="none", highlightthickness=0)
        self.selected_list.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        sel_scroll.config(command=self.selected_list.yview)
        self.selected_list.bind("<Double-Button-1>", lambda e: self._remove_selected())

        btn_frame = ctk.CTkFrame(body, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(6, 2), sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_frame, text="Add →",
            fg_color=ACCENT_TEAL, text_color=BG_ENTRY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
            command=self._add_selected
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")

        ctk.CTkButton(
            btn_frame, text="← Remove",
            fg_color=ACCENT_BLUE, text_color=BG_ENTRY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
            command=self._remove_selected
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        ctk.CTkButton(
            self, text="✔ Lock Parameters",
            fg_color=ACCENT_BLUE, text_color=BG_ENTRY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
            command=self._confirm
        ).pack(fill="x", padx=12, pady=(6, 12))

        self._refresh_lists()

    def _refresh_lists(self):
        q = self._s_var.get().lower().strip() if hasattr(self, "_s_var") else ""
        if q == self._last_q and not self._selection_changed:
            return
        self._last_q = q
        self._selection_changed = False

        self.available_list.delete(0, tk.END)
        self.selected_list.delete(0, tk.END)

        for item in self._all_items:
            if item in self._selected_set:
                continue
            if q and q not in item.lower():
                continue
            self.available_list.insert(tk.END, item)

        for item in sorted(self._selected_set, key=str.lower):
            self.selected_list.insert(tk.END, item)

    def _on_filter(self, *_):
        if self._filter_job:
            self.after_cancel(self._filter_job)
        self._filter_job = self.after(350, self._refresh_lists)

    def _add_selected(self):
        for idx in list(self.available_list.curselection()):
            self._selected_set.add(self.available_list.get(idx))
        self._selection_changed = True
        self._refresh_lists()

    def _remove_selected(self):
        for idx in list(self.selected_list.curselection()):
            self._selected_set.discard(self.selected_list.get(idx))
        self._selection_changed = True
        self._refresh_lists()

    def _confirm(self):
        self._selected = sorted(self._selected_set, key=str.lower)
        self.destroy()

    def get_selected(self):
        return getattr(self, "_selected", [])


# ── ConfirmCloseDialog ────────────────────────────────────────────────────────

class ConfirmCloseDialog(ctk.CTkToplevel):
    """
    Exit confirmation dialog.
    Shows a stronger warning when download_running=True.
    .result = True means confirmed exit.
    """

    def __init__(self, parent, download_running=False):
        super().__init__(parent)
        self.title("Confirm Exit")
        self.geometry("420x200")
        self.resizable(False, False)
        self.configure(fg_color=BG_PANEL)
        self.result = False

        try:
            if hasattr(parent, '_icon_img'):
                self.wm_iconphoto(True, parent._icon_img)
        except Exception:
            pass

        if download_running:
            msg = ("⚠  A download pipeline is still running.\n"
                   "Closing now will abort the current job and\n"
                   "any progress will be lost.\n\n"
                   "Are you sure you want to exit?")
            exit_btn_color = "#E63946"
            exit_btn_text  = "Abort & Exit"
            cancel_text    = "Keep Running"
        else:
            msg = "Are you sure you want to close BiblioBlitz?"
            exit_btn_color = ACCENT_BLUE
            exit_btn_text  = "Exit"
            cancel_text    = "Cancel"

        ctk.CTkLabel(
            self, text=msg,
            font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ),
            text_color=TEXT_BRIGHT, wraplength=380, justify="center"
        ).pack(padx=20, pady=(24, 16))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(padx=20, pady=(0, 20), fill="x")

        ctk.CTkButton(
            btn_row, text=exit_btn_text,
            fg_color=exit_btn_color, text_color=BG_ENTRY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
            command=self._confirm
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text=cancel_text,
            fg_color=ACCENT_TEAL, text_color=BG_ENTRY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
            command=self._cancel
        ).pack(side="left", expand=True, fill="x")

        self.grab_set()
        self.after(10, lambda: _raise_window(self))

    def _confirm(self):
        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()


# ── ResultsTableDialog ────────────────────────────────────────────────────────

class ResultsTableDialog(ctk.CTkToplevel):
    """
    Full results table with horizontal scroll, column resizing,
    clickable DOI, and double-click to open source page.
    """

    COLUMNS = [
        "Authors", "Year", "Title", "Journal", "DOI",
        "APA Citation", "Open Access/Metadata Only",
        "Download Status", "Source API", "Country", "Publication Type"
    ]

    COL_WIDTHS = {
        "Authors":                   160,
        "Year":                       55,
        "Title":                     320,
        "Journal":                   180,
        "DOI":                       180,
        "APA Citation":              260,
        "Open Access/Metadata Only":  90,
        "Download Status":           110,
        "Source API":                110,
        "Country":                   100,
        "Publication Type":          120,
    }

    def __init__(self, parent, records):
        super().__init__(parent)
        self.title(f"Results — {len(records)} records")
        self.geometry("1200x650")
        self.minsize(900, 480)
        self.configure(fg_color=BG_PANEL)

        try:
            if hasattr(parent, '_icon_img'):
                self.wm_iconphoto(True, parent._icon_img)
        except Exception:
            pass

        self._records = records
        self._build(records)

        self.grab_set()
        self.after(10, lambda: _raise_window(self))

    def _build(self, records):
        # ── Top bar: search + export count ──────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 6))

        ctk.CTkLabel(
            top, text="🔍 Filter rows:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
            text_color=TEXT_BRIGHT
        ).pack(side="left", padx=(0, 8))

        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", self._on_filter)
        ctk.CTkEntry(
            top, textvariable=self._filter_var, height=32, width=280,
            fg_color=BG_ENTRY, border_color=BORDER_CLR, text_color=TEXT_BRIGHT
        ).pack(side="left")

        self._count_lbl = ctk.CTkLabel(
            top, text=f"{len(records)} records",
            font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ),
            text_color=TEXT_MID)
        self._count_lbl.pack(side="right", padx=8)

        ctk.CTkLabel(
            top,
            text="💡 Click DOI to open  •  Double-click row to open source page",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MID
        ).pack(side="right", padx=8)

        # ── Treeview with both scrollbars ────────────────────────────────────
        tree_frame = tk.Frame(self, bg=BG_CARD)
        tree_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "BiblioBlitz.Treeview",
            background=BG_CARD, foreground=TEXT_BRIGHT,
            fieldbackground=BG_CARD, rowheight=24,
            font=(FONT_FAMILY, FONT_ENTRY_SZ)
        )
        style.configure(
            "BiblioBlitz.Treeview.Heading",
            background=BG_ENTRY, foreground=TEXT_BRIGHT,
            font=(FONT_FAMILY, FONT_ENTRY_SZ, "bold")
        )
        style.map("BiblioBlitz.Treeview",
                  background=[("selected", ACCENT_BLUE)],
                  foreground=[("selected", BG_ENTRY)])

        yscroll = tk.Scrollbar(tree_frame, orient="vertical")
        xscroll = tk.Scrollbar(tree_frame, orient="horizontal")

        self._tree = ttk.Treeview(
            tree_frame,
            columns=self.COLUMNS,
            show="headings",
            yscrollcommand=yscroll.set,
            xscrollcommand=xscroll.set,
            style="BiblioBlitz.Treeview"
        )

        yscroll.config(command=self._tree.yview)
        xscroll.config(command=self._tree.xview)

        yscroll.pack(side="right",  fill="y")
        xscroll.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)

        for col in self.COLUMNS:
            self._tree.heading(col, text=col,
                               command=lambda c=col: self._sort_by(c, False))
            self._tree.column(col, width=self.COL_WIDTHS.get(col, 120),
                              minwidth=50, stretch=True)

        self._populate(records)

        self._tree.bind("<ButtonRelease-1>",  self._on_click)
        self._tree.bind("<Double-Button-1>",  self._on_double_click)

    def _row_values(self, rec):
        return tuple(str(rec.get(col, "") or "") for col in self.COLUMNS)

    def _populate(self, records):
        self._tree.delete(*self._tree.get_children())
        for rec in records:
            self._tree.insert("", tk.END, values=self._row_values(rec))
        self._count_lbl.configure(text=f"{len(records)} records")

    def _on_filter(self, *_):
        if hasattr(self, "_fj"):
            self.after_cancel(self._fj)
        self._fj = self.after(300, self._apply_filter)

    def _apply_filter(self):
        q = self._filter_var.get().lower().strip()
        if not q:
            self._populate(self._records)
            return
        filtered = [
            r for r in self._records
            if any(q in str(v).lower() for v in r.values())
        ]
        self._populate(filtered)

    def _doi_col_index(self):
        return self.COLUMNS.index("DOI")

    def _on_click(self, event):
        col_id = self._tree.identify_column(event.x)
        try:
            col_idx = int(col_id.replace("#", "")) - 1
        except ValueError:
            return
        if col_idx == self._doi_col_index():
            item = self._tree.identify_row(event.y)
            if not item:
                return
            doi = self._tree.item(item)["values"][col_idx]
            if doi:
                webbrowser.open(f"https://doi.org/{doi}")

    def _on_double_click(self, event):
        item = self._tree.identify_row(event.y)
        if not item:
            return
        values = self._tree.item(item)["values"]
        doi_idx = self._doi_col_index()
        doi = values[doi_idx] if doi_idx < len(values) else ""
        if doi:
            webbrowser.open(f"https://doi.org/{doi}")

    def _sort_by(self, col, reverse):
        data = [
            (self._tree.set(child, col), child)
            for child in self._tree.get_children("")
        ]
        data.sort(key=lambda x: x[0].lower(), reverse=reverse)
        for idx, (_, child) in enumerate(data):
            self._tree.move(child, "", idx)
        self._tree.heading(col, command=lambda: self._sort_by(col, not reverse))

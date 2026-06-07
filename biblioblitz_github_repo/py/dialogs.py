#!/usr/bin/env python3
"""
dialogs.py - Reusable Selector Dialog Widgets
"""

import tkinter as tk
import customtkinter as ctk

from py.config import (
    FONT_FAMILY, FONT_LABEL_SZ, FONT_ENTRY_SZ,
    BG_PANEL, BG_CARD, BG_ENTRY,
    BORDER_CLR, ACCENT_BLUE, ACCENT_TEAL,
    TEXT_BRIGHT, TEXT_MID,
)
from py.utils import bind_mouse_wheel


# ── GenericSelectorDialog ────────────────────────────────────────────────────

class GenericSelectorDialog(ctk.CTkToplevel):
    def __init__(self, parent, title_text, items_list, current_selections):
        super().__init__(parent)
        self.title(title_text)
        self.geometry("520x600")
        self.configure(fg_color=BG_PANEL)
        self.grab_set()

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


# ── GroupedJournalSelectorDialog ─────────────────────────────────────────────

class GroupedJournalSelectorDialog(ctk.CTkToplevel):

    def __init__(self, parent, title_text, journal_items, current_selections):
        super().__init__(parent)
        self.title(title_text)
        self.geometry("780x580")
        self.minsize(640, 460)
        self.configure(fg_color=BG_PANEL)
        self.grab_set()

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

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build(self):
        # ── Search bar ──
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

        # ── Body: Available | Selected ──
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=4)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=0)
        body.rowconfigure(1, weight=1)
        body.rowconfigure(2, weight=0)

        # Headers
        ctk.CTkLabel(
            body, text="Available Journals",
            font=ctk.CTkFont(family=FONT_FAMILY,
                             size=FONT_LABEL_SZ, weight="bold"),
            text_color=TEXT_BRIGHT
        ).grid(row=0, column=0, pady=(4, 2))

        ctk.CTkLabel(
            body, text="Selected Journals",
            font=ctk.CTkFont(family=FONT_FAMILY,
                             size=FONT_LABEL_SZ, weight="bold"),
            text_color=TEXT_BRIGHT
        ).grid(row=0, column=1, pady=(4, 2))

        # Available listbox
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
            relief="flat", bd=0, activestyle="none",
            highlightthickness=0
        )
        self.available_list.pack(
            side="left", fill="both", expand=True, padx=4, pady=4)
        avail_scroll.config(command=self.available_list.yview)
        self.available_list.bind(
            "<Double-Button-1>", lambda e: self._add_selected())

        # Selected listbox
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
            relief="flat", bd=0, activestyle="none",
            highlightthickness=0
        )
        self.selected_list.pack(side="left", fill="both",
                                expand=True, padx=4, pady=4)
        sel_scroll.config(command=self.selected_list.yview)
        self.selected_list.bind("<Double-Button-1>",
                                lambda e: self._remove_selected())

        # ── Add / Remove buttons ──
        btn_frame = ctk.CTkFrame(body, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(6, 2), sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_frame, text="Add →",
            fg_color=ACCENT_TEAL, text_color=BG_ENTRY,
            font=ctk.CTkFont(family=FONT_FAMILY,
                             size=FONT_LABEL_SZ, weight="bold"),
            command=self._add_selected
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")

        ctk.CTkButton(
            btn_frame, text="← Remove",
            fg_color=ACCENT_BLUE, text_color=BG_ENTRY,
            font=ctk.CTkFont(family=FONT_FAMILY,
                             size=FONT_LABEL_SZ, weight="bold"),
            command=self._remove_selected
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # ── Lock Parameters ──
        ctk.CTkButton(
            self, text="✔ Lock Parameters",
            fg_color=ACCENT_BLUE, text_color=BG_ENTRY,
            font=ctk.CTkFont(family=FONT_FAMILY,
                             size=FONT_LABEL_SZ, weight="bold"),
            command=self._confirm
        ).pack(fill="x", padx=12, pady=(6, 12))

        self._refresh_lists()

    # ── Data logic ───────────────────────────────────────────────────────────

    def _refresh_lists(self):
        q = self._s_var.get().lower().strip() if hasattr(self, "_s_var") else ""

        # Skip if nothing changed
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
        indices = list(self.available_list.curselection())
        for idx in indices:
            self._selected_set.add(self.available_list.get(idx))
        self._selection_changed = True
        self._refresh_lists()

    def _remove_selected(self):
        indices = list(self.selected_list.curselection())
        for idx in indices:
            self._selected_set.discard(self.selected_list.get(idx))
        self._selection_changed = True
        self._refresh_lists()

    def _confirm(self):
        self._selected = sorted(self._selected_set, key=str.lower)
        self.destroy()

    def get_selected(self):
        return getattr(self, "_selected", [])

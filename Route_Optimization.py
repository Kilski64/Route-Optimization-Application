
import tkinter as tk
import ttkbootstrap as ttk

import tkintermapview as tkm
import customtkinter as ctk
from tkcalendar import DateEntry
from tkinter import messagebox

import requests

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

import os
import json
from google import genai
from google.genai import types

from geopy.geocoders import Nominatim, ArcGIS
from geopy.extra.rate_limiter import RateLimiter

import pywinstyles

from datetime import date

import re

#INSERT API KEY GEMINI
API_KEY = ''


#USER AGENT
geolocator = Nominatim(user_agent="RouteForge Analytics Project")

#RATE LIMTER
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=3)
reverse = RateLimiter(geolocator.reverse, min_delay_seconds=3)

class Inital_Screen(ttk.Frame): 
    def __init__(self, parent, controller): 
        super().__init__(parent)
        self.controller = controller

        self.center_frame = ttk.Frame(self)
        self.center_frame.place(relx=0.5, rely=0.5, anchor="center")

        self.lbl_title = ttk.Label(self.center_frame, text="RouteForge", font=("Helvetica", 72))
        self.lbl_title.pack(pady=(0, 50))

        self.btn_new_optimizations = ttk.Button(self.center_frame, text="New Optimization", padding=(120, 20), command=lambda: controller.show_page("New_Optimizations"))
        self.btn_new_optimizations.pack(fill="x", pady=(0, 20))

        self.btn_load_optimizations = ttk.Button(self.center_frame, text="Load Optimizations", padding=(120, 20), command=lambda: controller.show_page("Load_Optimizations"))
        self.btn_load_optimizations.pack(fill="x", pady=(0, 20))

        self.btn_settings = ttk.Button(self.center_frame, text="Settings", padding=(120, 20), command=lambda: controller.show_page("Results")) #originally settings
        self.btn_settings.pack(fill="x", pady=(0, 20))

        self.btn_exit_app = ttk.Button(self.center_frame, text="Exit Application", padding=(120, 20), command=self.exit_application)
        self.btn_exit_app.pack(fill="x")

    def exit_application(self):
        # Displays a standard confirmation message box dialog
        response = messagebox.askyesno(
            title="Exit RouteForge",
            message="Are you sure you want to exit RouteForge?"
        )
        if response:  # If user clicks 'Yes'
            self.controller.destroy()

class New_Optimizations(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller


        self.stored_stops = {}
        self.stops_items = [] 
        self.pickup_delivery_pairs = []
        self.stored_vehicles_inputs = {}
        self.num_stored_vehicles = 0

        self.saved_optimizations = {}

        self.scroll_canvas = tk.Canvas(self, highlightthickness=0)
        self.scroller = ttk.Scrollbar(self, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=self.scroller.set)

        self.scroller.pack(side="right", fill="y")
        self.scroll_canvas.pack(side="left", fill="both", expand=True)

        self.inner_frame = ttk.Frame(self.scroll_canvas)
        self.canvas_window = self.scroll_canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.scroll_canvas.bind("<Configure>", self._on_canvas_configure)
        self.scroll_canvas.bind("<Enter>", self._bind_mousewheel)
        self.scroll_canvas.bind("<Leave>", self._unbind_mousewheel)

        self.title_section()
        self.general()
        self.locations_and_stops()
        self.pickups_and_deliveries()
        self.vehicles()
        self.optimization_settings()

        self.apply_edge_cases()

    def _bind_mousewheel(self, event):
        self.scroll_canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.scroll_canvas.bind_all("<Up>", self._on_key_scroll)
        self.scroll_canvas.bind_all("<Down>", self._on_key_scroll)

    def _unbind_mousewheel(self, event):
        self.scroll_canvas.unbind_all("<MouseWheel>")
        self.scroll_canvas.unbind_all("<Up>")
        self.scroll_canvas.unbind_all("<Down>")

    def _on_key_scroll(self, event):
        focused = self.focus_get()
        if isinstance(focused, (ttk.Entry, tk.Listbox, ttk.Combobox)):
            return
        if event.keysym == "Up":
            self.scroll_canvas.yview_scroll(-1, "units")
        elif event.keysym == "Down":
            self.scroll_canvas.yview_scroll(1, "units")
        self._dismiss_autopopulate_listboxes()
        

    def _on_frame_configure(self, event):
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.scroll_canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mouse_wheel(self, event):
        self.scroll_canvas.yview_scroll(-1 * int(event.delta / 120), "units")
        self._dismiss_autopopulate_listboxes()

    def apply_edge_cases(self):
        float_vcmd = self._make_float_vcmd()
        int_vcmd = self._make_int_vcmd()
        time_vcmd = self._make_time_vcmd()

        int_fields = [
            self.ent_start_location_load_time,
            self.ent_stops_location_load_time,
            self.ent_stops_location_unload_time,
            self.ent_depot_capacity
        ]
        
        for ent in int_fields:
            ent.config(validate='key', validatecommand=int_vcmd)

        float_fields = [
            self.ent_start_location_weight, 
            self.ent_start_location_volume,
            self.ent_stop_weight, 
            self.ent_stop_volume,
            self.ent_max_weight,
            self.ent_max_volume,
            self.ent_fixed_cost,
            self.ent_variable_cost,
            self.ent_max_travel,
            self.ent_break_wait,
            self.ent_penalty,
            self.ent_max_travel_distance_global
        ]
        
        for ent in float_fields:
            ent.config(validate='key', validatecommand=float_vcmd)

        # 4. Time Fields (HH:MM)
        time_fields = [
            self.ent_start_location_time_window_start, 
            self.ent_start_location_time_window_end,
            self.ent_time_window_start, 
            self.ent_time_window_end
        ]
        
        for ent in time_fields:
            ent.config(validate='key', validatecommand=time_vcmd)

        self.cmb_stop_type.bind("<<ComboboxSelected>>", self._apply_stop_demand_validation, add="+")
        self._apply_stop_demand_validation()

    def _make_float_vcmd(self):
        def validate(action, value_if_allowed):
            if action == '0': return True
            if value_if_allowed in ('', '.', '-'): return True
            try:
                float(value_if_allowed)
                return True
            except ValueError: return False
        return (self.register(validate), '%d', '%P')

    def _make_int_vcmd(self):
        def validate(action, value_if_allowed):
            return action == '0' or value_if_allowed == '' or value_if_allowed.isdigit()
        return (self.register(validate), '%d', '%P')

    def _make_neg_float_vcmd(self):
        def validate(action, value_if_allowed):
            if action == '0': return True
            if value_if_allowed in ('', '-', '-.'): return True
            try:
                val = float(value_if_allowed)
                return val <= 0
            except ValueError: return False
        return (self.register(validate), '%d', '%P')

    def _make_time_vcmd(self):
        def validate(action, index, text, value_if_allowed):
            if action == '0': return True
            if len(value_if_allowed) > 5: return False
            if index == '2': return text == ':'
            if index in ('0', '1', '3', '4'): return text.isdigit()
            return False
        return (self.register(validate), '%d', '%i', '%S', '%P')

    def _apply_stop_demand_validation(self, event=None):
        stop_type = self.cmb_stop_type.get()
        # Toggle between negative for delivery and normal float
        vcmd = self._make_neg_float_vcmd() if stop_type == "Delivery" else self._make_float_vcmd()
        
        color = "red" if stop_type == "Delivery" else "" 
        
        self.ent_stop_weight.config(validate='key', validatecommand=vcmd, foreground=color)
        self.ent_stop_volume.config(validate='key', validatecommand=vcmd, foreground=color)

    def title_section(self):
        self.title_frame = ttk.Frame(self.inner_frame, relief="groove", borderwidth=2)
        self.title_frame.pack(fill="x", padx=20, pady=(10, 0))

        # Left Column: Text Content
        self.title_text_frame = ttk.Frame(self.title_frame)
        self.title_text_frame.pack(side=tk.LEFT, fill="both", expand=True)

        self.lbl_title = ttk.Label(self.title_text_frame, text="New Optimizations", font=("Helvetica", 40))
        self.lbl_title.pack(side=tk.TOP, anchor=tk.NW, padx=(30, 0), pady=(10, 0))
        
        self.lbl_title_desc = ttk.Label(self.title_text_frame, text="Configure your route and vehicle parameters", font=("Helvetica", 16))
        self.lbl_title_desc.pack(side=tk.TOP, anchor=tk.NW, padx=(60, 0), pady=(2, 15))

        self.title_btn_frame = ttk.Frame(self.title_frame)
        self.title_btn_frame.pack(side=tk.RIGHT, padx=(0, 30), pady=10, fill="y")

        self.btn_back_initial = ttk.Button(
            self.title_btn_frame, 
            text="Back", 
            command=lambda: self.controller.show_page("Inital_Screen")
        )
        self.btn_back_initial.pack(expand=True)

    def general(self):
        
        self.general_container = ttk.Frame(self.inner_frame, relief="groove", borderwidth=2)
        self.general_container.pack(fill="x", padx=20, pady=(15, 0))

        self.general_inner = ttk.Frame(self.general_container)
        self.general_inner.pack(fill="x")
        self.general_inner.columnconfigure(0, weight=1)
        self.general_inner.columnconfigure(1, weight=1)

        self.lbl_general = ttk.Label(self.general_inner, text="General", font=("Helvetica", 16))
        self.lbl_general.grid(row=0, column=0, columnspan=2, padx=15, pady=(8, 4), sticky="w")

        self.lbl_optimization_name = ttk.Label(self.general_inner, text="Optimization Name", font=("Helvetica", 12))
        self.lbl_optimization_name.grid(row=1, column=0, padx=15, pady=(0, 2), sticky="w")

        self.lbl_start_date = ttk.Label(self.general_inner, text="Start Date", font=("Helvetica", 12))
        self.lbl_start_date.grid(row=1, column=1, padx=15, pady=(0, 2), sticky="w")

        self.ent_optimization_name = ttk.Entry(self.general_inner, font=("Arial", 12))
        self.ent_optimization_name.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="ew")

        self.cal = DateEntry(self.general_inner, width=12, foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.cal.grid(row=2, column=1, padx=15, pady=(0, 15), sticky="ew")

    def locations_and_stops(self):
        self.locations_container = ttk.Frame(self.inner_frame, relief="groove", borderwidth=2)
        self.locations_container.pack(fill="x", padx=20, pady=(15, 0))

        self.locations_inner = ttk.Frame(self.locations_container)
        self.locations_inner.pack(fill="x")
        self.locations_inner.columnconfigure(0, weight=1)
        self.locations_inner.columnconfigure(1, weight=1)

        self.lbl_locations = ttk.Label(self.locations_inner, text="Locations & Stops", font=("Helvetica", 16))
        self.lbl_locations.grid(row=0, column=0, columnspan=2, padx=15, pady=(8, 4), sticky="w")

        self.lbl_start_location = ttk.Label(self.locations_inner, text="Start Location", font=("Helvetica", 12))
        self.lbl_start_location.grid(row=1, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_start_location = ttk.Entry(self.locations_inner, font=("Arial", 12)) 
        self.ent_start_location.grid(row=2, column=0, padx=15, pady=(0, 8), sticky="ew")

        self.lbl_stops = ttk.Label(self.locations_inner, text="Stops", font=("Helvetica", 12))
        self.lbl_stops.grid(row=3, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_stops = ttk.Entry(self.locations_inner, font=("Arial", 12))
        self.ent_stops.grid(row=4, column=0, padx=15, pady=(0, 8), sticky="ew")

        self.lbl_stop_type = ttk.Label(self.locations_inner, text="Stop Type", font=("Helvetica", 12))
        self.lbl_stop_type.grid(row=5, column=0, padx=15, pady=(0, 2), sticky="w")

        self.cmb_stop_type = ttk.Combobox(self.locations_inner, font=("Arial", 12), values=["Pickup", "Delivery"])
        self.cmb_stop_type.grid(row=6, column=0, padx=15, pady=(0, 10), sticky="ew")

        self.lbl_demands = ttk.Label(self.locations_inner, text="Demands", font=("Helvetica", 16))
        self.lbl_demands.grid(row=7, column=0, columnspan=2, padx=15, pady=(8, 4), sticky="w")

        self.lbl_start_location_weight = ttk.Label(self.locations_inner, text="Start Weight (kg)", font=("Helvetica", 12))
        self.lbl_start_location_weight.grid(row=8, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_start_location_weight = ttk.Entry(self.locations_inner, font=("Arial", 12))
        self.ent_start_location_weight.grid(row=9, column=0, padx=15, pady=(0, 8), sticky="ew")

        self.lbl_start_location_volume = ttk.Label(self.locations_inner, text="Start Volume (m³)", font=("Helvetica", 12))
        self.lbl_start_location_volume.grid(row=10, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_start_location_volume = ttk.Entry(self.locations_inner, font=("Arial", 12))
        self.ent_start_location_volume.grid(row=11, column=0, padx=15, pady=(0, 8), sticky="ew")

        self.lbl_stop_weight = ttk.Label(self.locations_inner, text="Stop Weight (kg)", font=("Helvetica", 12))
        self.lbl_stop_weight.grid(row=12, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_stop_weight = ttk.Entry(self.locations_inner, font=("Arial", 12))
        self.ent_stop_weight.grid(row=13, column=0, padx=15, pady=(0, 8), sticky="ew")

        self.lbl_stop_volume = ttk.Label(self.locations_inner, text="Stop Volume (m³)", font=("Helvetica", 12))
        self.lbl_stop_volume.grid(row=14, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_stop_volume = ttk.Entry(self.locations_inner, font=("Arial", 12))
        self.ent_stop_volume.grid(row=15, column=0, padx=15, pady=(0, 8), sticky="ew")

        self.lbl_time_heading = ttk.Label(self.locations_inner, text="Start & Stop Time Windows", font=("Helvetica", 16))
        self.lbl_time_heading.grid(row=16, column=0, columnspan=2, padx=15, pady=(8, 4), sticky="w")

        self.lbl_start_location_time_window_start = ttk.Label(self.locations_inner, text="Start Location Time Window Start (HH:MM)", font=("Helvetica", 12))
        self.lbl_start_location_time_window_start.grid(row=17, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_start_location_time_window_start = ttk.Entry(self.locations_inner, font=("Arial", 12))
        self.ent_start_location_time_window_start.grid(row=18, column=0, padx=15, pady=(0, 8), sticky="ew")

        self.lbl_start_location_time_window_end = ttk.Label(self.locations_inner, text="Start Location Time Window End (HH:MM)", font=("Helvetica", 12))
        self.lbl_start_location_time_window_end.grid(row=19, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_start_location_time_window_end = ttk.Entry(self.locations_inner, font=("Arial", 12))
        self.ent_start_location_time_window_end.grid(row=20, column=0, padx=15, pady=(0, 8), sticky="ew")

        self.lbl_load_and_unload = ttk.Label(self.locations_inner, text="Load & Unload Times", font=("Helvetica", 16))
        self.lbl_load_and_unload.grid(row=21, column=0, columnspan=2, padx=15, pady=(8, 4), sticky="w")

        self.lbl_start_location_load_time = ttk.Label(self.locations_inner, text="Start Location Load Time (min)", font=("Helvetica", 12))
        self.lbl_start_location_load_time.grid(row=22, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_start_location_load_time = ttk.Entry(self.locations_inner, font=("Arial", 12))
        self.ent_start_location_load_time.grid(row=23, column=0, padx=15, pady=(0, 8), sticky="ew")

        self.lbl_stops_location_unload_time = ttk.Label(self.locations_inner, text="Stop Location Unload Time (min)", font=("Helvetica", 12))
        self.lbl_stops_location_unload_time.grid(row=24, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_stops_location_unload_time = ttk.Entry(self.locations_inner, font=("Arial", 12))
        self.ent_stops_location_unload_time.grid(row=25, column=0, padx=15, pady=(0, 8), sticky="ew")

        self.lst_stops = tk.Listbox(self.locations_inner, font=("Arial", 11), height=10)
        self.lst_stops.grid(row=26, column=0, columnspan=2, padx=15, pady=(0, 8), sticky="ew")

        self.btn_add_stop = ttk.Button(self.locations_inner, text="+ Add Stop", command=self.add_stops_to_listbox)
        self.btn_add_stop.grid(row=27, column=0, padx=15, pady=(0, 15), sticky="w")

        self.lbl_map_placeholder = ttk.Label(self.locations_inner, text="Map Preview", font=("Helvetica", 12))
        self.lbl_map_placeholder.grid(row=1, column=1, padx=15, pady=(0, 2), sticky="w")

        # Move "Time Window Start" under the map
        self.lbl_time_window_start = ttk.Label(self.locations_inner, text="Stop Location Time Window Start (HH:MM)", font=("Helvetica", 12))
        self.lbl_time_window_start.grid(row=17, column=1, padx=15, pady=(0, 2), sticky="w") # Added 10px top padding

        self.ent_time_window_start = ttk.Entry(self.locations_inner, font=("Arial", 12))
        self.ent_time_window_start.grid(row=18, column=1, padx=15, pady=(0, 8), sticky="ew")

        # Move "Time Window End" under the map
        self.lbl_time_window_end = ttk.Label(self.locations_inner, text="Stop Location Time Window End (HH:MM)", font=("Helvetica", 12))
        self.lbl_time_window_end.grid(row=19, column=1, padx=15, pady=(0, 2), sticky="w")

        self.ent_time_window_end = ttk.Entry(self.locations_inner, font=("Arial", 12))
        self.ent_time_window_end.grid(row=20, column=1, padx=15, pady=(0, 8), sticky="ew")

        #Stop Locations Load and Unload times
        self.lbl_stops_location_load_time = ttk.Label(self.locations_inner, text="Stop Location Load Time (min)", font=("Helvetica", 12))
        self.lbl_stops_location_load_time.grid(row=22, column=1, padx=15, pady=(0, 2), sticky="w")

        self.ent_stops_location_load_time = ttk.Entry(self.locations_inner, font=("Arial", 12))
        self.ent_stops_location_load_time.grid(row=23, column=1, padx=15, pady=(0, 8), sticky="ew")

        self.frm_map_placeholder = ttk.Frame(self.locations_inner, relief="flat", borderwidth=2)
        self.frm_map_placeholder.grid(row=2, column=1, rowspan=14, padx=15, pady=(0, 8), sticky="nsew")


        self.lbl_map_placeholder_text = ttk.Label(self.frm_map_placeholder, text="[ Map / Drag & Drop Pin ]", font=("Helvetica", 11), foreground="gray")
        self.lbl_map_placeholder_text.pack(padx=60, pady=60)

        self.overlay_frame = ttk.Frame(self)

        self.overlay_frame.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)

        pywinstyles.set_opacity(self.overlay_frame, 0.1)

        self.overlay_frame.place_forget()

        self.lb_start_location = tk.Listbox(
            self.scroll_canvas, 
            font=("Arial", 11),
            height=10,
            width=81,
            relief="solid",
            borderwidth=1,
            selectbackground="#0078d7",
            selectforeground="white",
        )

        self.lb_start_location.place_forget()

        self.lb_stops = tk.Listbox(
            self.scroll_canvas, 
            font=("Arial", 11),
            height=8,
            width=81,
            relief="solid",
            borderwidth=1,
            selectbackground="#0078d7",
            selectforeground="white",
        )
        
        self.lb_stops.place_forget()

        self.ent_start_location.bind("<Return>", self.start_marker_via_text_input)

        self.ent_start_location.bind("<KeyRelease>", self.filter_addresses)
        self.lb_start_location.bind("<Double-Button-1>", self.double_click_listbox_item)

        self.ent_stops.bind("<KeyRelease>", self.filter_addresses)
        self.lb_stops.bind("<Double-Button-1>", self.double_click_listbox_item)

        self.overlay_frame.bind("<Button-1>", self.cancel_listboxs_through_outside_clicks)
        
        self.create_map_widget()


    def create_map_widget(self):
        self.map_widget = tkm.TkinterMapView(self.locations_container, width=760, height=200)

        # Wait for layout to settle before placing
        self.locations_container.after(50, self._place_map_widget)

        # Re-place on resize
        self.locations_container.bind("<Configure>", lambda e: self._place_map_widget())

        self.map_widget.set_position(40.7128, -74.0060)
        self.map_widget.set_zoom(13)

        self.map_widget.add_right_click_menu_command(
            label="Add Start Marker",
            command=self.start_marker_via_map_widget,
            pass_coords=True
        )

    
    def _place_map_widget(self):
        self.frm_map_placeholder.update_idletasks()

        x = self.frm_map_placeholder.winfo_rootx() - self.locations_container.winfo_rootx()
        y = self.frm_map_placeholder.winfo_rooty() - self.locations_container.winfo_rooty()
        w = self.frm_map_placeholder.winfo_width()
        h = self.frm_map_placeholder.winfo_height()

        self.map_widget.place(x=x, y=y, width=w, height=h)
        
    def select_widget_based_on_focus(self):
        # Get the widget that currently has focus in the application
        self.current_widget_focus = self.focus_get()

        if self.current_widget_focus == self.ent_start_location:
            return self.ent_start_location, self.lb_start_location
        elif self.current_widget_focus == self.ent_stops:
            return self.ent_stops, self.lb_stops
        else:
            return None, None

    def filter_addresses(self, event):
        self.entry, self.listbox = self.select_widget_based_on_focus()
        query = self.entry.get()

        if len(query) <= 3:
            return
        
        locations = geolocator.geocode(query, country_codes=['us'], exactly_one=False, limit=6)
        results = [loc.address for loc in locations] if locations else []

        if self.current_widget_focus == self.ent_start_location:
            self.entry = self.ent_start_location
            self.listbox = self.lb_start_location

        elif self.current_widget_focus == self.ent_stops:
            self.entry = self.ent_stops
            self.listbox = self.lb_stops

        else:
            return

        x = self.entry.winfo_rootx() - self.scroll_canvas.winfo_rootx()
        y = self.entry.winfo_rooty() - self.scroll_canvas.winfo_rooty() + self.entry.winfo_height()
        w = self.entry.winfo_width()

        self.listbox.place(x=x, y=y, width=w)

        self.listbox.lift()

        self.winfo_toplevel().bind("<Button-1>", self.cancel_listboxs_through_outside_clicks, add="+")

        self.listbox.delete(0, tk.END)
        for address in results:
            self.listbox.insert(tk.END, address)


    def double_click_listbox_item(self, event):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            return

        index = selected_indices[0]
        selected_item = self.listbox.get(index)

        self.entry.delete(0, tk.END)
        self.entry.insert(0, selected_item)

        self.listbox.place_forget()
        
        self.winfo_toplevel().unbind("<Button-1>")

        if self.entry == self.ent_start_location:
            try:
                location = geolocator.geocode(selected_item, timeout=10)
                if location:
                    # Clear any existing start markers first
                    if hasattr(self, '_start_marker') and self._start_marker:
                        self._start_marker.delete()

                    self._start_marker = self.map_widget.set_marker(
                        location.latitude,
                        location.longitude,
                        text="Start"
                    )
                    self.map_widget.set_position(location.latitude, location.longitude)
                    self.map_widget.set_zoom(13)
            except Exception as e:
                print(f"Failed to geocode start location: {e}")    
    
    def cancel_listboxs_through_outside_clicks(self, event):
        clicked_widget = event.widget
        
        if not hasattr(self, 'listbox') or not self.listbox or not self.listbox.winfo_manager():
            return

        if clicked_widget == self.entry or clicked_widget == self.listbox:
            return
            
        self.listbox.place_forget()
        
        self.winfo_toplevel().unbind("<Button-1>")                
        
         
    def _dismiss_autopopulate_listboxes(self):
        if hasattr(self, 'lb_start_location') and self.lb_start_location.winfo_manager():
            self.lb_start_location.place_forget()
        if hasattr(self, 'lb_stops') and self.lb_stops.winfo_manager():
            self.lb_stops.place_forget()
            

    
    def start_marker_via_text_input(self, event):
        start_marker_pin_input = self.ent_start_location.get()

        location = geolocator.geocode(start_marker_pin_input)

        lat = location.latitude
        lon = location.longitude

        self.map_widget.set_marker(lat, lon, text=start_marker_pin_input)

        self.map_widget.set_position(lat, lon)

    
    def add_stops_to_listbox(self):
        get_stop = self.ent_stops.get()
        get_weight = self.ent_stop_weight.get()
        get_volume = self.ent_stop_volume.get()
        get_tw_start = self.ent_time_window_start.get()
        get_tw_end = self.ent_time_window_end.get()
        get_stop_locations_load_times = self.ent_stops_location_load_time.get()
        get_stop_locations_unload_times = self.ent_stops_location_unload_time.get()
        get_stop_type = self.cmb_stop_type.get()

        stop_entry = {
            "address": get_stop,
            "weight": float(get_weight) if get_weight else 0.0,
            "volume": float(get_volume) if get_volume else 0.0,
            "time_window_start": get_tw_start if get_tw_start else "00:00",
            "time_window_end": get_tw_end if get_tw_end else "23:59",
            "load_times": get_stop_locations_load_times if get_stop_locations_load_times else 0,
            "unload_times": get_stop_locations_unload_times if get_stop_locations_unload_times else 0,
            "stop_type": get_stop_type if get_stop_type else "Pickup"
        }

        self.stops_items.append(stop_entry)

        self.ent_stops.delete(0, tk.END)
        self.ent_stop_weight.delete(0, tk.END)
        self.ent_stop_volume.delete(0, tk.END)
        self.ent_time_window_start.delete(0, tk.END)
        self.ent_time_window_end.delete(0, tk.END)
        self.ent_stops_location_load_time.delete(0, tk.END)
        self.ent_stops_location_unload_time.delete(0, tk.END)
        self.cmb_stop_type.set("")

        self.lst_stops.delete(0, tk.END)
        for item in self.stops_items:
            self.lst_stops.insert(tk.END, f"{item['address']} | {item['weight']}kg | {item['volume']}m³ | {item['time_window_start']}-{item['time_window_end']} | {item['load_times']} | {item['unload_times']} | {item['load_times']} | {item['unload_times']} | {item['stop_type']}")

        self.refresh_pd_dropdowns()

        try:
            location = geolocator.geocode(get_stop, timeout=10)
            if location:
                stop_num = len(self.stops_items)
                marker = self.map_widget.set_marker(
                    location.latitude,
                    location.longitude,
                    text=f"Stop {stop_num}"
                )
    
                if not hasattr(self, '_stop_markers'):
                    self._stop_markers = []
                self._stop_markers.append(marker)

                self.map_widget.set_position(location.latitude, location.longitude)
        except Exception as e:
            print(f"Failed to geocode stop '{get_stop}': {e}")

       
    def start_marker_via_map_widget(self, coords):
        self.map_widget.set_marker(coords[0], coords[1], text=f"({coords[0]}, {coords[1]})")

        self.ent_start_location.delete(0, tk.END)
        self.ent_start_location.insert(tk.END, f"{coords[0]}, {coords[1]}")


    def pickups_and_deliveries(self):
        self.pickups_and_deliveries_container = ttk.Frame(self.inner_frame, relief="groove", borderwidth=2)
        self.pickups_and_deliveries_container.pack(fill="x", padx=20, pady=(15, 0))

        self.pd_inner = ttk.Frame(self.pickups_and_deliveries_container)
        self.pd_inner.pack(fill="x")
        self.pd_inner.columnconfigure(0, weight=1)
        self.pd_inner.columnconfigure(1, weight=1)

        self.lbl_pd = ttk.Label(self.pd_inner, text="Pickup & Delivery Pairs", font=("Helvetica", 16))
        self.lbl_pd.grid(row=0, column=0, columnspan=2, padx=15, pady=(8, 4), sticky="w")

        self.lbl_pd_desc = ttk.Label(
            self.pd_inner,
            text="Pair a pickup stop with its corresponding delivery stop.",
            font=("Helvetica", 10), foreground="gray"
        )
        self.lbl_pd_desc.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 8), sticky="w")

        self.lbl_pickup_from = ttk.Label(self.pd_inner, text="Pickup From", font=("Helvetica", 12))
        self.lbl_pickup_from.grid(row=2, column=0, padx=15, pady=(0, 2), sticky="w")

        self.cmb_pickup_from = ttk.Combobox(self.pd_inner, font=("Arial", 12), state="readonly")
        self.cmb_pickup_from.grid(row=3, column=0, padx=15, pady=(0, 10), sticky="ew")

        self.lbl_deliver_to = ttk.Label(self.pd_inner, text="Deliver To", font=("Helvetica", 12))
        self.lbl_deliver_to.grid(row=2, column=1, padx=15, pady=(0, 2), sticky="w")

        self.cmb_deliver_to = ttk.Combobox(self.pd_inner, font=("Arial", 12), state="readonly")
        self.cmb_deliver_to.grid(row=3, column=1, padx=15, pady=(0, 10), sticky="ew")

        self.btn_add_pair = ttk.Button(self.pd_inner, text="+ Add Pair", command=self.add_pickup_delivery_pairs)
        self.btn_add_pair.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="w")

        self.lbl_pd_pairs = ttk.Label(self.pd_inner, text="Configured Pairs", font=("Helvetica", 12))
        self.lbl_pd_pairs.grid(row=5, column=0, columnspan=2, padx=15, pady=(0, 2), sticky="w")

        self.lst_pd_pairs = tk.Listbox(self.pd_inner, font=("Arial", 11), height=6)
        self.lst_pd_pairs.grid(row=6, column=0, columnspan=2, padx=15, pady=(0, 8), sticky="ew")

        self.btn_remove_pair = ttk.Button(self.pd_inner, text="Remove Selected", command=self.remove_pickup_delivery_pair)
        self.btn_remove_pair.grid(row=7, column=0, padx=15, pady=(0, 15), sticky="w")


    def add_pickup_delivery_pairs(self):
        pickup_addr  = self.cmb_pickup_from.get()
        deliver_addr = self.cmb_deliver_to.get()

        if not pickup_addr or not deliver_addr:
            return  

        if pickup_addr == deliver_addr:
            return  

        for pair in self.pickup_delivery_pairs:
            if pair["pickup"] == pickup_addr and pair["delivery"] == deliver_addr:
                return

        pair_entry = {"pickup": pickup_addr, "delivery": deliver_addr}
        self.pickup_delivery_pairs.append(pair_entry)

        self.lst_pd_pairs.delete(0, tk.END)
        for idx, pair in enumerate(self.pickup_delivery_pairs, start=1):
            self.lst_pd_pairs.insert(tk.END, f"Pair {idx}:  ↑ {pair['pickup']}  →  ↓ {pair['delivery']}")

        self.cmb_pickup_from.set("")
        self.cmb_deliver_to.set("")


    def remove_pickup_delivery_pair(self):
        selected = self.lst_pd_pairs.curselection()
        if not selected:
            return

        idx = selected[0]
        del self.pickup_delivery_pairs[idx]

        self.lst_pd_pairs.delete(0, tk.END)
        for i, pair in enumerate(self.pickup_delivery_pairs, start=1):
            self.lst_pd_pairs.insert(tk.END, f"Pair {i}:  ↑ {pair['pickup']}  →  ↓ {pair['delivery']}")


    def refresh_pd_dropdowns(self):
        pickup_stops  = [s["address"] for s in self.stops_items if s.get("stop_type") == "Pickup"]
        delivery_stops = [s["address"] for s in self.stops_items if s.get("stop_type") == "Delivery"]

        self.cmb_pickup_from["values"] = pickup_stops
        self.cmb_deliver_to["values"]  = delivery_stops

        if self.cmb_pickup_from.get() not in pickup_stops:
            self.cmb_pickup_from.set("")
        if self.cmb_deliver_to.get() not in delivery_stops:
            self.cmb_deliver_to.set("")


    def vehicles(self):
        self.vehicles_container = ttk.Frame(self.inner_frame, relief="groove", borderwidth=2)
        self.vehicles_container.pack(fill="x", padx=20, pady=(15, 0))

        self.vehicles_inner = ttk.Frame(self.vehicles_container)
        self.vehicles_inner.pack(fill="x")
        self.vehicles_inner.columnconfigure(0, weight=1)
        self.vehicles_inner.columnconfigure(1, weight=1)
        self.vehicles_inner.columnconfigure(2, weight=1)

        self.lbl_vehicles = ttk.Label(self.vehicles_inner, text="Vehicles", font=("Helvetica", 16))
        self.lbl_vehicles.grid(row=0, column=0, columnspan=3, padx=15, pady=(8, 4), sticky="w")

        self.lbl_vehicle_id = ttk.Label(self.vehicles_inner, text="Vehicle ID / Name", font=("Helvetica", 12))
        self.lbl_vehicle_id.grid(row=1, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_vehicle_id = ttk.Entry(self.vehicles_inner, font=("Arial", 12))
        self.ent_vehicle_id.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="ew")

        self.lbl_profile = ttk.Label(self.vehicles_inner, text="Profile / Mode", font=("Helvetica", 12))
        self.lbl_profile.grid(row=1, column=1, padx=15, pady=(0, 2), sticky="w")

        self.cmb_profile = ttk.Combobox(self.vehicles_inner, font=("Arial", 12), values=["Driving-Car", "Driving-HGV", "Cycling", "Walking"])
        self.cmb_profile.grid(row=2, column=1, padx=15, pady=(0, 10), sticky="ew")

        self.lbl_capacity = ttk.Label(self.vehicles_inner, text="Capacity", font=("Helvetica", 12))
        self.lbl_capacity.grid(row=3, column=0, columnspan=3, padx=15, pady=(0, 2), sticky="w")

        self.lbl_max_weight = ttk.Label(self.vehicles_inner, text="Max Weight (kg)", font=("Helvetica", 11))
        self.lbl_max_weight.grid(row=4, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_max_weight = ttk.Entry(self.vehicles_inner, font=("Arial", 12))
        self.ent_max_weight.grid(row=5, column=0, padx=15, pady=(0, 10), sticky="ew")

        self.lbl_max_volume = ttk.Label(self.vehicles_inner, text="Max Volume (m³)", font=("Helvetica", 11))
        self.lbl_max_volume.grid(row=4, column=1, padx=15, pady=(0, 2), sticky="w")

        self.ent_max_volume = ttk.Entry(self.vehicles_inner, font=("Arial", 12))
        self.ent_max_volume.grid(row=5, column=1, padx=15, pady=(0, 10), sticky="ew")

        self.lbl_depot_capacity = ttk.Label(self.vehicles_inner, text="Depot Capacity (num of vehicles)", font=("Helvetica", 11))
        self.lbl_depot_capacity.grid(row=4, column=2, padx=15, pady=(0, 2), sticky="w")

        self.ent_depot_capacity = ttk.Entry(self.vehicles_inner, font=("Arial", 12))
        self.ent_depot_capacity.grid(row=5, column=2, padx=15, pady=(0, 10), sticky="ew")

        self.lbl_fixed_cost = ttk.Label(self.vehicles_inner, text="Fixed Cost ($/day)", font=("Helvetica", 12))
        self.lbl_fixed_cost.grid(row=15, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_fixed_cost = ttk.Entry(self.vehicles_inner, font=("Arial", 12))
        self.ent_fixed_cost.grid(row=16, column=0, padx=15, pady=(0, 10), sticky="ew")

        self.lbl_variable_cost = ttk.Label(self.vehicles_inner, text="Variable Cost ($/km)", font=("Helvetica", 12))
        self.lbl_variable_cost.grid(row=15, column=1, padx=15, pady=(0, 2), sticky="w")

        self.ent_variable_cost = ttk.Entry(self.vehicles_inner, font=("Arial", 12))
        self.ent_variable_cost.grid(row=16, column=1, padx=15, pady=(0, 10), sticky="ew")

        self.lbl_skills = ttk.Label(self.vehicles_inner, text="Skills / Tags", font=("Helvetica", 12))
        self.lbl_skills.grid(row=17, column=0, columnspan=3, padx=15, pady=(0, 2), sticky="w")

        self.frm_skills_placeholder = ttk.Frame(self.vehicles_inner, relief="groove", borderwidth=2)
        self.frm_skills_placeholder.grid(row=18, column=0, columnspan=3, padx=15, pady=(0, 10), sticky="ew")

        self.current_skills = []
        
        self.frm_skills_placeholder = ttk.Frame(self.vehicles_inner, relief="groove", borderwidth=2)
        self.frm_skills_placeholder.grid(row=18, column=0, columnspan=3, padx=15, pady=(0, 10), sticky="ew")

        self.skills_display_frame = ttk.Frame(self.frm_skills_placeholder)
        self.skills_display_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.btn_add_skills = ttk.Button(self.skills_display_frame, text="+ Add skill", command=self.show_skill_input)
        self.btn_add_skills.pack(side="left", padx=2, pady=2)

    
    def show_skill_input(self):
        skill_popup = tk.Toplevel(self)
        skill_popup.title("Add Skill")
        skill_popup.geometry("300x120")
        skill_popup.transient(self)
        skill_popup.grab_set()
        
        skill_popup.update_idletasks()
        x = (skill_popup.winfo_screenwidth() // 2) - (300 // 2)
        y = (skill_popup.winfo_screenheight() // 2) - (120 // 2)
        skill_popup.geometry(f"300x120+{x}+{y}")
        
        ttk.Label(skill_popup, text="Enter skill name:", font=("Helvetica", 10)).pack(pady=(15, 5))
        
        skill_entry = ttk.Entry(skill_popup, font=("Arial", 12), width=25)
        skill_entry.pack(pady=5)
        skill_entry.focus()
        
        def add_skill_from_popup():
            skill_text = skill_entry.get().strip()
            if skill_text:
                self.add_skill(skill_text)
                skill_popup.destroy()
        
        skill_entry.bind("<Return>", lambda e: add_skill_from_popup())
        
        button_frame = ttk.Frame(skill_popup)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Add", command=add_skill_from_popup).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=skill_popup.destroy).pack(side="left", padx=5)

    def add_skill(self, skill_text):
        if skill_text not in self.current_skills:
            self.current_skills.append(skill_text)
            
            skill_frame = ttk.Frame(self.skills_display_frame, relief="solid", borderwidth=1)
            skill_frame.pack(side="left", padx=2, pady=2)
            
            skill_label = ttk.Label(skill_frame, text=skill_text, font=("Arial", 9), padding=(8, 4))
            skill_label.pack(side="left")

            remove_btn = ttk.Button(
                skill_frame, 
                text="×", 
                width=2,
                command=lambda: self.remove_skill(skill_text, skill_frame)
            )
            remove_btn.pack(side="left", padx=(2, 0))
            
            self.btn_add_skills.pack_forget()
            self.btn_add_skills.pack(side="left", padx=2, pady=2)

    def remove_skill(self, skill_text, skill_frame):
        if skill_text in self.current_skills:
            self.current_skills.remove(skill_text)
            skill_frame.destroy()
   

    def optimization_settings(self):
        self.settings_container = ttk.Frame(self.inner_frame, relief="groove", borderwidth=2)
        self.settings_container.pack(fill="x", padx=20, pady=(15, 0))

        self.settings_inner = ttk.Frame(self.settings_container)
        self.settings_inner.pack(fill="x")
        self.settings_inner.columnconfigure(0, weight=1)
        self.settings_inner.columnconfigure(1, weight=1)

        self.lbl_settings = ttk.Label(self.settings_inner, text="Optimization Settings", font=("Helvetica", 16))
        self.lbl_settings.grid(row=0, column=0, columnspan=2, padx=15, pady=(8, 4), sticky="w")

        self.lbl_max_travel = ttk.Label(self.settings_inner, text="Max Travel Time per Vehicle (min)", font=("Helvetica", 12))
        self.lbl_max_travel.grid(row=1, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_max_travel = ttk.Entry(self.settings_inner, font=("Arial", 12))
        self.ent_max_travel.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="ew")

        self.lbl_break_wait = ttk.Label(self.settings_inner, text="Break / Wait Allowance (min)", font=("Helvetica", 12))
        self.lbl_break_wait.grid(row=1, column=1, padx=15, pady=(0, 2), sticky="w")

        self.ent_break_wait = ttk.Entry(self.settings_inner, font=("Arial", 12))
        self.ent_break_wait.grid(row=2, column=1, padx=15, pady=(0, 10), sticky="ew")

        self.lbl_penalty = ttk.Label(self.settings_inner, text="Late Arrival Penalty Weight", font=("Helvetica", 12))
        self.lbl_penalty.grid(row=3, column=0, padx=15, pady=(0, 2), sticky="w")

        self.ent_penalty = ttk.Entry(self.settings_inner, font=("Arial", 12))
        self.ent_penalty.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="ew")

        self.lbl_max_travel_distance_global = ttk.Label(self.settings_inner, text="Max Travel Distance per Vehicle (km)", font=("Helvetica", 12))
        self.lbl_max_travel_distance_global.grid(row=3, column=1, padx=15, pady=(0, 2), sticky="w")

        self.ent_max_travel_distance_global = ttk.Entry(self.settings_inner, font=("Arial", 12))
        self.ent_max_travel_distance_global.grid(row=4, column=1, padx=15, pady=(0, 10), sticky="ew")
       
        self.penalty_row_container = ttk.Frame(self.settings_inner)
        self.penalty_row_container.grid(row=5, column=0, padx=15, pady=(4, 2), sticky="w")

        self.lbl_allow_penalty = ttk.Label(self.penalty_row_container, text="Allow Penalty", font=("Helvetica", 12))
        self.lbl_allow_penalty.pack(side="left", padx=15)

        self.var_penalty_enabled = tk.BooleanVar(value=False)
        self.chk_penalty_enabled = ttk.Checkbutton(self.penalty_row_container, variable=self.var_penalty_enabled, command=self._toggle_penalty_entry)
        self.chk_penalty_enabled.pack(side="left")

        self.ent_penalty.config(state="disabled")


        self.optimization_btn_frame = ttk.Frame(self.settings_container)
        self.optimization_btn_frame.pack(side="right")

        self.btn_run_optimization = ttk.Button(self.optimization_btn_frame, text="Run Optimization", command=self.run_optimization)
        self.btn_run_optimization.pack(side="right", padx=(0, 5))
        
        self.btn_draft = ttk.Button(self.optimization_btn_frame, text="Save Draft", command=self.save_optimization)
        self.btn_draft.pack(side="right", padx=(0, 5))

        self.btn_add_vehicle = ttk.Button(self.optimization_btn_frame, text="Add Vehicle", command=self.add_vehicle)
        self.btn_add_vehicle.pack(side="right", padx=(0, 5))


    def _toggle_penalty_entry(self):
        if self.var_penalty_enabled.get():
            self.ent_penalty.config(state="normal")
        else:
            self.ent_penalty.config(state="normal")
            self.ent_penalty.delete(0, tk.END)
            self.ent_penalty.config(state="disabled")


    def save_optimization(self):
        opt_name = self.ent_optimization_name.get().strip()
        if not opt_name:
            messagebox.showwarning(
                "Missing Name",
                "Please enter an Optimization Name before saving a draft."
            )
            return

        def _entry_val(widget):
            try:
                return widget.get()
            except Exception:
                return ""

        # General
        general_data = {
            "optimization_name": _entry_val(self.ent_optimization_name),
            "start_date":        self.cal.get_date().strftime("%Y-%m-%d"),
        }

        # Locations & Stops
        locations_data = {
            "start_location":                   _entry_val(self.ent_start_location),
            "start_weight_kg":                  _entry_val(self.ent_start_location_weight),
            "start_volume_m3":                  _entry_val(self.ent_start_location_volume),
            "start_time_window_start":          _entry_val(self.ent_start_location_time_window_start),
            "start_time_window_end":            _entry_val(self.ent_start_location_time_window_end),
            "start_load_time_min":              _entry_val(self.ent_start_location_load_time),
            "stop_weight_kg":                   _entry_val(self.ent_stop_weight),
            "stop_volume_m3":                   _entry_val(self.ent_stop_volume),
            "stop_time_window_start":           _entry_val(self.ent_time_window_start),
            "stop_time_window_end":             _entry_val(self.ent_time_window_end),
            "stop_load_time_min":               _entry_val(self.ent_stops_location_load_time),
            "stop_unload_time_min":             _entry_val(self.ent_stops_location_unload_time),
            "stop_type":                        self.cmb_stop_type.get(),
            "stops":                            list(self.stops_items),
        }

        # Vehicles
        vehicles_data = {
            "vehicle_id":        _entry_val(self.ent_vehicle_id),
            "profile":           self.cmb_profile.get(),
            "max_weight_kg":     _entry_val(self.ent_max_weight),
            "max_volume_m3":     _entry_val(self.ent_max_volume),
            "depot_capacity":    _entry_val(self.ent_depot_capacity),
            "fixed_cost":        _entry_val(self.ent_fixed_cost),
            "variable_cost":     _entry_val(self.ent_variable_cost),
            "skills":            list(self.current_skills),
            "stored_vehicles_inputs": {
                k: list(v) for k, v in self.stored_vehicles_inputs.items()
            },
            "stored_stops": {
                k: list(v) for k, v in self.stored_stops.items()
            },
            "num_stored_vehicles": self.num_stored_vehicles,
        }

        # Pickup & Delivery pairs
        pd_data = {
            "pickup_delivery_pairs": list(self.pickup_delivery_pairs),
        }

        # Optimization settings
        settings_data = {
            "max_travel_time_min":       _entry_val(self.ent_max_travel),
            "break_wait_allowance_min":  _entry_val(self.ent_break_wait),
            "late_arrival_penalty":      _entry_val(self.ent_penalty),
            "max_travel_distance_km":   _entry_val(self.ent_max_travel_distance_global),
            "allow_penalty":             self.var_penalty_enabled.get(),
        }

        from datetime import datetime
        payload = {
            "meta": {
                "schema_version":  1,
                "saved_at":        datetime.now().isoformat(timespec="seconds"),
                "status":          "draft",
            },
            "general":   general_data,
            "locations": locations_data,
            "vehicles":  vehicles_data,
            "pickup_delivery": pd_data,
            "optimization_settings": settings_data,
        }

        drafts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drafts")
        os.makedirs(drafts_dir, exist_ok=True)

        safe_name = re.sub(r'[^\w\-_. ]', '_', opt_name).replace(' ', '_')
        filename  = f"{safe_name}.json"
        filepath  = os.path.join(drafts_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)

            messagebox.showinfo(
                "Draft Saved",
                f"'{opt_name}' has been saved as a draft.\n\nFile: {filepath}"
            )
        except OSError as exc:
            messagebox.showerror(
                "Save Failed",
                f"Could not write draft to disk:\n{exc}"
            )
    def _get_required_fields(self):
        fields = [
            # General
            ("Optimization Name",                   self.ent_optimization_name),
            # Locations & Stops
            ("Start Location",                      self.ent_start_location),
            ("Start Weight (kg)",                    self.ent_start_location_weight),
            ("Start Volume (m³)",                    self.ent_start_location_volume),
            # Vehicles
            ("Vehicle ID / Name",                    self.ent_vehicle_id),
            ("Max Weight (kg)",                      self.ent_max_weight),
            ("Max Volume (m³)",                      self.ent_max_volume),
            ("Depot Capacity",                       self.ent_depot_capacity),
            ("Fixed Cost ($/day)",                   self.ent_fixed_cost),
            ("Variable Cost ($/km)",                 self.ent_variable_cost),
            # Optimization Settings
            ("Max Travel Time per Vehicle (min)",    self.ent_max_travel),
            ("Break / Wait Allowance (min)",         self.ent_break_wait),
            ("Max Travel Distance per Vehicle (km)", self.ent_max_travel_distance_global),
        ]

        if self.var_penalty_enabled.get():
            fields.append(("Late Arrival Penalty Weight", self.ent_penalty))

        return fields
    
    
    def _validate_required_fields(self):
        blank_fields = []
        for label, widget in self._get_required_fields():
            value = widget.get().strip()
            if not value:
                blank_fields.append(label)
        return blank_fields
    

    def add_vehicle(self):
        self.stored_vehicle_attr = []
        self.stored_indv_vehicles_inputs = []
        
        self.num_stored_vehicles += 1
        blank_fields = self._validate_required_fields()

        if blank_fields:
            field_list = "\n".join(f"  •  {name}" for name in blank_fields)
            messagebox.showwarning(
                "Incomplete Inputs",
                f"The following fields are still blank:\n\n"
                f"{field_list}\n\n"
                f"Please fill in all required inputs before adding a vehicle."
            )
            return
        
        my_frames = [self.inner_frame, self.general_inner, self.vehicles_inner, self.locations_inner, self.settings_inner]

        for frame in my_frames:
            for child in frame.winfo_children():
                if isinstance(child, ttk.Entry):
                    self.stored_vehicle_attr.append(child)

        for i in self.stored_vehicle_attr:
            get_widget = i.get()
            self.stored_indv_vehicles_inputs.append(get_widget)

        self.stored_indv_vehicles_inputs_stops = list(self.stops_items)

        if self.num_stored_vehicles == 1:
            self.stored_vehicles_inputs = {f"Vehicle {self.num_stored_vehicles}": self.stored_indv_vehicles_inputs}
            self.stored_stops = {f"Vehicle {self.num_stored_vehicles}": self.stored_indv_vehicles_inputs_stops}
           
        elif self.num_stored_vehicles > 1:
            self.stored_vehicles_inputs.update({f"Vehicle {self.num_stored_vehicles}": self.stored_indv_vehicles_inputs})
            self.stored_stops.update({f"Vehicle {self.num_stored_vehicles}": self.stored_indv_vehicles_inputs_stops})
        
        for frame in my_frames:
            for child in frame.winfo_children():
                if isinstance(child, (ttk.Entry, tk.Listbox)):
                    was_disabled = str(child.cget("state")) == "disabled" if isinstance(child, ttk.Entry) else False
                    if was_disabled:
                        child.config(state="normal")
                    child.delete(0, tk.END)
                    if was_disabled:
                        child.config(state="disabled")

        self.stops_items.clear()
        self.map_widget.delete_all_marker()


    def restore_draft(self, data: dict):
        general   = data.get("general",   {})
        locations = data.get("locations", {})
        vehicles  = data.get("vehicles",  {})
        pd        = data.get("pickup_delivery", {})
        settings  = data.get("optimization_settings", {})

        # ── Helper: safely set an Entry widget ────────────────────────────
        def _set(widget, value):
            widget.delete(0, tk.END)
            if value:
                widget.insert(0, str(value))

        # ── General ───────────────────────────────────────────────────────
        _set(self.ent_optimization_name, general.get("optimization_name", ""))
        try:
            self.cal.set_date(general.get("start_date", ""))
        except Exception:
            pass

        # ── Locations ─────────────────────────────────────────────────────
        _set(self.ent_start_location,               locations.get("start_location", ""))
        _set(self.ent_start_location_weight,         locations.get("start_weight_kg", ""))
        _set(self.ent_start_location_volume,         locations.get("start_volume_m3", ""))
        _set(self.ent_start_location_time_window_start, locations.get("start_time_window_start", ""))
        _set(self.ent_start_location_time_window_end,   locations.get("start_time_window_end", ""))
        _set(self.ent_start_location_load_time,      locations.get("start_load_time_min", ""))
        _set(self.ent_stop_weight,                   locations.get("stop_weight_kg", ""))
        _set(self.ent_stop_volume,                   locations.get("stop_volume_m3", ""))
        _set(self.ent_time_window_start,             locations.get("stop_time_window_start", ""))
        _set(self.ent_time_window_end,               locations.get("stop_time_window_end", ""))
        _set(self.ent_stops_location_load_time,      locations.get("stop_load_time_min", ""))
        _set(self.ent_stops_location_unload_time,    locations.get("stop_unload_time_min", ""))
        self.cmb_stop_type.set(locations.get("stop_type", ""))

        # Restore the stops list
        self.stops_items = locations.get("stops", [])
        self.lst_stops.delete(0, tk.END)
        for item in self.stops_items:
            self.lst_stops.insert(
                tk.END,
                f"{item['address']} | {item['weight']}kg | {item['volume']}m³ | "
                f"{item['time_window_start']}-{item['time_window_end']} | "
                f"{item['load_times']} | {item['unload_times']} | {item['stop_type']}"
            )
        self.refresh_pd_dropdowns()

        # ── Vehicles ──────────────────────────────────────────────────────
        _set(self.ent_vehicle_id,      vehicles.get("vehicle_id", ""))
        self.cmb_profile.set(          vehicles.get("profile", ""))
        _set(self.ent_max_weight,      vehicles.get("max_weight_kg", ""))
        _set(self.ent_max_volume,      vehicles.get("max_volume_m3", ""))
        _set(self.ent_depot_capacity,  vehicles.get("depot_capacity", ""))
        _set(self.ent_variable_cost,   vehicles.get("variable_cost", ""))

        for widget in self.skills_display_frame.winfo_children():
            if widget != self.btn_add_skills:
                widget.destroy()
        self.current_skills = []
        for skill in vehicles.get("skills", []):
            self.add_skill(skill)

        self.stored_vehicles_inputs = {
            k: list(v) for k, v in vehicles.get("stored_vehicles_inputs", {}).items()
        }
        self.stored_stops = {
            k: list(v) for k, v in vehicles.get("stored_stops", {}).items()
        }
        self.num_stored_vehicles = vehicles.get("num_stored_vehicles", 0)

        self.pickup_delivery_pairs = pd.get("pickup_delivery_pairs", [])
        self.lst_pd_pairs.delete(0, tk.END)
        for i, pair in enumerate(self.pickup_delivery_pairs, start=1):
            self.lst_pd_pairs.insert(
                tk.END, f"Pair {i}:  ↑ {pair['pickup']}  →  ↓ {pair['delivery']}"
            )

        _set(self.ent_max_travel,      settings.get("max_travel_time_min", ""))
        _set(self.ent_break_wait,      settings.get("break_wait_allowance_min", ""))
        _set(self.ent_penalty,         settings.get("late_arrival_penalty", ""))
        _set(self.ent_max_travel_distance_global, settings.get("max_travel_distance_km", ""))

        self.var_penalty_enabled.set(settings.get("allow_penalty", False))
        self.ent_penalty.config(state="normal")
        _set(self.ent_penalty,         settings.get("late_arrival_penalty", ""))
        self._toggle_penalty_entry()

    def run_optimization(self):
        if self.num_stored_vehicles < 1 or not self.stored_vehicles_inputs:
            self.num_stored_vehicles = 0
            self.stored_vehicles_inputs = {}
            messagebox.showwarning(
                "No Vehicles Added",
                "You must add at least one vehicle before running "
                "the optimization.\n\n"
                "Please fill in all required fields and click "
                "'Add Vehicle' first."
            )
            return

        routing = New_Vehicle_Routing(self.stored_vehicles_inputs, self.num_stored_vehicles, self.stored_stops, self.pickup_delivery_pairs, self.var_penalty_enabled, self.controller)
        routing.create_coordinates()


    def reset_inputs(self):
        self.stored_stops = {}
        self.stops_items = []
        self.pickup_delivery_pairs = []
        self.stored_vehicles_inputs = {}
        self.num_stored_vehicles = 0

        my_frames = [self.inner_frame, self.general_inner, self.vehicles_inner, self.locations_inner, self.settings_inner]

        for frame in my_frames:
            for child in frame.winfo_children():
                if isinstance(child, (ttk.Entry, tk.Listbox)):
                    was_disabled = str(child.cget("state")) == "disabled" if isinstance(child, ttk.Entry) else False
                    if was_disabled:
                        child.config(state="normal")
                    child.delete(0, tk.END)
                    if was_disabled:
                        child.config(state="disabled")

        if hasattr(self, 'lst_stops'):
            self.lst_stops.delete(0, tk.END)

        if hasattr(self, 'lst_pd_pairs'):
            self.lst_pd_pairs.delete(0, tk.END)

        if hasattr(self, 'current_skills'):
            self.current_skills = []

        if hasattr(self, 'skills_display_frame'):
            for widget in self.skills_display_frame.winfo_children():
                if widget != self.btn_add_skills:
                    widget.destroy()

        if hasattr(self, 'map_widget'):
            self.map_widget.delete_all_marker()

        if hasattr(self, 'var_penalty_enabled'):
            self.var_penalty_enabled.set(False)
            self._toggle_penalty_entry()
        
class New_Vehicle_Routing:
    def __init__(self, stored_vehicles_inputs, num_stored_vehicles, stored_stops, pickup_delivery_pairs, var_penalty_enabled, controller):
        
        self.stored_vehicles_inputs = stored_vehicles_inputs
        self.num_stored_vehicles = num_stored_vehicles
        self.stored_stops = stored_stops
        self.pickup_delivery_pairs = pickup_delivery_pairs
        self.var_penalty_enabled = var_penalty_enabled
        self.controller = controller

        self.location_coors = []
        self.pair_positions_location_coors_pickup = []
        self.pair_positions_location_coors_delivery = []


    def create_coordinates(self):
        vehicle_key_to_idx = {}

        self.addresses = []

        for idx, (key, value) in enumerate(self.stored_vehicles_inputs.items()):

            address_item = value[9]
            self.addresses.append([address_item])

            location = geolocator.geocode(value[9], timeout=10)
            if location:
                lat, lon = location.latitude, location.longitude
                self.location_coors.append([(lat, lon)])
                vehicle_key_to_idx[key] = idx
            else:
                print(f"No Start Location for {key}: {value}")

        for key, stops in self.stored_stops.items():
            if key in vehicle_key_to_idx:
                vehicle_idx = vehicle_key_to_idx[key]
                
                for stop in stops:
                    stop_address_items = stop["address"]
                    self.addresses[vehicle_idx].append(stop_address_items)
                    location = geolocator.geocode(stop["address"], timeout=10)
                    if location:
                        self.location_coors[vehicle_idx].append((location.latitude, location.longitude))

                    else:
                        print(f"Failed to geocode stop: {stop['address']}")
            else:
                print(f"No vehicle found for stops key: {key}")

        for pair in self.pickup_delivery_pairs:
            delivery = geolocator.geocode(pair['delivery'], timeout=10)
            pickup = geolocator.geocode(pair['pickup'], timeout=10)

            if delivery:
                self.pair_positions_location_coors_delivery.append((delivery.latitude, delivery.longitude))

            if pickup:
                self.pair_positions_location_coors_pickup.append((pickup.latitude, pickup.longitude))

        self.solve_vrp()


    def create_demands(self):

        start_locations_weight = []
        start_locations_volume = []

        stops_locations_weight = []
        stops_locations_volume = []

        max_weight = []
        max_volume = []

        depot_capacity = []

        for key, value in self.stored_vehicles_inputs.items():
            start_locations_weight.append(int(round(float(value[12]))))
            start_locations_volume.append(int(round(float(value[13]))))
            max_weight.append(int(round(float(value[4]))))
            max_volume.append(int(round(float(value[5]))))
            depot_capacity.append(int(value[6]))
        
        for key, stops in self.stored_stops.items():
            for stop in stops:
                stops_locations_weight.append(int(round(float(stop["weight"]))))
                stops_locations_volume.append(int(round(float(stop["volume"]))))
        
        return start_locations_weight, start_locations_volume, stops_locations_weight, stops_locations_volume, max_weight, max_volume, depot_capacity
    
    @staticmethod
    def string_to_minutes(time_str):
        h, m = map(int, time_str.split(':'))
        return (h * 60) + m
    
    def create_times(self):
        time_windows = []

        start_load_times = []

        stop_load_times = []
        stop_unload_times = []

        for key, value in self.stored_vehicles_inputs.items():
            start = self.string_to_minutes(value[16])  
            end   = self.string_to_minutes(value[17]) 
            time_windows.append((start, end))

            start_load = int(value[18])
            start_load_times.append(start_load)
           
            if key in self.stored_stops:
                for stop in self.stored_stops[key]:
                    min_time = self.string_to_minutes(stop["time_window_start"])
                    max_time = self.string_to_minutes(stop["time_window_end"])
                    stop_load = int(stop["load_times"])
                    stop_unload = int(stop["unload_times"])
                    time_windows.append((min_time, max_time))
                    stop_load_times.append(stop_load)
                    stop_unload_times.append(stop_unload)

        return time_windows, start_load_times, stop_load_times, stop_unload_times
    

    def OSRM_Matrix(self):
        str_coors = []

        for coor in self.location_coors:
            for i in coor:
                reversed_coords = tuple(reversed(i))
                str_coor = str(reversed_coords).strip("()").replace(" ", "")
                str_coors.append(str_coor)

        coors = ";".join(i for i in str_coors)

        url = f"http://router.project-osrm.org/table/v1/driving/{coors}?annotations=distance,duration"
        
        headers = {

            'User-Agent': 'RouteForge Analytics Project (pogehab359@mugstock.com)'
        }

        r = requests.get(url, headers=headers, timeout=10).json()

        if r['code'] != 'Ok':
            print(f"REQUEST FAILED: {r['code']}")
            return None

        else:
            print("Success")

        distance_matrix = [[round(cell) for cell in row] for row in r['distances']]
        duration_matrix = [[round(cell / 60) for cell in row] for row in r['durations']]
        
        return distance_matrix, duration_matrix
    

    def find_truck_restrictions(self):
        fixed_cost = []
        var_cost = []

        for key, value in self.stored_vehicles_inputs.items():
            f_c = int(round(float(value[7])))
            v_c = int(round(float(value[8])))

            fixed_cost.append(f_c)
            var_cost.append(v_c)

        return fixed_cost, var_cost
    

    def create_optimization_settings(self):
        first_value = next(iter(self.stored_vehicles_inputs.values()))

        max_travel_time = int(first_value[23])
        break_allowance = int(first_value[24])
        #penalty_weight = int(first_value[25])
        penalty_raw = first_value[25]
        penalty_weight = int(penalty_raw) if penalty_raw not in ('', None) else 0   

        max_travel_distance = int(first_value[26])

        return max_travel_time, break_allowance, penalty_weight, max_travel_distance


    def create_data_model(self):
        data = {}

        distance_matrix_result = self.OSRM_Matrix()
        demand_results = self.create_demands()
        time_results = self.create_times()
        restriction_results = self.find_truck_restrictions()
        settings_results = self.create_optimization_settings()
        
        if distance_matrix_result is None:
            print("Failed to build distance matrix from OSRM.")
            return None

        distance_matrix, duration_matrix = distance_matrix_result

        start_location_weight, start_location_volume, stops_locations_weight, stops_locations_volume, max_weight, max_volume, depot_capacity = demand_results

        time_windows, start_load_times, stop_load_times, stop_unload_times = time_results

        fixed_cost, var_cost = restriction_results

        max_travel_time, break_allowance, penalty_weight, max_travel_distance = settings_results

        total_nodes = len(distance_matrix)
        num_vehicles = self.num_stored_vehicles

        node_weight = [0] * total_nodes
        node_volume = [0] * total_nodes

        for i in range(num_vehicles):
            node_weight[i] = start_location_weight[i]
            node_volume[i] = start_location_volume[i]

        for j, (w, v) in enumerate(
            zip(stops_locations_weight, stops_locations_volume)
        ):
            node_weight[num_vehicles + j] = w
            node_volume[num_vehicles + j] = v

        start = list(range(num_vehicles))
        end   = list(range(num_vehicles))

        pickups_and_deliveries = []

        flat_location_coors = [coord for vehicle in self.location_coors for coord in vehicle]

        pickup_matches = [flat_location_coors.index(item) for item in self.pair_positions_location_coors_pickup if item in flat_location_coors]
        delivery_matches = [flat_location_coors.index(item) for item in self.pair_positions_location_coors_delivery if item in flat_location_coors]

        for i, j in zip(pickup_matches, delivery_matches):
            pickups_and_deliveries.append([i, j])
        
        data["distance_matrix"]  = distance_matrix
        data["duration_matrix"]  = duration_matrix
        data["num_vehicles"]     = num_vehicles
        data["start"]            = start
        data["end"]              = end
        data["node_weight"]      = node_weight   
        data["node_volume"]      = node_volume   
        data["max_weight"]       = max_weight
        data["max_volume"]       = max_volume
        data["depot_capacity"]   = depot_capacity
        data["time_windows"]     = time_windows
        data["start_load_times"] = start_load_times
        data["stop_load_times"] = stop_load_times
        data["stop_unload_times"] = stop_unload_times
        data["pickups_and_deliveries"] = pickups_and_deliveries
        data["fixed_cost"] = fixed_cost
        data["var_cost"] = var_cost
        data["max_travel_time"] = max_travel_time
        data["break_allowance"] = break_allowance
        data["penalty_weight"] = penalty_weight
        data["max_travel_distance"] = max_travel_distance

        self.distance_matrix = distance_matrix
        self.duration_matrix = duration_matrix
        self.num_vehicles = num_vehicles
        self.start = start 
        self.end = end
        self.node_weight = node_weight
        self.node_volume = node_volume
        self.max_weight = max_weight
        self.max_volume = max_volume
        self.depot_capacity = depot_capacity
        self.time_windows = time_windows
        self.start_load_times = start_load_times
        self.stop_load_times = stop_load_times
        self.stop_unload_times = stop_unload_times
        self.pickups_and_deliveries = pickups_and_deliveries
        self.fixed_cost = fixed_cost
        self.var_cost = var_cost
        self.max_travel_time = max_travel_time
        self.break_allowance = break_allowance
        self.penalty_weight = penalty_weight
        self.max_travel_distance = max_travel_distance

        return data

    def print_solution(self, data, manager, routing, solution):
        print(f"Objective: {solution.ObjectiveValue()}")

        # Display dropped nodes.
        dropped_nodes = "Dropped nodes:"
        for node in range(routing.Size()):
            if routing.IsStart(node) or routing.IsEnd(node):
                continue
            if solution.Value(routing.NextVar(node)) == node:
                dropped_nodes += f" {manager.IndexToNode(node)}"
        print(dropped_nodes)


        stringed_dropped_nodes = re.findall(r'\d+', dropped_nodes)
        self.dropped_nodes = [int(x) for x in stringed_dropped_nodes]

        total_distance     = 0
        total_weight       = 0
        total_volume       = 0

        self.per_vehicle_weight = []   
        self.per_vehicle_volume = []
        self.per_vehicle_distance = []
        self.nodes_order = []
        self.weight_load_order = []
        self.volume_load_order = []   

        for vehicle_id in range(data["num_vehicles"]):
            if not routing.IsVehicleUsed(solution, vehicle_id):
                continue

            index = routing.Start(vehicle_id)
            plan_output    = f"Route for vehicle {vehicle_id + 1}:\n"
            route_distance = 0
            route_weight   = 0
            route_volume   = 0
            route_nodes_order = []
            route_weight_load_order = []
            route_volume_load_order = []

            while not routing.IsEnd(index):
                node_index    = manager.IndexToNode(index)
                route_weight += data["node_weight"][node_index]
                route_volume += data["node_volume"][node_index]
                plan_output  += (
                    f"  Node {node_index} "
                    f"(Cumulative Weight: {route_weight}kg, "
                    f"Cumulative Volume: {route_volume / 100:.2f}m³) ->\n"
                )
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id
                )
                
                route_nodes_order.append(node_index)
                route_weight_load_order.append(route_weight)
                route_volume_load_order.append(route_volume)
                
            end_node = manager.IndexToNode(index)
            route_nodes_order.append(end_node)

            plan_output += f"  Node {end_node} (End)\n"
            plan_output += f"Distance of the route: {route_distance}m\n"
            plan_output += f"Total weight: {route_weight}kg\n"
            plan_output += f"Total volume: {route_volume / 100:.2f}m³\n"

            print(plan_output)

            self.nodes_order.append(route_nodes_order)

            self.weight_load_order.append(route_weight_load_order)
            self.volume_load_order.append(route_volume_load_order)

            self.per_vehicle_weight.append(route_weight)
            self.per_vehicle_volume.append(route_volume)
            self.per_vehicle_distance.append(route_distance)

            total_distance     += route_distance
            total_weight       += route_weight
            total_volume       += route_volume

        print(f"Total distance of all routes:   {total_distance}m")
        print(f"Total weight of all routes:     {total_weight}kg")
        print(f"Total volume of all routes:     {total_volume / 100:.2f}m³")

        self.total_distance = total_distance
        self.total_weight = total_weight
        self.total_volume = total_volume

        
    def time_print_solution(self, data, manager, routing, solution):
        print(f"Objective: {solution.ObjectiveValue()}")
        time_dimension = routing.GetDimensionOrDie("Time")
        total_time = 0
        per_vehicle_time = []
        self.time_windows_order = []
        for vehicle_id in range(data["num_vehicles"]):
            if not routing.IsVehicleUsed(solution, vehicle_id):
                continue
            index = routing.Start(vehicle_id)
            plan_output = f"Route for vehicle {vehicle_id + 1}:\n"
            route_time_windows = []
            while not routing.IsEnd(index):
                time_var = time_dimension.CumulVar(index)
                plan_output += (
                    f"{manager.IndexToNode(index)}"
                    f" Time({solution.Min(time_var)},{solution.Max(time_var)})"
                    " -> "
                )
                index = solution.Value(routing.NextVar(index))
            time_var = time_dimension.CumulVar(index)
            min_time = solution.Min(time_var)
            max_time = solution.Max(time_var)
            route_time_windows.append((min_time, max_time))
            plan_output += (
                f"{manager.IndexToNode(index)}"
                f" Time({solution.Min(time_var)},{solution.Max(time_var)})\n"
            )
            plan_output += f"Time of the route: {solution.Min(time_var)}min\n"
            per_vehicle_time.append(solution.Min(time_var))
            print(plan_output)
            total_time += solution.Min(time_var)
            self.time_windows_order.append(route_time_windows)
        print(f"Total time of all routes: {total_time}min")

        self.total_time = total_time
        self.per_vehicle_time = per_vehicle_time
   
    
    def setup_costs(self, routing, manager, data):
    
        num_vehicles = manager.GetNumberOfVehicles()
        
        variable_cost_callbacks = []

        for vehicle_id in range(num_vehicles):
            var_cost_coefficient = data['var_cost'][vehicle_id]
            
            def make_scaled_callback(coefficient):
                def scaled_callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)

                    return int(data['distance_matrix'][from_node][to_node] * coefficient)
                
                return scaled_callback

            vehicle_callback = make_scaled_callback(var_cost_coefficient)
            variable_cost_callbacks.append(vehicle_callback)
            
            transit_cost_index = routing.RegisterTransitCallback(vehicle_callback)
            
            routing.SetArcCostEvaluatorOfVehicle(transit_cost_index, vehicle_id)

            fixed_cost = int(round(float(data['fixed_cost'][vehicle_id])))
            routing.SetFixedCostOfVehicle(fixed_cost, vehicle_id)

        return variable_cost_callbacks

    def solve_vrp(self):
        
        data = self.create_data_model()

        if data is None:
            return
        
        self.data = data

        # Create the routing index manager.
        manager = pywrapcp.RoutingIndexManager(
            len(data["distance_matrix"]),
            data["num_vehicles"],
            data["start"],
            data["end"],
        )

        # Create Routing Model.
        routing = pywrapcp.RoutingModel(manager)

        active_callbacks = self.setup_costs(routing, manager, data)

        def time_callback(from_index, to_index):
            """Returns the travel time between the two nodes."""
            # Convert from routing variable Index to time matrix NodeIndex.
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data["duration_matrix"][from_node][to_node]
        
        transit_time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_time_callback_index)

        # Add Time Windows constraint.
        time = "Time"
        routing.AddDimension(
            transit_time_callback_index,
            data["break_allowance"],  
            data["max_travel_time"],  
            False,  # Don't force start cumul to zero.
            time,
        )

        time_dimension = routing.GetDimensionOrDie(time)
        
        for location_idx, time_window in enumerate(data["time_windows"]):
            if location_idx in data["start"] or location_idx in data["end"]:
                continue
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

        for vehicle_id in range(data["num_vehicles"]):
            start_idx = data["start"][vehicle_id]
            index = routing.Start(vehicle_id)
            time_dimension.CumulVar(index).SetRange(
                data["time_windows"][start_idx][0],
                data["time_windows"][start_idx][1]
            )

        for vehicle_id in range(data["num_vehicles"]):
            end_idx = data["end"][vehicle_id]
            index = routing.End(vehicle_id)
            time_dimension.CumulVar(index).SetRange(
                data["time_windows"][end_idx][0],
                data["time_windows"][end_idx][1]
            )

        solver = routing.solver()
        intervals = []

        for i in range(data["num_vehicles"]):
            intervals.append(
                solver.FixedDurationIntervalVar(
                    time_dimension.CumulVar(routing.Start(i)),
                    data["start_load_times"][i],
                    f"start_load_{i}",
                )
            )

            stops_for_vehicle = self.stored_stops[f"Vehicle {i + 1}"]

            for j, stop in enumerate(stops_for_vehicle):
                node_idx = data["num_vehicles"] + sum(
                    len(self.stored_stops[f"Vehicle {k + 1}"]) for k in range(i)
                ) + j

                routing_index = manager.NodeToIndex(node_idx)

                load_time   = int(stop.get("load_times", 0))
                unload_time = int(stop.get("unload_times", 0))

                if load_time > 0:
                    intervals.append(
                        solver.FixedDurationIntervalVar(
                            time_dimension.CumulVar(routing_index),
                            load_time,
                            f"load_v{i}_s{j}",   
                        )
                    )

                if unload_time > 0:
                    intervals.append(
                        solver.FixedDurationIntervalVar(
                            time_dimension.CumulVar(routing_index),
                            unload_time,
                            f"unload_v{i}_s{j}",  
                        )
                    )

        for i in range(data["num_vehicles"]):
            routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(routing.Start(i))
            )
            routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(i)))

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node   = manager.IndexToNode(to_index)
            return data["distance_matrix"][from_node][to_node]

        transit_distance_callback_index = routing.RegisterTransitCallback(distance_callback)

        routing.SetArcCostEvaluatorOfAllVehicles(transit_distance_callback_index)

        def weight_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return data["node_weight"][from_node]         

        weight_callback_index = routing.RegisterUnaryTransitCallback(weight_callback)
        routing.AddDimensionWithVehicleCapacity(
            weight_callback_index,
            0,                    
            data["max_weight"],   
            False,                 
            "WeightCapacity",
        )

        def volume_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return data["node_volume"][from_node]          

        volume_callback_index = routing.RegisterUnaryTransitCallback(volume_callback)
        routing.AddDimensionWithVehicleCapacity(
            volume_callback_index,
            0,                  
            data["max_volume"],   
            False,                 
            "VolumeCapacity",
        )

        routing.AddDimension(
            transit_distance_callback_index,
            0,          
            data["max_travel_distance"], 
            False,       
            "Distance",
        )
        distance_dimension = routing.GetDimensionOrDie("Distance")
        distance_dimension.SetGlobalSpanCostCoefficient(100)

        for request in data["pickups_and_deliveries"]:
            pickup_index = manager.NodeToIndex(request[0])
            delivery_index = manager.NodeToIndex(request[1])
            routing.AddPickupAndDelivery(pickup_index, delivery_index)
            routing.solver().Add(
                routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index)
            )
            routing.solver().Add(
                distance_dimension.CumulVar(pickup_index)
                <= distance_dimension.CumulVar(delivery_index)
            )
        

        
        # Allow to drop nodes.
        if self.var_penalty_enabled.get():
            penalty = data["penalty_weight"]#10**9
            for node_idx in range(1, len(data["distance_matrix"])):
                if node_idx in data["start"] or node_idx in data["end"]:
                    continue

                routing.AddDisjunction([manager.NodeToIndex(node_idx)], penalty)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.FromSeconds(1)

        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            self.solution = solution
            self.print_solution(data, manager, routing, solution)
            self.time_print_solution(data, manager, routing, solution)
            self.run_results()
        else:
            messagebox.showerror(
                title="No Solution Found",
                message="The solver could not find a feasible solution with the current constraints.\n\n"
                        "Try adjusting your vehicle capacities, time windows, or optimization settings."
            )
            
            new_opt_frame = self.controller.frames["New_Optimizations"]
            new_opt_frame.reset_inputs()

    

    def get_results(self):
        return {
            "data": self.data,
            "solution": self.solution,
            "num_vehicles": self.num_stored_vehicles,
            "stored_stops": self.stored_stops,
            "location_coordinates": self.location_coors,
            "addresses": self.addresses,

            # --- User Inputs ---
            "distance_matrix": self.distance_matrix,
            "duration_matrix": self.duration_matrix,
            "input_num_vehicles": self.num_vehicles,
            "start_nodes": self.start,
            "end_nodes": self.end,
            "node_weight": self.node_weight,
            "node_volume": self.node_volume,
            "input_max_weight": self.max_weight,
            "input_max_volume": self.max_volume,
            "depot_capacity": self.depot_capacity,
            "input_time_windows": self.time_windows,
            "start_load_times": self.start_load_times,
            "stop_load_times": self.stop_load_times,
            "stop_unload_times": self.stop_unload_times,
            "pickups_and_deliveries": self.pickups_and_deliveries,
            
            # Global Totals
            "total_distance": self.total_distance,
            "total_time": self.total_time,
            "total_weight": self.total_weight,
            "total_volume": self.total_volume,
            "dropped_nodes": self.dropped_nodes,
            "max_weight": self.max_weight,
            "max_volume": self.max_volume,

            # --- PASS FINANCIAL METRICS TO THE METRIC CARD ---
            "vehicle_fixed_costs": self.data.get('fixed_cost', [0] * self.num_stored_vehicles),
            "vehicle_variable_costs": self.data.get('var_cost', [0] * self.num_stored_vehicles),
            
            # Per-Vehicle Consolidated Totals
            "per_vehicle_distance": self.per_vehicle_distance,
            "per_vehicle_time": self.per_vehicle_time,
            "per_vehicle_weight": self.per_vehicle_weight,   
            "per_vehicle_volume": self.per_vehicle_volume,
            
            # Stop-by-Stop Ordered Sequences (List of Lists per Route)
            "nodes_order": self.nodes_order,   
            "weight_load_order": self.weight_load_order,
            "volume_load_order": self.volume_load_order,  
            "time_windows_order": self.time_windows_order, 

            "max_travel_time": self.max_travel_time,
            "break_allowance": self.break_allowance,
            "penalty_weight": self.penalty_weight,
            "max_travel_distance": self.max_travel_distance,
        }

    
    def run_results(self):
        results_frame = self.controller.frames["Results"]
        results_frame.refresh(self.get_results())
        self.controller.show_page("Results")


class Results(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        
        self.controller = controller
        self.data = None
        self.results = 0
        self.num_stored_vehicles = 0
        self.stored_stops = 0
        self.location_coors = 0
        self.addresses = []

        # --- Original User Inputs ---
        self.distance_matrix = None
        self.duration_matrix = None
        self.num_vehicles = None
        self.start = []
        self.end = []
        self.node_weight = []
        self.node_volume = []
        self.max_weight = 0
        self.max_volume = 0
        self.depot_capacity = 0
        self.time_windows = []
        self.start_load_times = []
        self.stop_load_times = []
        self.stop_unload_times = []
        self.pickups_and_deliveries = []
        
        # Global Aggregates & Constraints
        self.total_distance = 0
        self.total_time = 0
        self.total_weight = 0
        self.total_volume = 0
        self.max_weight = 0
        self.max_volume = 0
        self.dropped_nodes = [] 
        
        # Per-Vehicle Accumulated Totals
        self.per_vehicle_distance = []   
        self.per_vehicle_time = []       
        self.per_vehicle_weight = []   
        self.per_vehicle_volume = []
        
        # Stop-by-Stop Sequences (Lists of Lists)
        self.nodes_order = []
        self.weight_load_order = []      
        self.volume_load_order = []      
        self.time_windows_order = []

        self.max_travel_time = 0
        self.break_alloance = 0
        self.penalty_weight = 0
        self.max_travel_distance = 0

        # Gemini collected responses
        self.collect_gemini_responses = {}

        self.scroll_canvas = tk.Canvas(self, highlightthickness=0)
        self.scroller = ttk.Scrollbar(self, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=self.scroller.set)
        self.scroller.pack(side="right", fill="y")
        self.scroll_canvas.pack(fill="both", expand=True)

        self.inner_frame = ttk.Frame(self.scroll_canvas)
        self.canvas_window = self.scroll_canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.scroll_canvas.bind("<Configure>", self._on_canvas_configure)

        self.scroll_canvas.bind("<Enter>", self._bind_mousewheel)
        self.scroll_canvas.bind("<Leave>", self._unbind_mousewheel)

        self.inner_frame.columnconfigure(0, weight=1)
        
        title_and_desc_container = ttk.Frame(self.inner_frame)
        title_and_desc_container.pack(fill="x", expand=True)
        title_and_desc_container.columnconfigure(0, weight=1)  
        title_and_desc_container.columnconfigure(1, weight=0)  

        title_and_desc_frame = ttk.Frame(title_and_desc_container)
        title_and_desc_frame.pack(side='left')

        self.lbl_title = ttk.Label(title_and_desc_frame, text="Optimization Results", font=("Helvetica", 40))
        self.lbl_title.grid(row=0, column=0, padx=30, pady=(10, 0), sticky="w")

        ttk.Separator(self.inner_frame, orient="horizontal", bootstyle="secondary").pack(fill="x", padx=20, pady=10)

        self.lbl_title_desc = ttk.Label(title_and_desc_frame, text=f"Run complete", font=("Helvetica", 16))
        self.lbl_title_desc.grid(row=1, column=0, padx=60, pady=(0, 10), sticky="w")

        btn_frame = ttk.Frame(title_and_desc_container)
        btn_frame.pack(side="right", padx=(0, 12))

        self.btn_back = ttk.Button(btn_frame, text="← Back", command=lambda: controller.show_page("New_Optimizations"))
        self.btn_back.pack(side="left", padx=5)

        self.btn_export = ttk.Button(btn_frame, text="Export .txt", command=lambda: self.export_txt())
        self.btn_export.pack(side="right")

        self.cards_frame = ttk.Frame(self.inner_frame)
        self.cards_frame.pack(fill="x", expand=True)

    def refresh(self, results: dict):
        self.results = results
        self.data = results["data"]
        self.num_stored_vehicles = results["num_vehicles"]
        self.stored_stops = results["stored_stops"]
        self.location_coors = results["location_coordinates"]
        self.addresses = results["addresses"]

        # --- Map User Inputs ---
        self.distance_matrix = results["distance_matrix"]
        self.duration_matrix = results["duration_matrix"]
        self.num_vehicles = results["input_num_vehicles"]
        self.start = results["start_nodes"]
        self.end = results["end_nodes"]
        self.node_weight = results["node_weight"]
        self.node_volume = results["node_volume"]
        self.max_weight = results["input_max_weight"]
        self.max_volume = results["input_max_volume"]
        self.depot_capacity = results["depot_capacity"]
        self.time_windows = results["input_time_windows"]
        self.start_load_times = results["start_load_times"]
        self.stop_load_times = results["stop_load_times"]
        self.stop_unload_times = results["stop_unload_times"]
        self.pickups_and_deliveries = results["pickups_and_deliveries"]
        
        # Global Aggregates & Constraints
        self.total_distance = results["total_distance"]
        self.total_time = results["total_time"]
        self.total_weight = results["total_weight"]
        self.total_volume = results["total_volume"]
        self.dropped_nodes = results["dropped_nodes"]
        self.max_weight = results["max_weight"]
        self.max_volume = results["max_volume"]
        
        # Per-Vehicle Consolidated Totals
        self.per_vehicle_distance = results["per_vehicle_distance"]  
        self.per_vehicle_time = results["per_vehicle_time"]          
        self.per_vehicle_weight = results["per_vehicle_weight"]
        self.per_vehicle_volume = results["per_vehicle_volume"]

        self.vehicle_fixed_costs = results.get("vehicle_fixed_costs", [])
        self.vehicle_variable_costs = results.get("vehicle_variable_costs", [])
        
        # Stop-by-Stop Ordered Sequences
        self.nodes_order = results["nodes_order"]
        self.weight_load_order = results["weight_load_order"]        
        self.volume_load_order = results["volume_load_order"]        
        self.time_windows_order = results["time_windows_order"]

        self.max_travel_time = results["max_travel_time"]
        self.break_allowance = results["break_allowance"]
        self.penalty_weight = results["penalty_weight"]
        self.max_travel_distance = results["max_travel_distance"]

        self.num_nodes_dropped = 0

        self.collect_gemini_responses = {}
        
        self.lbl_title_desc.config(text=f"Run complete · {self.create_today_date()} · {self.num_stored_vehicles} vehicles")

        self.cards_frame.destroy()
        self.cards_frame = ttk.Frame(self.inner_frame)
        self.cards_frame.pack(fill="x", expand=True)

        self.create_cards()

        
    def _bind_mousewheel(self, event):
        self.scroll_canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.scroll_canvas.bind_all("<Up>", self._on_key_scroll)
        self.scroll_canvas.bind_all("<Down>", self._on_key_scroll)


    def _unbind_mousewheel(self, event):
        self.scroll_canvas.unbind_all("<MouseWheel>")
        self.scroll_canvas.unbind_all("<Up>")
        self.scroll_canvas.unbind_all("<Down>")    
       

    def _on_key_scroll(self, event):
        focused = self.focus_get()
        if isinstance(focused, (ttk.Entry, tk.Listbox, ttk.Combobox)):
            return
        if event.keysym == "Up":
            self.scroll_canvas.yview_scroll(-1, "units")
        elif event.keysym == "Down":
            self.scroll_canvas.yview_scroll(1, "units")

    def _on_frame_configure(self, event):
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.scroll_canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mouse_wheel(self, event):
        self.scroll_canvas.yview_scroll(-1 * int(event.delta / 120), "units")

    @staticmethod
    def create_today_date():
        today_date = date.today()
        formatted_date = today_date.strftime("%a %Y-%m-%d")
        return formatted_date

    def create_cards(self):
        self.summary_row_headings()
        self.arrange_summary_cards()
        self.arrange_rs_and_cu_cards()
        self.dropped_stops_card()
        self.suggestions_card()
        self.health_score_card()


    def summary_row_headings(self):
        self.summary_container = ttk.Frame(self.cards_frame)
        self.summary_container.pack(fill='x', expand=True)

        self.summary_inner = ttk.Frame(self.summary_container, relief="groove", borderwidth=2)
        self.summary_inner.pack(fill='x')

        self.summary_inner.columnconfigure(0, weight=0)
        self.summary_inner.columnconfigure(1, weight=0)
        self.summary_inner.columnconfigure(2, weight=0)

        self.lbl_summary = ttk.Label(self.summary_inner, text="Summary", font=("Helvetica", 18))
        self.lbl_summary.grid(row=0, column=0, padx=(30, 0), pady=8, sticky='w')

        ttk.Separator(self.cards_frame, orient="horizontal", bootstyle="secondary").pack(fill="x", padx=20, pady=10)


    def arrange_summary_cards(self):
        self.arrange_summary_cards_container = ttk.Frame(self.cards_frame)
        self.arrange_summary_cards_container.pack(expand=True, fill='x')

        ttk.Separator(self.cards_frame, orient="horizontal", bootstyle="secondary").pack(fill="x", padx=20, pady=10)

        self.card_1 = self.total_distance_card(self.arrange_summary_cards_container)
        self.card_1.grid(row=0, column=0, padx=6, pady=6, sticky='nsew')

        self.card_2 = self.total_time_card(self.arrange_summary_cards_container)
        self.card_2.grid(row=0, column=1, padx=6, pady=6, sticky='nsew')

        self.card_3 = self.stops_served_card(self.arrange_summary_cards_container)
        self.card_3.grid(row=0, column=2, padx=6, pady=6, sticky='nsew')

        self.card_4 = self.est_cost_card(self.arrange_summary_cards_container)
        self.card_4.grid(row=0, column=3, padx=6, pady=6, sticky='nsew')
        
        for i in range(4):
            self.arrange_summary_cards_container.columnconfigure(i, weight=1)


    def calculate_entered_order_baseline(self):
       
        baseline_distance = 0
        baseline_time = 0
        
        for vehicle_idx in range(self.num_stored_vehicles):
            vehicle_key = f"Vehicle {vehicle_idx + 1}"
            
            if vehicle_key not in self.stored_stops:
                continue
                
            original_sequence = [vehicle_idx]
            
            num_stops = len(self.stored_stops[vehicle_key])

            for stop_offset in range(num_stops):
                stop_node_id = self.num_stored_vehicles + sum(
                    len(self.stored_stops[f"Vehicle {v + 1}"]) 
                    for v in range(vehicle_idx)
                ) + stop_offset
                original_sequence.append(stop_node_id)
            
            original_sequence.append(vehicle_idx)
            
            for i in range(len(original_sequence) - 1):
                from_node = original_sequence[i]
                to_node = original_sequence[i + 1]
                
                baseline_distance += self.distance_matrix[from_node][to_node]
                baseline_time += self.duration_matrix[from_node][to_node]
        
        return baseline_distance, baseline_time
    

    def total_distance_card(self, parent):

        frame = ttk.Frame(parent, relief="groove", borderwidth=2)

        km = round(self.total_distance / 1000)

        baseline_distance, _ = self.calculate_entered_order_baseline()
        baseline_km = round(baseline_distance / 1000)
        
        if baseline_km > 0:
            change = ((baseline_km - km) / baseline_km) * 100
            if change >= 0:
                improvement_text = f"↓ {round(abs(change))}% vs entered order"
                improvement_color = "green"
            else:
                improvement_text = f"↑ {round(abs(change))}% vs entered order"
                improvement_color = "red"
        else:
            improvement_text = "N/A"
            improvement_color = "gray"

        ttk.Label(frame, text="Total distance", font=("Helvetica", 9)).grid(
            row=0, column=0, padx=12, pady=(10, 2), sticky='nw'
        )
        ttk.Label(frame, text=f"{km} km", font=("Helvetica", 16, "bold")).grid(
            row=1, column=0, padx=12, pady=2, sticky='nw'
        )
        ttk.Label(frame, text=improvement_text, font=("Helvetica", 8), 
                foreground=improvement_color).grid(
            row=2, column=0, padx=12, pady=(2, 10), sticky='nw'
        )

        return frame
    
   
    def total_time_card(self, parent):
        frame = ttk.Frame(parent, relief="groove", borderwidth=2)

        hours = self.total_time // 60
        minutes = self.total_time % 60

        _, baseline_time = self.calculate_entered_order_baseline()
        
        if baseline_time > 0:
            change = ((baseline_time - self.total_time) / baseline_time) * 100
            if change >= 0:
                improvement_text = f"↓ {round(abs(change))}% vs entered order"
                improvement_color = "green"
            else:
                improvement_text = f"↑ {round(abs(change))}% vs entered order"
                improvement_color = "red"
        else:
            improvement_text = "N/A"
            improvement_color = "gray"

        ttk.Label(frame, text="Total time", font=("Helvetica", 9)).grid(
            row=0, column=0, padx=12, pady=(10, 2), sticky='nw'
        )
        ttk.Label(frame, text=f"{hours}h {minutes}m", font=("Helvetica", 16, "bold")).grid(
            row=1, column=0, padx=12, pady=2, sticky='nw'
        )
        ttk.Label(frame, text=improvement_text, font=("Helvetica", 8), 
                foreground=improvement_color).grid(
            row=2, column=0, padx=12, pady=(2, 10), sticky='nw'
        )

        return frame
    

    def stops_served_card(self, parent):
        frame = ttk.Frame(parent, relief="groove", borderwidth=2)

        total_stops = sum(len(stops) for stops in self.stored_stops.values())
        
        self.num_nodes_dropped = len(self.dropped_nodes)

        ttk.Label(frame, text="Stops served", font=("Helvetica", 9)).grid(
            row=0, column=0, padx=12, pady=(10, 2), sticky='nw'
        )
        ttk.Label(frame, text=f"{total_stops - self.num_nodes_dropped} / {total_stops}", 
                font=("Helvetica", 16, "bold")).grid(
            row=1, column=0, padx=12, pady=2, sticky='nw'
        )

        if self.num_nodes_dropped != 0:
            ttk.Label(frame, text=f"{self.num_nodes_dropped} dropped — see below", 
                    font=("Helvetica", 8), foreground="red").grid(
                row=2, column=0, padx=12, pady=(2, 10), sticky='nw'
            )

        elif self.num_nodes_dropped == 0:
            ttk.Label(frame, text=f"No nodes dropped", 
                    font=("Helvetica", 8), foreground="green").grid(
                row=2, column=0, padx=12, pady=(2, 10), sticky='nw'
            )

        return frame
    

    def calculate_actual_routing_costs(self):
        
        total_calculated_cost = 0.0
        
        for vehicle_id, distance_meters in enumerate(self.per_vehicle_distance):
            if distance_meters > 0: # Vehicle
                distance_km = distance_meters / 1000.0
                
                raw_fixed = self.vehicle_fixed_costs[vehicle_id] if vehicle_id < len(self.vehicle_fixed_costs) else 0
                raw_variable = self.vehicle_variable_costs[vehicle_id] if vehicle_id < len(self.vehicle_variable_costs) else 0
                
                try:
                    fixed_rate = float(raw_fixed) if raw_fixed else 0.0
                except (ValueError, TypeError):
                    fixed_rate = 0.0
                    
                try:
                    variable_rate = float(raw_variable) if raw_variable else 0.0
                except (ValueError, TypeError):
                    variable_rate = 0.0
                
                vehicle_cost = fixed_rate + (distance_km * variable_rate)
                total_calculated_cost += vehicle_cost
                
        return round(total_calculated_cost, 2)
    
    def est_cost_card(self, parent):
        frame = ttk.Frame(parent, relief="groove", borderwidth=2)
        
        total_calculated_cost = 0.0
        for vehicle_id, distance_meters in enumerate(self.per_vehicle_distance):
            if distance_meters > 0:  
                distance_km = distance_meters / 1000.0
                
                raw_fixed = self.vehicle_fixed_costs[vehicle_id] if vehicle_id < len(self.vehicle_fixed_costs) else 0
                raw_variable = self.vehicle_variable_costs[vehicle_id] if vehicle_id < len(self.vehicle_variable_costs) else 0
                
                try:
                    fixed_rate = float(raw_fixed) if raw_fixed else 0.0
                except (ValueError, TypeError):
                    fixed_rate = 0.0
                    
                try:
                    variable_rate = float(raw_variable) if raw_variable else 0.0
                except (ValueError, TypeError):
                    variable_rate = 0.0
                
                vehicle_cost = fixed_rate + (distance_km * variable_rate)
                total_calculated_cost += vehicle_cost
                
        actual_cost = round(total_calculated_cost, 2)
        
        baseline_distance, _ = self.calculate_entered_order_baseline()
        baseline_km = baseline_distance / 1000.0
        
        clean_vars = []
        for v in self.vehicle_variable_costs:
            try:
                clean_vars.append(float(v))
            except (ValueError, TypeError):
                clean_vars.append(0.0)

        clean_fixed = []
        for f in self.vehicle_fixed_costs:
            try:
                clean_fixed.append(float(f))
            except (ValueError, TypeError):
                clean_fixed.append(0.0)

        avg_var_rate = sum(clean_vars) / len(clean_vars) if clean_vars else 1.0
        avg_fix_rate = sum(clean_fixed) / len(clean_fixed) if clean_fixed else 0.0
        
        baseline_cost = avg_fix_rate + (baseline_km * avg_var_rate)
        
        if baseline_cost > 0 and actual_cost > 0:
            change = ((baseline_cost - actual_cost) / baseline_cost) * 100
            if change >= 0:
                comparison_text = f"↓ {round(abs(change))}% savings vs baseline"
                comparison_color = "green"
            else:
                comparison_text = f"↑ {round(abs(change))}% over baseline"
                comparison_color = "red"
        else:
            comparison_text = "Optimized Asset Budget"
            comparison_color = "blue"

        ttk.Label(frame, text="Estimated Cost", font=("Helvetica", 9)).grid(
            row=0, column=0, padx=12, pady=(10, 2), sticky='nw'
        )
        ttk.Label(frame, text=f"${actual_cost:,.2f}", font=("Helvetica", 16, "bold")).grid(
            row=1, column=0, padx=12, pady=2, sticky='nw'
        )
        ttk.Label(frame, text=comparison_text, font=("Helvetica", 8), foreground=comparison_color).grid(
            row=2, column=0, padx=12, pady=(2, 10), sticky='nw'
        )
        
        return frame
    
   
    def arrange_rs_and_cu_cards(self):
        self.rs_cu_container = ttk.Frame(self.cards_frame)
        self.rs_cu_container.pack(expand=True, fill='x', padx=6, pady=6)

        self.rs_cu_container.columnconfigure(0, weight=1)
        self.rs_cu_container.columnconfigure(1, weight=1)

        self.card_rs = self.route_sequence_card(self.rs_cu_container)
        self.card_rs.grid(row=0, column=0, padx=6, pady=6, sticky='nsew')

        self.card_cu = self.capacity_utilization_card(self.rs_cu_container)
        self.card_cu.grid(row=0, column=1, padx=6, pady=6, sticky='nsew')

        ttk.Separator(self.cards_frame, orient="horizontal", bootstyle="secondary").pack(fill="x", padx=20, pady=10)

   
    def route_sequence_card(self, parent):
        frame = ttk.Frame(parent, relief="groove", borderwidth=2)
        # Header row
        header = ttk.Frame(frame)
        header.grid(row=0, column=0, padx=12, pady=(10, 4), sticky='nw')
        ttk.Label(header, text="Route sequence", font=("Helvetica", 11, "bold")).pack(side='left')

        if self.num_nodes_dropped > 0:
            ttk.Label(header, text="out of scope", font=("Helvetica", 8), foreground="white", background="red").pack(side='left', padx=(6, 0))
        else:
            ttk.Label(header, text="in scope", font=("Helvetica", 8), foreground="white", background="green").pack(side='left', padx=(6, 0))

        flat_addresses = [addr for sublist in self.addresses for addr in sublist]
        
        vehicle_routes = [
            [flat_addresses[i] for i in vehicle]
            for vehicle in self.nodes_order
        ]

        pickup_nodes = set()
        delivery_nodes = set()
        for pair in self.pickups_and_deliveries:
            pickup_nodes.add(pair[0])
            delivery_nodes.add(pair[1])

        def get_stop_color(node_index, position, route_length):
            if position == 0:
                return "blue"        
            elif position == route_length - 1:
                return "gray"        
            elif node_index in pickup_nodes:
                return "green"       # Pickup
            elif node_index in delivery_nodes:
                return "orange"      
            else:
                return "green"      
             

        def show_route(route, node_indices):
            for widget in self.route_stops_frame.winfo_children():
                widget.destroy()
            route_length = len(route)
            for ctr, (addr, node_idx) in enumerate(zip(route, node_indices)):
                color = get_stop_color(node_idx, ctr, route_length)
                row_frame = ttk.Frame(self.route_stops_frame)
                row_frame.grid(row=ctr, column=0, pady=2, padx=12, sticky='w')
                ttk.Label(row_frame, text="●", foreground=color, font=("Helvetica", 10)).pack(side='left', padx=(0, 6))
                ttk.Label(row_frame, text=f"{addr}", font=("Helvetica", 8), wraplength=600, justify='left', anchor='w').pack(side='left')

        tab_row = ttk.Frame(frame)

        ctr_tab_row = 0
        num_btns = 5

        for i, (route, node_indices) in enumerate(zip(vehicle_routes, self.nodes_order)):
            ttk.Button(tab_row, text=f"Vehicle {i + 1}",
                       command=lambda r=route, ni=node_indices: show_route(r, ni)
                       ).pack(side='left', padx=2)

            tab_row.grid(row=1 + ctr_tab_row, column=0, padx=12, pady=(0, 6), sticky='nw')

            if i >= num_btns:
                ctr_tab_row += 1
                num_btns += 5
        
        self.route_stops_frame = ttk.Frame(frame)
        self.route_stops_frame.grid(row=2, column=0, padx=12, pady=(0, 10), sticky='nsew')

        legend = ttk.Frame(frame)
        legend.grid(row=3, column=0, padx=12, pady=(4, 10), sticky='nw')
        for color, label in [("blue", "Depot"), ("green", "Pickup"), ("orange", "Delivery"), ("gray", "Return")]:
            ttk.Label(legend, text="●", foreground=color, font=("Helvetica", 8)).pack(side='left')
            ttk.Label(legend, text=label, font=("Helvetica", 8)).pack(side='left', padx=(2, 8))

        return frame
    
   
    def capacity_utilization_card(self, parent):
    
        frame = ttk.Frame(parent, relief="groove", borderwidth=2)

        is_over_capacity = False
        for i, w in enumerate(self.per_vehicle_weight):
            if w > self.max_weight[i]:
                is_over_capacity = True
                break
        if not is_over_capacity:
            for i, v in enumerate(self.per_vehicle_volume):
                if v > self.max_volume[i]:
                    is_over_capacity = True
                    break

        header = ttk.Frame(frame)
        header.grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 4), sticky='nw')
        ttk.Label(header, text="Capacity utilization", font=("Helvetica", 11, "bold")).pack(side='left')

        if is_over_capacity:
            ttk.Label(header, text="out of scope", font=("Helvetica", 8), foreground="white", background="red").pack(side='left', padx=(6, 0))
        else:
            ttk.Label(header, text="in scope", font=("Helvetica", 8), foreground="white", background="green").pack(side='left', padx=(6, 0))

        ttk.Label(frame, text="Weight", font=("Helvetica", 9, "bold")).grid(row=1, column=0, columnspan=2, padx=12, pady=(6, 2), sticky='nw')

        wt_ctr = 0
        vol_ctr = 0

        for i in self.per_vehicle_weight:
            ttk.Label(frame, text=f"Vehicle {wt_ctr + 1}", font=("Helvetica", 8)).grid(row=2 + wt_ctr, column=0, padx=12, pady=2, sticky='nw')
            v1_weight_bar = ttk.Progressbar(frame, orient='horizontal', length=160, mode='determinate', value=round((i / self.max_weight[wt_ctr]) * 100))
            v1_weight_bar.grid(row=2 + wt_ctr, column=1, padx=(4, 12), pady=2, sticky='ew')
            ttk.Label(frame, text=f"{i}/{self.max_weight[wt_ctr]} kg", font=("Helvetica", 8), foreground="gray").grid(row=2 + wt_ctr, column=2, padx=(0, 12), pady=2, sticky='nw')
            wt_ctr += 1

        for i in self.per_vehicle_volume:
            ttk.Label(frame, text=f"Vehicle {vol_ctr + 1}", font=("Helvetica", 8)).grid(row=5 + vol_ctr, column=0, padx=12, pady=2, sticky='nw')
            v1_vol_bar = ttk.Progressbar(frame, orient='horizontal', length=160, mode='determinate', value=round((i / self.max_volume[vol_ctr]) * 100))
            v1_vol_bar.grid(row=5 + vol_ctr, column=1, padx=(4, 12), pady=2, sticky='ew')
            ttk.Label(frame, text=f"{i}/{self.max_volume[vol_ctr]} m³", font=("Helvetica", 8), foreground="gray").grid(row=5 + vol_ctr, column=2, padx=(0, 12), pady=2, sticky='nw')
            vol_ctr += 1

        ttk.Label(frame, text="Volume", font=("Helvetica", 9, "bold")).grid(row=4, column=0, columnspan=2, padx=12, pady=(8, 2), sticky='nw')

        frame.columnconfigure(1, weight=1)
        return frame
    
   
    def dropped_stops_card(self):
        frame = ttk.Frame(self.cards_frame, relief="groove", borderwidth=2)
        frame.pack(expand=True, fill='x', padx=12, pady=6)

        header = ttk.Frame(frame)
        header.grid(row=0, column=0, padx=12, pady=(10, 4), sticky='nw')
        ttk.Label(header, text="Dropped stops", font=("Helvetica", 11, "bold")).pack(side='left')

        if self.num_nodes_dropped > 0:
            ttk.Label(header, text="out of scope", font=("Helvetica", 8), foreground="white", background="red").pack(side='left', padx=(6, 0))
        else:
            ttk.Label(header, text="in scope", font=("Helvetica", 8), foreground="white", background="green").pack(side='left', padx=(6, 0))
    
        flat_addresses = [addr for sublist in self.addresses for addr in sublist]
        
        dropped_addresses = [flat_addresses[i] for i in self.dropped_nodes if i < len(flat_addresses)]

        self.dropped_stops_frame = ttk.Frame(frame)
        self.dropped_stops_frame.grid(row=1, column=0, padx=12, pady=(0, 10), sticky='nsew')

        if self.num_nodes_dropped == 0:
            ttk.Label(self.dropped_stops_frame, text="No nodes were dropped", font=("Helvetica", 8), foreground="gray").grid(row=0, column=0, padx=6, pady=(4, 0), sticky='nw')

        ctr = 0

        for dropped_address in dropped_addresses:
            ttk.Label(self.dropped_stops_frame, text=f"{dropped_address}", font=("Helvetica", 10, "bold")).grid(row=1 + ctr, column=0, padx=6, pady=(4, 0), sticky='ew')
            ctr += 1

        frame.columnconfigure(0, weight=1)

        ttk.Separator(self.cards_frame, orient="horizontal", bootstyle="secondary").pack(fill="x", padx=20, pady=10)

    def gemini_function_call(self, dispatcher_instruction: str = ""):
        
        client = genai.Client(api_key=API_KEY) 

        results_payload = self.results

        analyze_and_adjust_route_tool = {
            "name": "analyze_and_adjust_route",
            "description": (
                "Analyzes active route performance, constraints, and anomalies (such as dropped nodes "
                "or SLA breaches) and executes modifications or dispatch adjustments."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "input_num_vehicles": {
                        "type": "integer",
                        "description": "The initial number of vehicles configured for dispatch."
                    },
                    "input_max_weight": {
                        "type": "number",
                        "description": "The maximum allowable vehicle cargo weight capacity constraint."
                    },
                    "input_max_volume": {
                        "type": "number",
                        "description": "The maximum allowable vehicle cargo volume capacity constraint."
                    },
                    "total_distance": {
                        "type": "number",
                        "description": "Total combined distance traveled across all active vehicle routes (in meters)."
                    },
                    "total_time": {
                        "type": "number",
                        "description": "Total combined duration of all active routes (in minutes)."
                    },
                    "dropped_nodes": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of node/stop IDs that could not be serviced by the routing engine due to constraints."
                    },
                    "nodes_order": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer"}
                        },
                        "description": "A list of lists, where each sublist represents the ordered sequence of node IDs visited by a specific vehicle."
                    },
                    "time_windows_order": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "minItems": 2,
                                "maxItems": 2
                            }
                        },
                        "description": "A list of lists containing [min_time, max_time] arrival window boundaries for each node in nodes_order."
                    },
                    "per_vehicle_weight": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Total weight loaded onto each active vehicle."
                    },
                    "per_vehicle_volume": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Total volume loaded onto each active vehicle."
                    },

                    "vehicle_fixed_costs": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "The fixed daily cost assigned to each vehicle."
                    },
                    "vehicle_variable_costs": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "The per-km variable cost assigned to each vehicle."
                    },
                    "max_travel_time": {
                        "type": "number",
                        "description": "Maximum allowed travel time per vehicle (in minutes)."
                    },
                    "break_allowance": {
                        "type": "number",
                        "description": "Allowed break/waiting time for vehicles (in minutes)."
                    },
                    "penalty_weight": {
                        "type": "number",
                        "description": "Penalty cost applied when a stop is dropped/unassigned."
                    },
                    "max_travel_distance": {
                        "type": "number",
                        "description": "Maximum allowed travel distance per vehicle (in km)."
                    },
                    "target_adjustments": {
                        "type": "string",
                        "description": "The strategic operational action to resolve route inefficiencies or accommodate dispatcher input."
                    },
            
                    "target_adjustments": {
                        "type": "array",
                        "description": "A list of actionable alternative strategies generated by the AI to optimize constraints or lower operational windows.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "strategy_type": {
                                    "type": "string",
                                    "description": "Category of action: 'RE_SEQUENCE', 'FLEET_EXPANSION', 'TIME_WINDOW_SHIFT', or 'CAPACITY_REDUNDANCY'."
                                },
                                "impact_score": {
                                    "type": "string",
                                    "description": "The priority or effectiveness level of this suggestion: 'HIGH', 'MEDIUM', or 'LOW'."
                                },
                                "description": {
                                    "type": "string",
                                    "description": "A clear, concise operational explanation of what the dispatcher should change."
                                },
                                "estimated_time_saved_mins": {
                                    "type": "integer",
                                    "description": "An approximation of how much transit/idle time this specific option cuts from the timeline."
                                }
                            },
                            "required": ["strategy_type", "impact_score", "description"]
                        }
                    }
                },
                    "required": [
                        "input_num_vehicles", 
                        "total_distance", 
                        "total_time", 
                        "dropped_nodes", 
                        "nodes_order", 
                        "time_windows_order",
                        "vehicle_fixed_costs",
                        "vehicle_variable_costs",
                        "max_travel_time",
                        "break_allowance",
                        "penalty_weight",
                        "max_travel_distance"
                    ],
                },
            }

        tools = types.Tool(function_declarations=[analyze_and_adjust_route_tool])
        
        config = types.GenerateContentConfig(
            tools=[tools], 
            temperature=0.1,
            system_instruction=(
                "You are an integrated AI co-pilot built inside a logistics route optimization engine. "
                "Your objective is to ingest the operational constraints, parameters, and solution matrices, "
                "cross-reference them with user instructions, and output structured tool payloads back to the "
                "backend routing execution matrix."
            )
        )

        prompt_context = (
            f"--- CURRENT SOLVER STATE ---\n"
            f"Configured Vehicles: {results_payload['input_num_vehicles']}\n"
            f"Max Allowed Capacity: Weight={results_payload['input_max_weight']}kg, Volume={results_payload['input_max_volume']} units\n"
            f"Current Route Totals: Distance={results_payload['total_distance']}m, Time={results_payload['total_time']}min\n"
            f"Dropped Stops (Unassigned Nodes): {results_payload['dropped_nodes']}\n"
            f"Active Node Sequence Paths: {results_payload['nodes_order']}\n"
            f"Calculated Node Arrival Time Windows: {results_payload['time_windows_order']}\n"
            f"Vehicle Fixed Costs: {results_payload['vehicle_fixed_costs']}\n"
            f"Vehicle Variable Costs: {results_payload['vehicle_variable_costs']}\n"
            f"Max Travel Time per Vehicle: {results_payload['max_travel_time']} min\n"
            f"Break/Wait Allowance: {results_payload['break_allowance']} min\n"
            f"Penalty Weight (Drop Cost): {results_payload['penalty_weight']}\n"
            f"Max Travel Distance per Vehicle: {results_payload['max_travel_distance']} km\n\n"
            f"--- DISPATCHER INTERVENTION STATEMENT ---\n"
            f"User Input: '{dispatcher_instruction if dispatcher_instruction else 'Analyze routing profile for failures and suggest optimization modifications.'}'"
        )

        print("🤖 Processing context with Gemini...")
        
        try:
            response = client.models.generate_content(
                model="gemini-3-flash-preview", 
                contents=prompt_context,
                config=config,
            )

            has_executed_calls = False

            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        has_executed_calls = True
                        function_call = part.function_call
                        args = function_call.args
                        
                        print("\n🎯 [Gemini Function Call Triggered]")
                        print(f" -> Function Name: {function_call.name}")
                        
                        suggestions_list = args.get("target_adjustments", [])
                        print(f"\n📊 Generated {len(suggestions_list)} Strategies for the UI Panel:")
                        
                        for index, item in enumerate(suggestions_list, 1):
                            self.get_strategy_type = item.get('strategy_type')
                            self.get_impact_score = item.get('impact_score')
                            self.get_description = item.get('description')
                            self.get_potential_savings = item.get('estimated_time_saved_mins', 0)

                            print(f"\n[Option #{index}] Type: {self.get_strategy_type} ({self.get_impact_score} Impact)")
                            print(f" -> Advice: {self.get_description}")
                            print(f" -> Potential Savings: {self.get_potential_savings} mins")

                            self.collect_gemini_responses[f"Option {index}"] = {"strategy type": self.get_strategy_type,"impact score": self.get_impact_score,"description": self.get_description,"potential savings": self.get_potential_savings}
            
            if not has_executed_calls:
                print("\nℹ️ No operational adjustments required based on constraints. Conversational text:")
                print(response.text)

        except Exception as e:
            print(f"❌ Error compiling route updates via Gemini API: {e}")

    
    def suggestions_card(self):
        frame = ttk.Frame(self.cards_frame, relief='groove', borderwidth=2)
        frame.pack(expand=True, fill='x', padx=12, pady=6)

        header = ttk.Frame(frame)
        header.grid(row=0, column=0, padx=12, pady=(10, 4), sticky='nw')
        ttk.Label(header, text="Suggestions", font=("Helvetica", 11, "bold")).pack(side='left')
        ttk.Label(header, text="Gemini Free API", font=("Helvetica", 8), foreground="white", background="blue").pack(side='left', padx=(6, 0))

        ctr = 0

        if not self.collect_gemini_responses:
            suggestions_frame = ttk.Frame(frame)
            suggestions_frame.grid(row=2 + ctr, column=0, padx=12, pady=(0, 10), sticky='nsew')
            
            # Fallback message
            ttk.Label(
                suggestions_frame, 
                text="No optimization suggestions available at this time. Please run a route adjustment to generate strategies.", 
                font=("Helvetica", 10, "italic"), 
                foreground="gray",
                justify='left', 
                anchor='w',
                wraplength=350 # or use frame_width math
            ).pack(anchor='w', fill='x', pady=10)

        else:
            for idx, (key, value) in enumerate(self.collect_gemini_responses.items(), 1):
                retrieve_strategy_type = self.collect_gemini_responses[f"Option {idx}"].get("strategy type", "Strategy type missing")
                retrieve_impact_score = self.collect_gemini_responses[f"Option {idx}"].get("impact score", "Impact score missing")
                retrieve_description = self.collect_gemini_responses[f"Option {idx}"].get("description", "Description missing")
                retrieve_potential_savings = self.collect_gemini_responses[f"Option {idx}"].get("potential savings", "Potential savings missing")

                # ── Card container with border ──────────────────────────────
                card = ttk.Frame(frame, relief="solid", borderwidth=1)
                card.grid(row=2 + ctr, column=0, padx=12, pady=(0, 10), sticky='nsew')

                # ── Impact badge color ──────────────────────────────────────
                impact_colors = {"HIGH": "#e74c3c", "MEDIUM": "#f39c12", "LOW": "#27ae60"}
                badge_color = impact_colors.get(str(retrieve_impact_score).upper(), "#888888")

                # ── Header row: strategy type + impact badge ────────────────
                card_header = ttk.Frame(card)
                card_header.pack(fill='x', padx=12, pady=(10, 4))

                ttk.Label(
                    card_header,
                    text=f"#{idx}  {retrieve_strategy_type}",
                    font=("Helvetica", 11, "bold"),
                    anchor='w'
                ).pack(side='left')

                impact_badge = tk.Label(
                    card_header,
                    text=f" {retrieve_impact_score} ",
                    font=("Helvetica", 9, "bold"),
                    foreground="white",
                    background=badge_color,
                    padx=6,
                    pady=1
                )
                impact_badge.pack(side='left', padx=(8, 0))

                ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12, pady=(2, 6))

                ttk.Label(
                    card,
                    text=retrieve_description,
                    font=("Helvetica", 10),
                    justify='left',
                    anchor='w',
                    wraplength=500
                ).pack(anchor='w', fill='x', padx=12, pady=(0, 6))

                card_footer = ttk.Frame(card)
                card_footer.pack(fill='x', padx=12, pady=(0, 10))

                ttk.Label(
                    card_footer,
                    text=f"⏱ Potential Savings: {retrieve_potential_savings} mins",
                    font=("Helvetica", 10, "bold"),
                    anchor='w'
                ).pack(side='left')

                ttk.Label(
                    card_footer,
                    text="✨ Gemini",
                    font=("Helvetica", 9),
                    foreground='blue',
                    anchor='e'
                ).pack(side='right')

                ctr += 1
                
            ttk.Separator(self.cards_frame, orient="horizontal", bootstyle="secondary").pack(fill="x", padx=20, pady=10)

            frame.columnconfigure(0, weight=1)
    

    def calculate_health_score_metrics(self):
        total_stops = sum(len(stops) for stops in self.stored_stops.values())
        num_nodes_dropped = len(self.dropped_nodes)
        stops_served = ((total_stops - num_nodes_dropped) / total_stops * 100) if total_stops > 0 else 0
        
        tw_violations = 0
        total_stops_with_tw = 0
        
        for vehicle_idx, time_windows in enumerate(self.time_windows_order):
            for stop_idx, (min_time, max_time) in enumerate(time_windows):
                node_sequence = self.nodes_order[vehicle_idx]
                if stop_idx < len(node_sequence):
                    node_id = node_sequence[stop_idx]
                    
                    if node_id not in self.start and node_id not in self.end:
                        total_stops_with_tw += 1
                        expected_tw = self.time_windows[node_id]
                        
                        if min_time < expected_tw[0] or max_time > expected_tw[1]:
                            tw_violations += 1
        
        tw_adherence = ((total_stops_with_tw - tw_violations) / total_stops_with_tw * 100) if total_stops_with_tw > 0 else 100
        
        weight_utilization = []
        volume_utilization = []
        
        for i in range(self.num_stored_vehicles):
            if self.max_weight[i] > 0:
                weight_util = (self.per_vehicle_weight[i] / self.max_weight[i]) * 100
                weight_utilization.append(weight_util)
            
            if self.max_volume[i] > 0:
                volume_util = (self.per_vehicle_volume[i] / self.max_volume[i]) * 100
                volume_utilization.append(volume_util)
        
        all_utilizations = weight_utilization + volume_utilization
        capacity_use = sum(all_utilizations) / len(all_utilizations) if all_utilizations else 0
        
        total_productive_time = 0
        total_idle_time = 0
        
        for vehicle_idx in range(self.num_stored_vehicles):
            productive_time = self.per_vehicle_time[vehicle_idx]
            total_productive_time += productive_time
            
            idle_time = 0
            idle_time += self.start_load_times[vehicle_idx]
            
            vehicle_key = f"Vehicle {vehicle_idx + 1}"
            if vehicle_key in self.stored_stops:
                for stop in self.stored_stops[vehicle_key]:
                    idle_time += int(stop.get("load_times", 0))
                    idle_time += int(stop.get("unload_times", 0))
            
            total_idle_time += idle_time
        
        break_budget = int(self.break_allowance) * self.num_stored_vehicles
        penalized_idle = max(0, total_idle_time - break_budget)
        
        total_time = total_productive_time + total_idle_time
        idle_time_score = ((total_time - penalized_idle) / total_time * 100) if total_time > 0 else 0
        
        total_actual_distance = self.total_distance
        total_straight_line_distance = 0
        
        for vehicle_idx, route in enumerate(self.nodes_order):
            vehicle_coords = self.location_coors[vehicle_idx]
            
            for i in range(len(route) - 1):
                node_a = route[i]
                node_b = route[i + 1]
                
                if node_a < len(vehicle_coords) and node_b < len(vehicle_coords):
                    lat1, lon1 = vehicle_coords[node_a]
                    lat2, lon2 = vehicle_coords[node_b]
                    
                    from math import radians, sin, cos, sqrt, atan2
                    
                    R = 6371000
                    
                    lat1_rad = radians(lat1)
                    lat2_rad = radians(lat2)
                    delta_lat = radians(lat2 - lat1)
                    delta_lon = radians(lon2 - lon1)
                    
                    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2)**2
                    c = 2 * atan2(sqrt(a), sqrt(1-a))
                    
                    straight_distance = R * c
                    total_straight_line_distance += straight_distance
        
        distance_efficiency = (total_straight_line_distance / total_actual_distance * 100) if total_actual_distance > 0 else 0
        distance_efficiency = min(distance_efficiency, 100)
        
        return {
            "stops_served": round(stops_served, 1),
            "tw_adherence": round(tw_adherence, 1),
            "capacity_use": round(capacity_use, 1),
            "idle_time": round(idle_time_score, 1),
            "distance_efficiency": round(distance_efficiency, 1)
        }
    
    def _draw_health_gauge(self, parent, score):
        SIZE        = 120       
        THICKNESS   = 14        
        PAD         = 10        
        
        BG_RING     = "#495057"
        MORPH_BLUE  = "#007bff" 
        MORPH_AMBER = "#ffc107" 
        MORPH_RED   = "#dc3545" 
        SUB_CLR     = "#adb5bd" 

        if score >= 75:
            FILL_CLR = MORPH_BLUE
            TEXT_CLR = MORPH_BLUE
        elif score >= 50:
            FILL_CLR = MORPH_AMBER
            TEXT_CLR = MORPH_AMBER
        else:
            FILL_CLR = MORPH_RED
            TEXT_CLR = MORPH_RED

        CANVAS_BG = "#222222" 
        try:
            CANVAS_BG = parent.winfo_toplevel().cget("bg")
        except Exception:
            pass

        cv = tk.Canvas(parent, width=SIZE, height=SIZE,
                       bg=CANVAS_BG, highlightthickness=0)
        cv.pack(pady=(6, 2))

        x0, y0 = PAD, PAD
        x1, y1 = SIZE - PAD, SIZE - PAD

        cv.create_arc(x0, y0, x1, y1,
                      start=0, extent=359.9,
                      outline=BG_RING, width=THICKNESS,
                      style="arc")

        extent = (score / 100) * 360
        cv.create_arc(x0, y0, x1, y1,
                      start=90, extent=-extent,
                      outline=FILL_CLR, width=THICKNESS,
                      style="arc")

        cx, cy = SIZE / 2, SIZE / 2
        cv.create_text(cx, cy - 8, text=str(score),
                       font=("Helvetica", 22, "bold"),
                       fill=TEXT_CLR)

        cv.create_text(cx, cy + 14, text="/ 100",
                       font=("Helvetica", 9),
                       fill=SUB_CLR)
    
    
    def health_score_card(self):
        frame = ttk.Frame(self.cards_frame, relief='groove', borderwidth=2)
        frame.pack(expand=True, fill='x', padx=12, pady=6)

        header = ttk.Frame(frame)
        header.grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 4), sticky='nw')
        ttk.Label(header, text="Health score", font=("Helvetica", 11, "bold")).pack(side='left')
        ttk.Label(header, text="in scope", font=("Helvetica", 8), foreground="white", background="green").pack(side='left', padx=(6, 0))
        
        metrics = self.calculate_health_score_metrics()
        
        weights = {
            "stops_served": 0.20,
            "tw_adherence": 0.20,
            "capacity_use": 0.15,
            "idle_time": 0.10,
            "distance_efficiency": 0.10,
            
        }
        
        overall_score = sum(metrics[key] * weights[key] for key in weights.keys())
        
        self.health_score_gauge_frame = ttk.Frame(frame)
        self.health_score_gauge_frame.grid(row=1, column=0, padx=12, pady=(0, 10), sticky='nsew')

        self._draw_health_gauge(self.health_score_gauge_frame, round(overall_score))

        metrics_frame = ttk.Frame(frame)
        metrics_frame.grid(row=1, column=1, padx=12, pady=(0, 10), sticky='nsew')

        metric_configs = [
            ("Stops served", metrics["stops_served"]),
            ("TW adherence", metrics["tw_adherence"]),
            ("Capacity use", metrics["capacity_use"]),
            ("Idle time", metrics["idle_time"]),
            ("Distance efficiency", metrics["distance_efficiency"]),
        ]
        
        for i, (label, value) in enumerate(metric_configs):
            if value >= 80:
                color = "green"
            elif value >= 60:
                color = "orange"
            else:
                color = "red"
                
            ttk.Label(metrics_frame, text=label, font=("Helvetica", 8)).grid(
                row=i, column=0, padx=(0, 8), pady=2, sticky='nw'
            )
            bar = ttk.Progressbar(metrics_frame, orient='horizontal', length=160, 
                                mode='determinate', value=value)
            bar.grid(row=i, column=1, pady=2, sticky='ew')
            
            ttk.Label(metrics_frame, text=f"{round(value)}%", 
                    font=("Helvetica", 8), foreground=color).grid(
                row=i, column=2, padx=(4, 0), pady=2, sticky='nw'
            )

        metrics_frame.columnconfigure(1, weight=1)
        frame.columnconfigure(1, weight=1)
   

    def export_txt(self):
        from tkinter import filedialog
        import datetime

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"RouteForge_Results_{date.today().strftime('%Y-%m-%d')}.txt",
            title="Export Results"
        )
        if not filepath:
            return

        flat_addresses = [addr for sublist in self.addresses for addr in sublist]
        vehicle_routes = [
            [flat_addresses[i] for i in vehicle_nodes]
            for vehicle_nodes in self.nodes_order
        ]

        baseline_distance, baseline_time = self.calculate_entered_order_baseline()
        baseline_km    = round(baseline_distance / 1000)
        baseline_hours = baseline_time // 60
        baseline_mins  = baseline_time % 60

        total_km    = round(self.total_distance / 1000)
        total_hours = self.total_time // 60
        total_mins  = self.total_time % 60

        total_stops   = sum(len(stops) for stops in self.stored_stops.values())
        stops_served  = total_stops - len(self.dropped_nodes)

        actual_cost = self.calculate_actual_routing_costs()

        lines = []
        W = 60  

        def sep(char="─"):
            lines.append(char * W)

        def heading(text):
            sep("═")
            lines.append(f"  {text}")
            sep("═")

        lines.append("=" * W)
        lines.append("  RouteForge — Optimization Results".center(W))
        lines.append(f"  Generated : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(W))
        lines.append(f"  Vehicles  : {self.num_stored_vehicles}".center(W))
        lines.append("=" * W)
        lines.append("")

        heading("SUMMARY")
        lines.append(f"  Total Distance   : {total_km} km  (baseline {baseline_km} km)")
        if baseline_km > 0:
            dist_pct = round(((baseline_km - total_km) / baseline_km) * 100)
            lines.append(f"                     ↓ {dist_pct}% vs entered order")

        lines.append(f"  Total Time       : {total_hours}h {total_mins}m  "
                    f"(baseline {baseline_hours}h {baseline_mins}m)")
        if baseline_time > 0:
            time_pct = round(((baseline_time - self.total_time) / baseline_time) * 100)
            lines.append(f"                     ↓ {time_pct}% vs entered order")

        lines.append(f"  Stops Served     : {stops_served} / {total_stops}"
                    + (f"  ({len(self.dropped_nodes)} dropped)" if self.dropped_nodes else ""))
        lines.append(f"  Estimated Cost   : ${actual_cost:,.2f}")
        lines.append("")

        heading("ROUTE SEQUENCES")
        for v_idx, route in enumerate(vehicle_routes):
            v_dist_km = round(self.per_vehicle_distance[v_idx] / 1000) if v_idx < len(self.per_vehicle_distance) else "—"
            v_time    = self.per_vehicle_time[v_idx] if v_idx < len(self.per_vehicle_time) else 0
            v_hours   = v_time // 60
            v_mins    = v_time % 60
            lines.append(f"  Vehicle {v_idx + 1}  —  {v_dist_km} km  |  {v_hours}h {v_mins}m")
            sep()
            for step, addr in enumerate(route):
                if step == 0:
                    tag = "[DEPOT START]"
                elif step == len(route) - 1:
                    tag = "[DEPOT RETURN]"
                else:
                    tag = f"[Stop {step}]"
                lines.append(f"    {tag:15s}  {addr}")
            lines.append("")

        heading("CAPACITY UTILIZATION")
        lines.append(f"  {'Vehicle':<12} {'Weight Used':>12} {'Weight Cap':>12} {'Vol Used':>10} {'Vol Cap':>10}")
        sep()
        for i in range(self.num_stored_vehicles):
            wt      = self.per_vehicle_weight[i] if i < len(self.per_vehicle_weight) else 0
            wt_cap  = self.max_weight[i] if i < len(self.max_weight) else 0
            vol     = self.per_vehicle_volume[i] if i < len(self.per_vehicle_volume) else 0
            vol_cap = self.max_volume[i] if i < len(self.max_volume) else 0
            lines.append(f"  {'Vehicle ' + str(i+1):<12} {str(wt) + ' kg':>12} {str(wt_cap) + ' kg':>12} "
                        f"{str(vol) + ' m³':>10} {str(vol_cap) + ' m³':>10}")
        lines.append("")

        heading("DROPPED STOPS")
        if not self.dropped_nodes:
            lines.append("  No stops were dropped.")
        else:
            dropped_addresses = [flat_addresses[i] for i in self.dropped_nodes if i < len(flat_addresses)]
            for addr in dropped_addresses:
                lines.append(f"  • {addr}")
        lines.append("")

        heading("GEMINI SUGGESTIONS")
        if not self.collect_gemini_responses:
            lines.append("  No suggestions available — Gemini API key not set or not yet run.")
        else:
            for idx, (key, value) in enumerate(self.collect_gemini_responses.items(), 1):
                strategy  = value.get("strategy type", "—")
                impact    = value.get("impact score", "—")
                desc      = value.get("description", "—")
                savings   = value.get("potential savings", "—")
                lines.append(f"  Option {idx}  [{impact} Impact]")
                sep()
                lines.append(f"  Strategy : {strategy}")
                lines.append(f"  Details  : {desc}")
                lines.append(f"  Savings  : {savings} mins")
                lines.append("")

        sep("═")
        lines.append("  End of report — RouteForge Analytics")
        sep("═")

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            messagebox.showinfo("Export Successful", f"Results exported to:\n{filepath}")
        except OSError as e:
            messagebox.showerror("Export Failed", f"Could not write file:\n{e}")

class Load_Optimizations(ttk.Frame):
    _HEADER_BG    = "#2e2e2e"
    _ROW_BG_EVEN  = "#3a3a3a"
    _ROW_BG_ODD   = "#424242"
    _BORDER_CLR   = "#555555"
    _ACCENT       = "#4a90d9"
    _TEXT_MAIN    = "#e8e8e8"
    _TEXT_DIM     = "#aaaaaa"
    _ROWS_PER_PAGE = 5

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self._current_page  = 1
        self._all_drafts    = []
        self._filtered      = []
        self._autocomplete_visible = False

        self.inner_frame = ttk.Frame(self)
        self.inner_frame.pack(fill='x', expand=True)

        self.title_frame = ttk.Frame(self.inner_frame, relief="groove", borderwidth=2)
        self.title_frame.pack(fill="x", padx=20, pady=(10, 0))

        self.title_text_frame = ttk.Frame(self.title_frame)
        self.title_text_frame.pack(side=tk.LEFT, fill="both", expand=True)

        self.lbl_title = ttk.Label(
            self.title_text_frame, text="Load Optimizations", font=("Helvetica", 40)
        )
        self.lbl_title.pack(side=tk.TOP, anchor=tk.NW, padx=(30, 0), pady=(10, 0))

        self.lbl_title_desc = ttk.Label(
            self.title_text_frame,
            text="Select a previously saved optimization to continue",
            font=("Helvetica", 16),
        )
        self.lbl_title_desc.pack(side=tk.TOP, anchor=tk.NW, padx=(60, 0), pady=(2, 15))

        self.title_btn_frame = ttk.Frame(self.title_frame)
        self.title_btn_frame.pack(side=tk.RIGHT, padx=(0, 30), pady=10, fill="y")

        self.btn_refresh = ttk.Button(
            self.title_btn_frame, text="↺ Refresh", command=self.refresh_table
        )
        self.btn_refresh.pack(side=tk.TOP, pady=(0, 5))

        self.btn_back = ttk.Button(
            self.title_btn_frame, text="← Back", width=9,
            command=lambda: controller.show_page("Inital_Screen"),
        )
        self.btn_back.pack(side=tk.TOP)

        self._build_search_bar()

        self.table_container = ttk.Frame(self.inner_frame)
        self.table_container.pack(fill="x", padx=40, pady=(10, 0))

        self._build_pagination_bar()

        self._load_and_render()

   
    def _build_search_bar(self):
        search_outer = tk.Frame(
            self.inner_frame,
            background=self._HEADER_BG,
            highlightthickness=1,
            highlightbackground=self._BORDER_CLR,
        )
        search_outer.pack(fill="x", padx=40, pady=(14, 0))

        tk.Label(
            search_outer, text="⌕",
            font=("Helvetica", 16),
            fg=self._TEXT_DIM, bg=self._HEADER_BG,
        ).pack(side="left", padx=(12, 4), pady=8)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)

        self._search_entry = tk.Entry(
            search_outer,
            textvariable=self._search_var,
            font=("Helvetica", 13),
            fg=self._TEXT_MAIN,
            bg=self._HEADER_BG,
            insertbackground=self._TEXT_MAIN,
            relief="flat",
            bd=0,
        )
        self._search_entry.pack(side="left", fill="both", expand=True, pady=10)
        self._search_entry.insert(0, "Search optimizations…")
        self._search_entry.config(fg=self._TEXT_DIM)

        self._search_entry.bind("<FocusIn>",  self._on_search_focus_in)
        self._search_entry.bind("<FocusOut>", self._on_search_focus_out)
        self._search_entry.bind("<Return>",   lambda e: self._hide_autocomplete())
        self._search_entry.bind("<Escape>",   lambda e: self._hide_autocomplete())

        self._btn_clear_search = tk.Label(
            search_outer, text="✕",
            font=("Helvetica", 13),
            fg=self._TEXT_DIM, bg=self._HEADER_BG,
            cursor="hand2",
        )
        self._btn_clear_search.pack(side="right", padx=12)
        self._btn_clear_search.bind("<Button-1>", self._clear_search)

        self._autocomplete_frame = tk.Frame(
            self.inner_frame,
            background="#2a2a2a",
            highlightthickness=1,
            highlightbackground=self._ACCENT,
        )
        self._autocomplete_listbox = tk.Listbox(
            self._autocomplete_frame,
            font=("Helvetica", 12),
            fg=self._TEXT_MAIN,
            bg="#2a2a2a",
            selectbackground=self._ACCENT,
            selectforeground="#ffffff",
            relief="flat",
            bd=0,
            activestyle="none",
            highlightthickness=0,
        )
        self._autocomplete_listbox.pack(fill="both", expand=True, padx=2, pady=2)
        self._autocomplete_listbox.bind("<<ListboxSelect>>", self._on_autocomplete_select)

        self._search_outer = search_outer


    def _on_search_focus_in(self, event):
        if self._search_entry.get() == "Search optimizations…":
            self._search_entry.delete(0, "end")
            self._search_entry.config(fg=self._TEXT_MAIN)


    def _on_search_focus_out(self, event):
        if not self._search_entry.get().strip():
            self._search_entry.insert(0, "Search optimizations…")
            self._search_entry.config(fg=self._TEXT_DIM)


    def _on_search_change(self, *_):
        query = self._search_var.get().strip()
        placeholder = "Search optimizations…"

        if not query or query == placeholder:
            self._filtered = list(self._all_drafts)
            self._hide_autocomplete()
        else:
            ql = query.lower()
            self._filtered = [d for d in self._all_drafts if ql in d["name"].lower()]
            self._show_autocomplete(ql)

        self._current_page = 1
        self._render_table()
        self._update_pagination_label()


    def _show_autocomplete(self, query_lower):
        matches = [d["name"] for d in self._all_drafts if query_lower in d["name"].lower()]
        if not matches:
            self._hide_autocomplete()
            return

        self._autocomplete_listbox.delete(0, "end")
        for name in matches[:8]:
            self._autocomplete_listbox.insert("end", name)

        self._search_outer.update_idletasks()
        x = self._search_outer.winfo_x()
        y = self._search_outer.winfo_y() + self._search_outer.winfo_height()
        w = self._search_outer.winfo_width()
        h = min(len(matches), 8) * 28 + 6

        self._autocomplete_frame.place(x=x, y=y, width=w, height=h)
        self._autocomplete_frame.lift()
        self._autocomplete_visible = True


    def _hide_autocomplete(self):
        if self._autocomplete_visible:
            self._autocomplete_frame.place_forget()
            self._autocomplete_visible = False


    def _on_autocomplete_select(self, event):
        sel = self._autocomplete_listbox.curselection()
        if not sel:
            return
        chosen = self._autocomplete_listbox.get(sel[0])
        self._search_var.set(chosen)
        self._search_entry.config(fg=self._TEXT_MAIN)
        self._hide_autocomplete()
        self._search_entry.icursor("end")


    def _clear_search(self, event=None):
        self._search_var.set("")
        self._search_entry.delete(0, "end")
        self._search_entry.insert(0, "Search optimizations…")
        self._search_entry.config(fg=self._TEXT_DIM)
        self._hide_autocomplete()
        self._filtered = list(self._all_drafts)
        self._current_page = 1
        self._render_table()
        self._update_pagination_label()

   
    def _build_pagination_bar(self):
        self._pagination_frame = tk.Frame(self.inner_frame, background=self._HEADER_BG)
        self._pagination_frame.pack(fill="x", padx=40, pady=(6, 18))

        self._lbl_page = tk.Label(
            self._pagination_frame,
            text="Showing page 1 of 1 of optimizations",
            font=("Helvetica", 11),
            fg=self._TEXT_DIM,
            bg=self._HEADER_BG,
            anchor="w",
        )
        self._lbl_page.pack(side="left")

        btn_container = tk.Frame(self._pagination_frame, bg=self._HEADER_BG)
        btn_container.pack(side="right")

        self._btn_prev = ttk.Button(
            btn_container, text="← Previous", width=12,
            command=self._go_prev,
        )
        self._btn_prev.pack(side="left", padx=(0, 6))

        self._btn_next = ttk.Button(
            btn_container, text="Next →", width=12,
            command=self._go_next,
        )
        self._btn_next.pack(side="left")


    def _total_pages(self):
        total = max(1, len(self._filtered))
        return (total + self._ROWS_PER_PAGE - 1) // self._ROWS_PER_PAGE
    

    def _go_prev(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._render_table()
            self._update_pagination_label()


    def _go_next(self):
        if self._current_page < self._total_pages():
            self._current_page += 1
            self._render_table()
            self._update_pagination_label()


    def _update_pagination_label(self):
        if not hasattr(self, "_lbl_page"):
            return
        total_pg = self._total_pages()
        self._lbl_page.config(
            text=f"Showing page {self._current_page} of {total_pg} of optimizations"
        )
        self._btn_prev.state(["disabled"] if self._current_page <= 1 else ["!disabled"])
        self._btn_next.state(["disabled"] if self._current_page >= total_pg else ["!disabled"])

   
    def _bind_mousewheel(self, event):
        self.scroll_canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.scroll_canvas.bind_all("<Up>",  self._on_key_scroll)
        self.scroll_canvas.bind_all("<Down>", self._on_key_scroll)


    def _unbind_mousewheel(self, event):
        self.scroll_canvas.unbind_all("<MouseWheel>")
        self.scroll_canvas.unbind_all("<Up>")
        self.scroll_canvas.unbind_all("<Down>")


    def _on_key_scroll(self, event):
        focused = self.focus_get()
        if isinstance(focused, (ttk.Entry, tk.Listbox, ttk.Combobox)):
            return
        if event.keysym == "Up":
            self.scroll_canvas.yview_scroll(-1, "units")
        elif event.keysym == "Down":
            self.scroll_canvas.yview_scroll(1, "units")
        

    def _on_frame_configure(self, event):
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))


    def _on_canvas_configure(self, event):
        self.scroll_canvas.itemconfig(self.canvas_window, width=event.width)


    def _on_mouse_wheel(self, event):
        self.scroll_canvas.yview_scroll(-1 * int(event.delta / 120), "units")

   
    def _load_and_render(self):
        self._all_drafts = self._load_drafts()
        self._filtered   = list(self._all_drafts)
        self._current_page = 1
        self._render_table()
        self._update_pagination_label()

    
    def _render_table(self):
        if not hasattr(self, "table_container"):
            return
        for widget in self.table_container.winfo_children():
            widget.destroy()

        COL_WEIGHTS = [3, 2, 2, 2]
        self._create_header(COL_WEIGHTS)

        if not self._filtered:
            self._create_empty_state_row()
            return

        start = (self._current_page - 1) * self._ROWS_PER_PAGE
        page_drafts = self._filtered[start: start + self._ROWS_PER_PAGE]

        for idx, draft in enumerate(page_drafts):
            self._create_table_row(draft, idx, COL_WEIGHTS)


    def refresh_table(self):
        self._clear_search()
        self._load_and_render()


    def create_table(self):
        self._load_and_render()

    
    def _create_header(self, col_weights):
        header = tk.Frame(
            self.table_container,
            background=self._HEADER_BG,
            highlightthickness=1,
            highlightbackground=self._BORDER_CLR,
        )
        header.pack(fill="x", padx=0)
        header.grid_rowconfigure(0, weight=1)
        for i, w in enumerate(col_weights):
            header.grid_columnconfigure(i, weight=w)

        labels = [
            ("Name",          "w",      (25, 10)),
            ("Date Created",  "center", (40, 10)),
            ("Last Modified", "center", (10, 50)),
            ("Action",        "center", (10, 55)),
        ]
        for col, (text, anchor, (px_l, px_r)) in enumerate(labels):
            tk.Label(
                header,
                text=text,
                font=("Helvetica", 12, "bold"),
                fg=self._TEXT_MAIN,
                bg=self._HEADER_BG,
                anchor=anchor,
            ).grid(row=0, column=col, sticky="ew", padx=(px_l, px_r), pady=16)

  
    def _create_table_row(self, draft, row_idx, col_weights):
        row_bg = self._ROW_BG_EVEN if row_idx % 2 == 0 else self._ROW_BG_ODD

        row = tk.Frame(
            self.table_container,
            background=row_bg,
            highlightthickness=1,
            highlightbackground=self._BORDER_CLR,
        )
        row.pack(fill="x")
        row.grid_rowconfigure(0, weight=1)
        for i, w in enumerate(col_weights):
            row.grid_columnconfigure(i, weight=w)

        row_font = ("Helvetica", 12)

        tk.Label(
            row, text=draft["name"], font=row_font,
            fg=self._TEXT_MAIN, bg=row_bg, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=(25, 10), pady=14)

        tk.Label(
            row, text=draft["start_date"], font=row_font,
            fg=self._TEXT_DIM, bg=row_bg, anchor="center",
        ).grid(row=0, column=1, sticky="ew", padx=10, pady=14)

        tk.Label(
            row, text=draft["saved_at"], font=row_font,
            fg=self._TEXT_DIM, bg=row_bg, anchor="center",
        ).grid(row=0, column=2, sticky="ew", padx=10, pady=14)

        btn_frame = tk.Frame(row, background=row_bg)
        btn_frame.grid(row=0, column=3, sticky="ns", padx=(10, 25), pady=10)

        ttk.Button(
            btn_frame, text="Load",
            command=lambda d=draft: self._on_load_click(d),
        ).pack(side="left", padx=6)

        ttk.Button(
            btn_frame, text="Delete",
            command=lambda d=draft: self._on_delete_click(d),
        ).pack(side="left")


    def _create_empty_state_row(self):
        empty = tk.Frame(
            self.table_container,
            background=self._ROW_BG_EVEN,
            highlightthickness=1,
            highlightbackground=self._BORDER_CLR,
        )
        empty.pack(fill="x")
        tk.Label(
            empty,
            text="No saved optimizations found.  Use 'Save Draft' on the New Optimization page to create one.",
            font=("Helvetica", 11),
            fg=self._TEXT_DIM,
            bg=self._ROW_BG_EVEN,
            anchor="center",
        ).pack(pady=30)

    
    def _get_drafts_dir(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "drafts")
    

    def _load_drafts(self):
        import datetime as _dt
        drafts_dir = self._get_drafts_dir()
        if not os.path.isdir(drafts_dir):
            return []

        drafts = []
        for filename in sorted(os.listdir(drafts_dir)):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(drafts_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                name = (
                    data.get("general", {}).get("optimization_name")
                    or filename.replace(".json", "").replace("_", " ")
                )
                saved_at_raw = data.get("meta", {}).get("saved_at", "")
                try:
                    dt = _dt.datetime.fromisoformat(saved_at_raw)
                    saved_at = dt.strftime("%Y-%m-%d")
                except Exception:
                    saved_at = saved_at_raw or "—"

                start_date = data.get("general", {}).get("start_date", "—")
                status     = data.get("meta", {}).get("status", "draft").capitalize()

                drafts.append({
                    "name":       name,
                    "saved_at":   saved_at,
                    "start_date": start_date,
                    "status":     status,
                    "filepath":   filepath,
                    "raw":        data,
                })
            except (json.JSONDecodeError, OSError):
                continue

        return drafts


    def _on_load_click(self, draft: dict):
        confirmed = messagebox.askyesno(
            "Load Optimization",
            f"Load '{draft['name']}'?\n\nThis will navigate to the New Optimization "
            f"page and fill in all saved inputs.",
        )
        if not confirmed:
            return
        new_opt_frame = self.controller.frames["New_Optimizations"]
        new_opt_frame.restore_draft(draft["raw"])
        self.controller.show_page("New_Optimizations")


    def _on_delete_click(self, draft: dict):
        confirmed = messagebox.askyesno(
            "Delete Optimization",
            f"Are you sure you want to delete '{draft['name']}'?\n\n"
            f"This will permanently remove the saved file and cannot be undone.",
            icon="warning",
        )
        if not confirmed:
            return
        try:
            os.remove(draft["filepath"])
        except OSError as exc:
            messagebox.showerror("Delete Failed", f"Could not delete file:\n{exc}")
            return
        self.refresh_table()


class Settings(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.lbl_test = ttk.Label(self, text="Settings Page Loaded Successfully")
        self.lbl_test.pack(side="top")


class Main_App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RouteForge")
        self.geometry("600x400")
        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand=True) 

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        for Page_Class in (Inital_Screen, New_Optimizations, Load_Optimizations, Settings, Results):
            frame = Page_Class(parent=container, controller=self) 
            self.frames[Page_Class.__name__] = frame 
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_page("Inital_Screen")

        self.style = ttk.Style(theme="morph")
        

    def show_page(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

if __name__ == "__main__":
    app = Main_App()
    app.mainloop()






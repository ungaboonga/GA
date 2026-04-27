import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import json
import re
import math
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkcalendar import DateEntry

import database as db

class VarDialog(tk.Toplevel):
    def __init__(self, parent, title="Добавить переменную", var_data=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("550x580")
        self.parent = parent
        self.var_data = var_data
        self.result = None
        all_vars = db.get_variables()
        self.groups = [(v[0], v[1]) for v in all_vars if v[2] == 'group']
        if var_data and var_data[2] == 'group':
            self.groups = [g for g in self.groups if g[0] != var_data[0]]
        self.group_names = [""] + [f"{name} (id{id})" for id, name in self.groups]
        row = 0
        ttk.Label(self, text="Имя:").grid(row=row, column=0, padx=5, pady=5, sticky='e')
        self.entry_name = ttk.Entry(self, width=30)
        self.entry_name.grid(row=row, column=1, padx=5, pady=5, columnspan=2)
        row += 1
        ttk.Label(self, text="Тип:").grid(row=row, column=0, padx=5, pady=5, sticky='e')
        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(self, textvariable=self.type_var,
                                        values=['number', 'text', 'boolean', 'date', 'list', 'group'],
                                        state='readonly')
        self.type_combo.grid(row=row, column=1, padx=5, pady=5, sticky='w')
        self.type_combo.bind('<<ComboboxSelected>>', self.on_type_change)
        row += 1
        ttk.Label(self, text="Родительская группа:").grid(row=row, column=0, padx=5, pady=5, sticky='e')
        self.parent_var = tk.StringVar()
        self.parent_combo = ttk.Combobox(self, textvariable=self.parent_var, values=self.group_names, state='readonly')
        self.parent_combo.grid(row=row, column=1, padx=5, pady=5, sticky='w')
        row += 1
        self.formula_label = ttk.Label(self, text="Формула (опционально):")
        self.formula_label.grid(row=row, column=0, padx=5, pady=5, sticky='e')
        self.entry_formula = ttk.Entry(self, width=40)
        self.entry_formula.grid(row=row, column=1, padx=5, pady=5, columnspan=2)
        self.tooltip = tk.Label(self, text="Пример: v1 + v2*2, math.sin(v1). Доступны v1,v2,... и модуль math", 
                                 fg="gray", font=("Arial", 8))
        self.tooltip.grid(row=row+1, column=1, columnspan=2, sticky='w', padx=5)
        self.tooltip.grid_remove()
        def on_focus_in(event):
            self.tooltip.grid()
        def on_focus_out(event):
            self.tooltip.grid_remove()
        self.entry_formula.bind("<FocusIn>", on_focus_in)
        self.entry_formula.bind("<FocusOut>", on_focus_out)
        row += 2
        self.condition_label = ttk.Label(self, text="Условие (например v1>10):")
        self.condition_label.grid(row=row, column=0, padx=5, pady=5, sticky='e')
        self.entry_condition = ttk.Entry(self, width=40)
        self.entry_condition.grid(row=row, column=1, padx=5, pady=5, columnspan=2)
        row += 1
        self.actions_label = ttk.Label(self, text="Действия (JSON, например {'v2':'=v1+5'}):")
        self.actions_label.grid(row=row, column=0, padx=5, pady=5, sticky='ne')
        self.text_actions = tk.Text(self, height=4, width=40)
        self.text_actions.grid(row=row, column=1, padx=5, pady=5, columnspan=2)
        row += 1
        self.sequence_label = ttk.Label(self, text="Последовательность (через запятую, операции: +2, *3, =10):")
        self.sequence_label.grid(row=row, column=0, padx=5, pady=5, sticky='e')
        self.entry_sequence = ttk.Entry(self, width=40)
        self.entry_sequence.grid(row=row, column=1, padx=5, pady=5, columnspan=2)
        row += 1
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="OK", command=self.ok).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Отмена", command=self.cancel).pack(side='left', padx=5)
        self.hide_unused_fields()
        if var_data:
            self.entry_name.insert(0, var_data[1])
            self.type_var.set(var_data[2])
            self.entry_formula.insert(0, var_data[3] or '')
            self.entry_condition.insert(0, var_data[4] or '')
            if var_data[5]:
                try:
                    actions = json.loads(var_data[5])
                    self.text_actions.insert('1.0', json.dumps(actions, indent=2))
                except:
                    pass
            self.entry_sequence.insert(0, var_data[6] or '')
            if var_data[7]:
                for id, name in self.groups:
                    if id == var_data[7]:
                        self.parent_var.set(f"{name} (id{id})")
                        break
            self.on_type_change()
    
    def hide_unused_fields(self):
        typ = self.type_var.get()
        if typ == 'number':
            self.formula_label.grid()
            self.entry_formula.grid()
        else:
            self.formula_label.grid_remove()
            self.entry_formula.grid_remove()
            self.tooltip.grid_remove()
        if typ == 'boolean':
            self.condition_label.grid()
            self.entry_condition.grid()
            self.actions_label.grid()
            self.text_actions.grid()
        else:
            self.condition_label.grid_remove()
            self.entry_condition.grid_remove()
            self.actions_label.grid_remove()
            self.text_actions.grid_remove()
        if typ == 'list':
            self.sequence_label.grid()
            self.entry_sequence.grid()
        else:
            self.sequence_label.grid_remove()
            self.entry_sequence.grid_remove()
    
    def on_type_change(self, event=None):
        self.hide_unused_fields()
    
    def ok(self):
        name = self.entry_name.get().strip()
        typ = self.type_var.get()
        if not name or not typ:
            messagebox.showerror("Ошибка", "Заполните имя и тип")
            return
        parent_id = None
        parent_text = self.parent_var.get()
        if parent_text and parent_text.strip():
            match = re.search(r'id(\d+)', parent_text)
            if match:
                parent_id = int(match.group(1))
        formula = self.entry_formula.get().strip() if typ == 'number' else None
        condition = self.entry_condition.get().strip() if typ == 'boolean' else None
        sequence = self.entry_sequence.get().strip() if typ == 'list' else None
        actions = None
        if typ == 'boolean':
            actions_text = self.text_actions.get('1.0', tk.END).strip()
            if actions_text:
                try:
                    actions = json.loads(actions_text)
                except:
                    messagebox.showerror("Ошибка", "Действия должны быть в формате JSON")
                    return
        self.result = (name, typ, formula, condition, actions, sequence, parent_id)
        self.destroy()
    
    def cancel(self):
        self.result = None
        self.destroy()

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Анализатор партий настольных игр")
        self.root.geometry("1200x800")
        db.init_db()
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True)
        self.frame_vars = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_vars, text="Переменные")
        self.setup_variables_tab()
        self.frame_input = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_input, text="Ввод данных")
        self.setup_input_tab()
        self.frame_analytics = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_analytics, text="Аналитика")
        self.setup_analytics_tab()
    
    def setup_variables_tab(self):
        btn_frame = ttk.Frame(self.frame_vars)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Добавить", command=self.add_var).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Изменить", command=self.edit_var).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_var).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Вверх", command=self.move_var_up).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Вниз", command=self.move_var_down).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Экспорт", command=self.export_data).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Импорт", command=self.import_data).pack(side='left', padx=5)
        self.tree_vars = ttk.Treeview(self.frame_vars, columns=('type', 'info'), show='tree headings')
        self.tree_vars.heading('#0', text='Имя')
        self.tree_vars.heading('type', text='Тип')
        self.tree_vars.heading('info', text='Доп. инфо')
        self.tree_vars.column('#0', width=300)
        self.tree_vars.column('type', width=100)
        self.tree_vars.column('info', width=300)
        self.tree_vars.pack(fill='both', expand=True, padx=5, pady=5)
        scrollbar = ttk.Scrollbar(self.tree_vars, orient='vertical', command=self.tree_vars.yview)
        self.tree_vars.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.refresh_vars_tree()
    
    def refresh_vars_tree(self):
        for item in self.tree_vars.get_children():
            self.tree_vars.delete(item)
        tree = db.get_variables_tree()
        self._insert_nodes('', tree)
    
    def _insert_nodes(self, parent, nodes):
        for node in nodes:
            info = ""
            if node['type'] == 'number' and node['formula']:
                info = f"формула: {node['formula']}"
            elif node['type'] == 'boolean' and node['condition']:
                info = f"условие: {node['condition']}"
            elif node['type'] == 'list' and node['sequence']:
                info = f"последовательность: {node['sequence']}"
            item_id = self.tree_vars.insert(parent, 'end', iid=str(node['id']), text=node['name'],
                                            values=(node['type'], info))
            if node['children']:
                self._insert_nodes(item_id, node['children'])
    
    def add_var(self):
        dlg = VarDialog(self.root, "Добавить переменную")
        self.root.wait_window(dlg)
        if dlg.result:
            name, typ, formula, condition, actions, sequence, parent_id = dlg.result
            db.add_variable(name, typ, formula, condition, actions, sequence, parent_id)
            self.refresh_vars_tree()
            self.refresh_input_form()
            self.refresh_analytics_vars()
    
    def edit_var(self):
        selected = self.tree_vars.selection()
        if not selected:
            return
        var_id = int(selected[0])
        all_vars = db.get_variables(include_deleted=False)
        for v in all_vars:
            if v[0] == var_id:
                dlg = VarDialog(self.root, "Изменить переменную", var_data=v[:8])
                self.root.wait_window(dlg)
                if dlg.result:
                    new_name, new_typ, new_formula, new_cond, new_actions, new_seq, new_parent = dlg.result
                    db.update_variable(var_id, new_name, new_typ, new_formula, new_cond, new_actions, new_seq, new_parent)
                    self.refresh_vars_tree()
                    self.refresh_input_form()
                    self.refresh_analytics_vars()
                break
    
    def delete_var(self):
        selected = self.tree_vars.selection()
        if not selected:
            return
        if messagebox.askyesno("Подтверждение", "Удалить выбранную переменную?"):
            var_id = int(selected[0])
            db.delete_variable(var_id)
            self.refresh_vars_tree()
            self.refresh_input_form()
            self.refresh_analytics_vars()
    
    def move_var_up(self):
        selected = self.tree_vars.selection()
        if not selected:
            return
        var_id = int(selected[0])
        conn = sqlite3.connect(db.DB_NAME)
        c = conn.cursor()
        c.execute("SELECT parent_id FROM variables WHERE id=?", (var_id,))
        row = c.fetchone()
        conn.close()
        parent_id = row[0] if row else None
        siblings = db.get_variables_by_parent(parent_id)
        idx = next((i for i, (sid, _) in enumerate(siblings) if sid == var_id), None)
        if idx is None or idx == 0:
            return
        prev_id = siblings[idx-1][0]
        db.swap_orders(var_id, prev_id)
        self.refresh_vars_tree()
        self.tree_vars.selection_set(str(var_id))
    
    def move_var_down(self):
        selected = self.tree_vars.selection()
        if not selected:
            return
        var_id = int(selected[0])
        conn = sqlite3.connect(db.DB_NAME)
        c = conn.cursor()
        c.execute("SELECT parent_id FROM variables WHERE id=?", (var_id,))
        row = c.fetchone()
        conn.close()
        parent_id = row[0] if row else None
        siblings = db.get_variables_by_parent(parent_id)
        idx = next((i for i, (sid, _) in enumerate(siblings) if sid == var_id), None)
        if idx is None or idx == len(siblings)-1:
            return
        next_id = siblings[idx+1][0]
        db.swap_orders(var_id, next_id)
        self.refresh_vars_tree()
        self.tree_vars.selection_set(str(var_id))
    
    def export_data(self):
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not filename:
            return
        all_vars = db.get_variables(include_deleted=False)
        vars_export = [list(v) for v in all_vars]
        games = db.get_all_games()
        data = {
            "version": 2,
            "variables": vars_export,
            "games": games
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Экспорт", f"Данные сохранены в {filename}")
    
    def import_data(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not filename:
            return
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not messagebox.askyesno("Импорт", "Это заменит все текущие данные. Продолжить?"):
            return
        db.clear_all_data()
        db.import_variables(data['variables'])
        db.import_games(data['games'])
        self.refresh_vars_tree()
        self.refresh_input_form()
        self.refresh_analytics_vars()
        messagebox.showinfo("Импорт", "Данные успешно импортированы")
    
    def setup_input_tab(self):
        self.input_canvas = tk.Canvas(self.frame_input)
        self.input_scrollbar = ttk.Scrollbar(self.frame_input, orient='vertical', command=self.input_canvas.yview)
        self.input_scrollable_frame = ttk.Frame(self.input_canvas)
        self.input_scrollable_frame.bind("<Configure>", lambda e: self.input_canvas.configure(scrollregion=self.input_canvas.bbox("all")))
        self.input_canvas.create_window((0,0), window=self.input_scrollable_frame, anchor='nw')
        self.input_canvas.configure(yscrollcommand=self.input_scrollbar.set)
        self.input_canvas.pack(side='left', fill='both', expand=True)
        self.input_scrollbar.pack(side='right', fill='y')
        self.step_frame = ttk.Frame(self.frame_input)
        self.step_frame.pack(side='top', fill='x', padx=5, pady=5)
        ttk.Button(self.step_frame, text="-1 ход", command=self.prev_step).pack(side='left', padx=5)
        self.step_label = ttk.Label(self.step_frame, text="Ход: 1")
        self.step_label.pack(side='left', padx=5)
        ttk.Button(self.step_frame, text="+1 ход", command=self.next_step).pack(side='left', padx=5)
        ttk.Button(self.step_frame, text="Сохранить партию", command=self.save_game).pack(side='right', padx=5)
        self.current_step = 0
        self.step_values = {}
        self.input_widgets = {}
        self.refresh_input_form()
    
    def refresh_input_form(self):
        for widget in self.input_scrollable_frame.winfo_children():
            widget.destroy()
        self.input_widgets = {}
        tree = db.get_variables_tree()
        for node in tree:
            self._build_input_frame(self.input_scrollable_frame, node)
        self.current_step = 0
        self.step_values = {}
        self.step_label.config(text=f"Ход: {self.current_step+1}")
        self.load_current_step()
    
    def _build_input_frame(self, parent, node):
        if node['type'] == 'group':
            group_frame = ttk.LabelFrame(parent, text=node['name'])
            group_frame.pack(fill='x', pady=5, padx=5)
            for child in node['children']:
                self._build_input_frame(group_frame, child)
        else:
            frame = ttk.Frame(parent)
            frame.pack(fill='x', pady=2, padx=10)
            ttk.Label(frame, text=node['name']+':').pack(side='left', padx=5)
            var_id = node['id']
            typ = node['type']
            if typ == 'number':
                entry = ttk.Entry(frame)
                entry.pack(side='left', fill='x', expand=True)
                self.input_widgets[var_id] = ('number', entry)
            elif typ == 'text':
                entry = ttk.Entry(frame)
                entry.pack(side='left', fill='x', expand=True)
                self.input_widgets[var_id] = ('text', entry)
            elif typ == 'boolean':
                var_bool = tk.BooleanVar()
                check = ttk.Checkbutton(frame, variable=var_bool)
                check.pack(side='left')
                self.input_widgets[var_id] = ('boolean', var_bool)
            elif typ == 'date':
                date_label = ttk.Label(frame, text="автоматически")
                date_label.pack(side='left')
                self.input_widgets[var_id] = ('date', None)
            elif typ == 'list':
                entry = ttk.Entry(frame)
                entry.pack(side='left', fill='x', expand=True)
                self.input_widgets[var_id] = ('list', entry)
    
    def load_current_step(self):
        for var_id, (typ, widget) in self.input_widgets.items():
            if typ == 'date':
                continue
            if var_id in self.step_values and self.current_step < len(self.step_values[var_id]):
                val = self.step_values[var_id][self.current_step]
                if typ == 'boolean':
                    widget.set(val == 'True' or val == '1')
                else:
                    widget.delete(0, tk.END)
                    widget.insert(0, str(val))
            else:
                if typ == 'boolean':
                    widget.set(False)
                elif widget:
                    widget.delete(0, tk.END)
                    widget.insert(0, "")
    
    def update_step_values(self):
        for var_id, (typ, widget) in self.input_widgets.items():
            if typ == 'date':
                continue
            if var_id not in self.step_values:
                self.step_values[var_id] = []
            while len(self.step_values[var_id]) <= self.current_step:
                self.step_values[var_id].append(None)
            if typ == 'boolean':
                val = '1' if widget.get() else '0'
            else:
                val = widget.get().strip()
            self.step_values[var_id][self.current_step] = val
    
    def next_step(self):
        self.update_step_values()
        self.current_step += 1
        for var_id in self.step_values:
            while len(self.step_values[var_id]) <= self.current_step:
                new_val = self.compute_next_value(var_id, self.current_step)
                self.step_values[var_id].append(new_val)
        self.step_label.config(text=f"Ход: {self.current_step+1}")
        self.load_current_step()
    
    def prev_step(self):
        if self.current_step > 0:
            self.update_step_values()
            self.current_step -= 1
            self.step_label.config(text=f"Ход: {self.current_step+1}")
            self.load_current_step()
    
    def compute_next_value(self, var_id, step):
        all_vars = db.get_variables(include_deleted=False)
        var = next((v for v in all_vars if v[0] == var_id), None)
        if not var:
            return ""
        typ = var[2]
        if typ == 'number' and var[3]:
            namespace = {'math': math}
            for other_id, vals in self.step_values.items():
                prev_val = vals[step-1] if step-1 < len(vals) else (vals[-1] if vals else 0)
                try:
                    namespace[f'v{other_id}'] = float(prev_val) if prev_val else 0
                except:
                    namespace[f'v{other_id}'] = 0
            try:
                result = eval(var[3], {"__builtins__": {}}, namespace)
                return str(result)
            except:
                return "0"
        elif typ == 'list' and var[6]:
            seq_str = var[6]
            parts = [p.strip() for p in seq_str.split(',')]
            values = []
            current = None
            for p in parts:
                if p.startswith('+'):
                    if current is None:
                        current = 0
                    current += float(p[1:])
                elif p.startswith('*'):
                    if current is None:
                        current = 1
                    current *= float(p[1:])
                elif p.startswith('='):
                    current = float(p[1:])
                else:
                    current = float(p)
                values.append(current)
            if step < len(values):
                return str(values[step])
            else:
                return str(values[-1]) if values else "0"
        elif typ == 'boolean' and var[4]:
            namespace = {'math': math}
            for other_id, vals in self.step_values.items():
                prev_val = vals[step-1] if step-1 < len(vals) else (vals[-1] if vals else 0)
                try:
                    namespace[f'v{other_id}'] = float(prev_val) if prev_val else 0
                except:
                    namespace[f'v{other_id}'] = 0
            try:
                cond = eval(var[4], {"__builtins__": {}}, namespace)
                if cond:
                    actions = json.loads(var[5]) if var[5] else {}
                    for target_var_id, expr in actions.items():
                        try:
                            new_val = eval(expr, {"__builtins__": {}}, namespace)
                            if target_var_id not in self.step_values:
                                self.step_values[target_var_id] = []
                            while len(self.step_values[target_var_id]) <= step:
                                self.step_values[target_var_id].append(None)
                            self.step_values[target_var_id][step] = str(new_val)
                        except:
                            pass
                return '1' if cond else '0'
            except:
                return '0'
        return ""
    
    def save_game(self):
        self.update_step_values()
        if not self.step_values:
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения")
            return
        steps_count = max(len(vals) for vals in self.step_values.values())
        values_dict = {}
        for var_id, vals in self.step_values.items():
            while len(vals) < steps_count:
                vals.append("")
            values_dict[var_id] = vals
        game_id = db.save_game(values_dict, steps_count)
        messagebox.showinfo("Сохранено", f"Партия #{game_id} сохранена ({steps_count} ходов)")
        self.step_values = {}
        self.current_step = 0
        self.refresh_input_form()
    
    def setup_analytics_tab(self):
        control_frame = ttk.Frame(self.frame_analytics)
        control_frame.pack(side='top', fill='x', padx=5, pady=5)
        ttk.Label(control_frame, text="X (номер хода или переменная):").grid(row=0, column=0)
        self.x_combo = ttk.Combobox(control_frame, state='readonly', width=25)
        self.x_combo.grid(row=0, column=1, padx=5)
        ttk.Label(control_frame, text="Y:").grid(row=1, column=0)
        self.y_combo = ttk.Combobox(control_frame, state='readonly', width=25)
        self.y_combo.grid(row=1, column=1, padx=5)
        ttk.Label(control_frame, text="Тип графика:").grid(row=2, column=0)
        self.chart_type = tk.StringVar(value='line')
        chart_combo = ttk.Combobox(control_frame, textvariable=self.chart_type,
                                    values=['line', 'scatter', 'bar'], state='readonly', width=10)
        chart_combo.grid(row=2, column=1, sticky='w', padx=5)
        ttk.Button(control_frame, text="Построить", command=self.plot_graph).grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(control_frame, text="Очистить графики", command=self.clear_plots).grid(row=4, column=0, columnspan=2)
        self.plot_notebook = ttk.Notebook(self.frame_analytics)
        self.plot_notebook.pack(fill='both', expand=True, padx=5, pady=5)
        self.plot_notebook.bind("<MouseWheel>", self.on_mousewheel)
        self.refresh_analytics_vars()
    
    def refresh_analytics_vars(self):
        vars_list = db.get_variables()
        names = ["Номер хода"] + [f"{v[1]} (id{v[0]})" for v in vars_list]
        self.x_combo['values'] = names
        self.y_combo['values'] = names
    
    def on_mousewheel(self, event):
        delta = -1 if event.delta > 0 else 1
        current = self.plot_notebook.index(self.plot_notebook.select())
        new_index = (current + delta) % self.plot_notebook.index('end')
        self.plot_notebook.select(new_index)
    
    def clear_plots(self):
        for tab in self.plot_notebook.tabs():
            self.plot_notebook.forget(tab)
    
    def plot_graph(self):
        x_text = self.x_combo.get()
        y_text = self.y_combo.get()
        if not x_text or not y_text:
            messagebox.showwarning("Предупреждение", "Выберите X и Y")
            return
        use_step = (x_text == "Номер хода")
        if use_step:
            match_y = re.search(r'id(\d+)', y_text)
            if not match_y:
                messagebox.showerror("Ошибка", "Не удалось определить Y")
                return
            y_id = int(match_y.group(1))
            values = db.get_values_for_variable(y_id)
            step_values = {}
            for _, step, val in values:
                try:
                    num = float(val)
                except:
                    continue
                step_values.setdefault(step, []).append(num)
            if not step_values:
                messagebox.showinfo("Нет данных", "Нет числовых данных для выбранной переменной")
                return
            x_vals = sorted(step_values.keys())
            y_vals = [sum(step_values[s])/len(step_values[s]) for s in x_vals]
            title = f"Зависимость {y_text} от хода (среднее по партиям)"
        else:
            match_x = re.search(r'id(\d+)', x_text)
            match_y = re.search(r'id(\d+)', y_text)
            if not match_x or not match_y:
                messagebox.showerror("Ошибка", "Не удалось определить ID переменных")
                return
            x_id = int(match_x.group(1))
            y_id = int(match_y.group(1))
            x_vals_all = db.get_values_for_variable(x_id)
            y_vals_all = db.get_values_for_variable(y_id)
            x_dict = {(gid, step): val for (gid, step, val) in x_vals_all}
            y_dict = {(gid, step): val for (gid, step, val) in y_vals_all}
            common = set(x_dict.keys()) & set(y_dict.keys())
            points = []
            for key in common:
                try:
                    x = float(x_dict[key])
                    y = float(y_dict[key])
                    points.append((x, y))
                except:
                    continue
            if not points:
                messagebox.showinfo("Нет данных", "Нет числовых точек")
                return
            points.sort(key=lambda p: p[0])
            x_vals = [p[0] for p in points]
            y_vals = [p[1] for p in points]
            title = f"{y_text} от {x_text}"
        tab = ttk.Frame(self.plot_notebook)
        self.plot_notebook.add(tab, text=f"График {len(self.plot_notebook.tabs())+1}")
        fig = Figure(figsize=(8,5), dpi=100)
        ax = fig.add_subplot(111)
        chart = self.chart_type.get()
        if chart == 'line':
            ax.plot(x_vals, y_vals, marker='o', color='blue')
        elif chart == 'scatter':
            ax.scatter(x_vals, y_vals, color='blue')
        elif chart == 'bar':
            ax.bar(range(len(x_vals)), y_vals, tick_label=[str(round(x,2)) for x in x_vals])
        ax.set_xlabel(x_text)
        ax.set_ylabel(y_text)
        ax.set_title(title)
        ax.grid(True)
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()

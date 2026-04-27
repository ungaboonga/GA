import sqlite3
import json

DB_NAME = "stats.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS variables (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    parent_id INTEGER,
                    deleted INTEGER DEFAULT 0,
                    order_idx INTEGER DEFAULT 0,
                    FOREIGN KEY (parent_id) REFERENCES variables(id)
                )''')
    c.execute("PRAGMA table_info(variables)")
    existing = [col[1] for col in c.fetchall()]
    if 'formula' not in existing:
        c.execute("ALTER TABLE variables ADD COLUMN formula TEXT")
    if 'condition' not in existing:
        c.execute("ALTER TABLE variables ADD COLUMN condition TEXT")
    if 'actions' not in existing:
        c.execute("ALTER TABLE variables ADD COLUMN actions TEXT")
    if 'sequence' not in existing:
        c.execute("ALTER TABLE variables ADD COLUMN sequence TEXT")
    c.execute('''CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    step_number INTEGER NOT NULL,
                    variable_id INTEGER NOT NULL,
                    value TEXT,
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
                    FOREIGN KEY (variable_id) REFERENCES variables(id) ON DELETE CASCADE
                )''')
    conn.commit()
    conn.close()

def get_max_order():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT MAX(order_idx) FROM variables")
    max_order = c.fetchone()[0]
    conn.close()
    return max_order if max_order is not None else 0

def swap_orders(id1, id2):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT order_idx FROM variables WHERE id=?", (id1,))
    order1 = c.fetchone()[0]
    c.execute("SELECT order_idx FROM variables WHERE id=?", (id2,))
    order2 = c.fetchone()[0]
    c.execute("UPDATE variables SET order_idx=? WHERE id=?", (order2, id1))
    c.execute("UPDATE variables SET order_idx=? WHERE id=?", (order1, id2))
    conn.commit()
    conn.close()

def get_variables(include_deleted=False):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if include_deleted:
        c.execute("SELECT id, name, type, formula, condition, actions, sequence, parent_id, order_idx FROM variables ORDER BY order_idx")
    else:
        c.execute("SELECT id, name, type, formula, condition, actions, sequence, parent_id, order_idx FROM variables WHERE deleted=0 ORDER BY order_idx")
    rows = c.fetchall()
    conn.close()
    return rows

def get_variables_tree():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, type, formula, condition, actions, sequence, parent_id FROM variables WHERE deleted=0 ORDER BY order_idx")
    rows = c.fetchall()
    conn.close()
    nodes = {}
    for row in rows:
        node_id, name, typ, formula, condition, actions, sequence, parent_id = row
        nodes[node_id] = {
            'id': node_id,
            'name': name,
            'type': typ,
            'formula': formula,
            'condition': condition,
            'actions': actions,
            'sequence': sequence,
            'parent_id': parent_id,
            'children': []
        }
    tree = []
    for node_id, node in nodes.items():
        if node['parent_id'] is None:
            tree.append(node)
        else:
            if node['parent_id'] in nodes:
                nodes[node['parent_id']]['children'].append(node)
    return tree

def get_variables_by_parent(parent_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, order_idx FROM variables WHERE deleted=0 AND parent_id IS ? ORDER BY order_idx", (parent_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def add_variable(name, var_type, formula=None, condition=None, actions=None, sequence=None, parent_id=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    max_order = get_max_order() + 1
    actions_json = json.dumps(actions) if actions else None
    c.execute("""INSERT INTO variables 
                 (name, type, formula, condition, actions, sequence, parent_id, order_idx)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (name, var_type, formula, condition, actions_json, sequence, parent_id, max_order))
    conn.commit()
    conn.close()

def delete_variable(var_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE variables SET deleted=1 WHERE id=?", (var_id,))
    conn.commit()
    conn.close()

def update_variable(var_id, name, var_type, formula=None, condition=None, actions=None, sequence=None, parent_id=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    actions_json = json.dumps(actions) if actions else None
    c.execute("""UPDATE variables 
                 SET name=?, type=?, formula=?, condition=?, actions=?, sequence=?, parent_id=?
                 WHERE id=?""",
              (name, var_type, formula, condition, actions_json, sequence, parent_id, var_id))
    conn.commit()
    conn.close()

def save_game(values_dict, steps_count):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO games DEFAULT VALUES")
    game_id = c.lastrowid
    for step in range(steps_count):
        for var_id, step_values in values_dict.items():
            if step < len(step_values):
                value = str(step_values[step])
                c.execute("INSERT INTO steps (game_id, step_number, variable_id, value) VALUES (?, ?, ?, ?)",
                          (game_id, step, var_id, value))
    conn.commit()
    conn.close()
    return game_id

def get_all_games():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, timestamp FROM games ORDER BY timestamp")
    games = c.fetchall()
    result = []
    for game in games:
        game_id, ts = game
        c.execute("SELECT step_number, variable_id, value FROM steps WHERE game_id=? ORDER BY step_number", (game_id,))
        steps = {}
        for step, var_id, val in c.fetchall():
            if step not in steps:
                steps[step] = {}
            steps[step][var_id] = val
        result.append({
            'id': game_id,
            'timestamp': ts,
            'steps': steps
        })
    conn.close()
    return result

def get_values_for_variable(var_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT game_id, step_number, value FROM steps WHERE variable_id=? ORDER BY game_id, step_number", (var_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def clear_all_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM steps")
    c.execute("DELETE FROM games")
    c.execute("DELETE FROM variables")
    c.execute("DELETE FROM sqlite_sequence WHERE name='variables'")
    c.execute("DELETE FROM sqlite_sequence WHERE name='games'")
    c.execute("DELETE FROM sqlite_sequence WHERE name='steps'")
    conn.commit()
    conn.close()

def import_variables(vars_list):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    for var in vars_list:
        c.execute("""INSERT INTO variables 
                     (id, name, type, formula, condition, actions, sequence, parent_id, order_idx)
                     VALUES (?,?,?,?,?,?,?,?,?)""", var)
    conn.commit()
    conn.close()

def import_games(games_list):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    for game in games_list:
        c.execute("INSERT INTO games (id, timestamp) VALUES (?, ?)", (game['id'], game['timestamp']))
        for step, step_data in game['steps'].items():
            for var_id, val in step_data.items():
                c.execute("INSERT INTO steps (game_id, step_number, variable_id, value) VALUES (?, ?, ?, ?)",
                          (game['id'], step, var_id, val))
    conn.commit()
    conn.close()

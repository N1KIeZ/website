import tkinter as tk
from tkinter import ttk
import json
import os
import secrets
import sys
import urllib.request
import urllib.error
import time

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'keys_db.json')
BANNED_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'banned_keys.json')
LOCAL_CONFIG = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), '.banned_local.json')
SITE_CONFIG = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'banned_config.json')
_CH  = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

ACCENT = '#e91e8c'
ACCENT_HOVER = '#c4186e'
BG = '#0d090c'
BG2 = '#150e12'
BG3 = '#1e141a'
FG = '#e8e0e6'
FG_DIM = '#9c8d96'
FONT_MONO = ('Consolas', 10, 'normal')
FONT_SUB = ('Segoe UI', 9, 'normal')

STATIC_N = 59596791868544965917715049293139712060670803368525004046780554740535049298561
STATIC_D = 44411372526603278231981439147021640563272121446936530565914521287135611291649

DURATIONS = {
    'lifetime': None,
    '1 week': 7 * 24 * 60 * 60,
    '1 month': 30 * 24 * 60 * 60,
}

def b32_encode(data):
    bits = "".join(f"{b:08b}" for b in data)
    padding = (5 - len(bits) % 5) % 5
    bits += "0" * padding
    return "".join(_CH[int(bits[i:i+5], 2)] for i in range(0, len(bits), 5))

def _h(s):
    h = 0
    for c in s:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFFFFFFFFFF
    return h

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    db = {'active': [], 'banned': []}
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)
    return db

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)
    ban_list = []
    for item in db.get('banned', []):
        if isinstance(item, dict):
            ban_list.append(item['key'])
        else:
            ban_list.append(item)
    with open(BANNED_FILE, 'w') as f:
        json.dump({'banned': ban_list}, f, indent=2)

def load_config():
    if os.path.exists(LOCAL_CONFIG):
        try:
            with open(LOCAL_CONFIG, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(cfg):
    with open(LOCAL_CONFIG, 'w') as f:
        json.dump(cfg, f, indent=2)

def gist_request(method, url, token, data=None):
    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header('Authorization', 'token ' + token)
    req.add_header('Accept', 'application/vnd.github+json')
    if body:
        req.add_header('Content-Type', 'application/json')
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read().decode('utf-8'))

def push_bans_to_gist(banned_list):
    cfg = load_config()
    token = cfg.get('github_token', '')
    gist_id = cfg.get('gist_id')

    if not token:
        return None, 'no github token set'

    ban_keys = []
    for item in banned_list:
        if isinstance(item, dict):
            ban_keys.append(item['key'])
        else:
            ban_keys.append(item)

    content = json.dumps({'banned': ban_keys}, indent=2)

    try:
        if gist_id:
            gist_request('PATCH', f'https://api.github.com/gists/{gist_id}', token, {
                'files': {'banned_keys.json': {'content': content}}
            })
            raw_url = cfg.get('raw_url', '')
        else:
            result = gist_request('POST', 'https://api.github.com/gists', token, {
                'description': 'nikita.gg banned keys',
                'public': False,
                'files': {'banned_keys.json': {'content': content}}
            })
            gist_id = result['id']
            raw_url = result['files']['banned_keys.json']['raw_url']
            cfg['gist_id'] = gist_id
            cfg['raw_url'] = raw_url
            save_config(cfg)

        if raw_url:
            with open(SITE_CONFIG, 'w') as f:
                json.dump({'cloud_url': raw_url}, f, indent=2)

        return gist_id, None
    except urllib.error.HTTPError as e:
        return None, f'github error: {e.code}'
    except Exception as e:
        return None, str(e)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('nikita.gg  |  License Key Manager')
        self.geometry('700x580')
        self.minsize(600, 480)
        self.configure(bg=BG)
        self.db = load_db()
        self._build()
        self._refresh()

    def _build(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill='x', padx=36, pady=20)
        tk.Label(header, text='nikita.gg', font=('Segoe UI', 26, 'normal'),
                 bg=BG, fg=ACCENT).pack(side='left')
        tk.Label(header, text='asymmetric license manager', font=FONT_SUB,
                 bg=BG, fg=FG_DIM).pack(side='left', padx=12, anchor='s')

        tk.Frame(self, bg=ACCENT, height=1).pack(fill='x', padx=36)

        cfg = load_config()
        self._cloud_visible = False
        cloud_frame = tk.Frame(self, bg=BG)
        cloud_frame.pack(fill='x', padx=36, pady=6)
        self.cloud_btn = tk.Button(cloud_frame, text='+ CLOUD SYNC', font=FONT_SUB,
                                    bg=BG3, fg=FG_DIM, activebackground='#2a1822',
                                    activeforeground='#fff', relief='flat',
                                    padx=12, cursor='hand2', command=self._toggle_cloud)
        self.cloud_btn.pack(side='left')

        gist_status = 'live' if cfg.get('gist_id') else 'local only'
        gist_color = '#e878b4' if cfg.get('gist_id') else FG_DIM
        self.gist_label = tk.Label(cloud_frame, text=gist_status, font=FONT_SUB,
                                    bg=BG, fg=gist_color)
        self.gist_label.pack(side='right')

        self.token_frame = tk.Frame(self, bg=BG)
        tk.Label(self.token_frame, text='github token', font=FONT_SUB, bg=BG, fg=FG_DIM).pack(side='left')
        self.token_var = tk.StringVar(value=cfg.get('github_token', ''))
        self.token_entry = tk.Entry(self.token_frame, textvariable=self.token_var, font=FONT_MONO,
                                     bg=BG3, fg=FG, insertbackground=FG, relief='flat',
                                     highlightthickness=1, highlightbackground=ACCENT, width=40)
        self.token_entry.pack(side='left', padx=10)
        tk.Button(self.token_frame, text='SAVE', font=FONT_SUB, bg=BG3, fg=FG_DIM,
                  activebackground='#2a1822', activeforeground='#fff', relief='flat',
                  padx=10, cursor='hand2', command=self._save_token).pack(side='left', padx=10)

        controls = tk.Frame(self, bg=BG)
        controls.pack(fill='x', padx=36, pady=10)

        self.qty_var = tk.IntVar(value=1)
        qf = tk.Frame(controls, bg=BG)
        qf.pack(side='left', padx=14)
        tk.Label(qf, text='quantity', font=FONT_SUB, bg=BG, fg=FG_DIM).pack(anchor='w')
        tk.Spinbox(qf, from_=1, to=100, textvariable=self.qty_var, width=5,
                   font=FONT_MONO, bg=BG3, fg=FG, insertbackground=FG,
                   buttonbackground=BG2, relief='flat',
                   highlightthickness=1, highlightbackground=ACCENT).pack()

        df = tk.Frame(controls, bg=BG)
        df.pack(side='left', padx=14)
        tk.Label(df, text='duration', font=FONT_SUB, bg=BG, fg=FG_DIM).pack(anchor='w')
        self.duration_var = tk.StringVar(value='lifetime')
        duration_menu = ttk.Combobox(df, textvariable=self.duration_var, values=list(DURATIONS.keys()),
                                      state='readonly', width=12, font=FONT_MONO)
        duration_menu.pack()

        gen_btn = tk.Button(controls, text='GENERATE', font=('Segoe UI', 9, 'normal'),
                            bg=ACCENT, fg='#fff', activebackground=ACCENT_HOVER,
                            activeforeground='#fff', relief='flat',
                            padx=18, pady=7, cursor='hand2', command=self._generate)
        gen_btn.pack(side='left', padx=10, pady=14)

        copy_btn = tk.Button(controls, text='COPY SELECTED', font=('Segoe UI', 9, 'normal'),
                             bg=BG3, fg=FG_DIM, activebackground='#2a1822',
                             activeforeground='#fff', relief='flat',
                             padx=18, pady=7, cursor='hand2', command=self._copy_selected)
        copy_btn.pack(side='left', padx=10, pady=14)

        ban_btn = tk.Button(controls, text='BAN SELECTED', font=('Segoe UI', 9, 'normal'),
                            bg=BG3, fg=FG_DIM, activebackground='#2a1822',
                            activeforeground='#fff', relief='flat',
                            padx=18, pady=7, cursor='hand2', command=self._ban_selected)
        ban_btn.pack(side='left', padx=10, pady=14)

        vframe = tk.Frame(self, bg=BG2, highlightthickness=1, highlightbackground='#2a1e26')
        vframe.pack(fill='both', expand=True, padx=36, pady=8)

        style = ttk.Style(self)
        style.theme_use('default')
        style.configure('K.Treeview', background=BG2, foreground=FG,
                        fieldbackground=BG2, font=FONT_MONO, rowheight=28, borderwidth=0)
        style.configure('K.Treeview.Heading', background=BG3, foreground=FG_DIM,
                        font=FONT_SUB, relief='flat')
        style.map('K.Treeview', background=[('selected', '#2a0e1e')],
                  foreground=[('selected', ACCENT)])

        self.tree = ttk.Treeview(vframe, columns=('key', 'duration', 'status'), show='headings',
                                 style='K.Treeview', selectmode='extended')
        self.tree.heading('key', text='license key')
        self.tree.heading('duration', text='duration')
        self.tree.heading('status', text='status')
        self.tree.column('key', width=380, anchor='w')
        self.tree.column('duration', width=100, anchor='center')
        self.tree.column('status', width=80, anchor='center')

        sb = ttk.Scrollbar(vframe, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        self.status = tk.Label(self, text='', font=FONT_SUB, bg=BG, fg=FG_DIM, anchor='w')
        self.status.pack(fill='x', padx=36, pady=14)

    def _toggle_cloud(self):
        self._cloud_visible = not self._cloud_visible
        if self._cloud_visible:
            self.token_frame.pack(fill='x', padx=36, pady=4)
            self.cloud_btn.config(text='- CLOUD SYNC')
        else:
            self.token_frame.pack_forget()
            self.cloud_btn.config(text='+ CLOUD SYNC')

    def _save_token(self):
        token = self.token_var.get().strip()
        cfg = load_config()
        cfg['github_token'] = token
        save_config(cfg)
        if token:
            self.gist_label.config(text='token saved', fg='#e878b4')
        else:
            self.gist_label.config(text='no token', fg=FG_DIM)

    def _get_entry(self, item):
        vals = self.tree.item(item, 'values')
        key = vals[0]
        duration = vals[1]
        status = vals[2]
        return key, duration, status

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.db['active']:
            if isinstance(item, dict):
                dur = item.get('duration', 'lifetime')
                self.tree.insert('', 'end', values=(item['key'], dur, 'ACTIVE'))
            else:
                self.tree.insert('', 'end', values=(item, 'lifetime', 'ACTIVE'))
        for item in self.db['banned']:
            if isinstance(item, dict):
                dur = item.get('duration', 'lifetime')
                self.tree.insert('', 'end', values=(item['key'], dur, 'BANNED'))
            else:
                self.tree.insert('', 'end', values=(item, 'lifetime', 'BANNED'))
        self.status.config(text=f"{len(self.db['active'])} active  |  {len(self.db['banned'])} banned")

    def _generate(self):
        qty = max(1, min(100, self.qty_var.get()))
        duration = self.duration_var.get()
        new_keys = []

        d = STATIC_D
        n = STATIC_N

        dur_char = {'lifetime': 'L', '1 week': 'W', '1 month': 'M'}[duration]
        prefix_chars = _CH[:-3]

        while len(new_keys) < qty:
            prefix = "".join(secrets.choice(prefix_chars) for _ in range(9))
            payload = prefix + dur_char
            h = _h(payload)
            sig = pow(h, d, n)
            sig_bytes = sig.to_bytes((sig.bit_length() + 7) // 8, byteorder='big')
            sig_b32 = b32_encode(sig_bytes)
            raw_key = payload + sig_b32
            formatted_key = "-".join(raw_key[i:i+5] for i in range(0, len(raw_key), 5))

            existing_keys = []
            for item in self.db['active']:
                existing_keys.append(item['key'] if isinstance(item, dict) else item)
            for item in self.db['banned']:
                existing_keys.append(item['key'] if isinstance(item, dict) else item)

            if formatted_key not in existing_keys and formatted_key not in new_keys:
                new_keys.append(formatted_key)

        now = int(time.time())
        for k in new_keys:
            entry = {'key': k, 'duration': duration, 'created': now}
            self.db['active'].append(entry)

        save_db(self.db)
        self._refresh()

        self.clipboard_clear()
        self.clipboard_append('\n'.join(new_keys))
        self.status.config(text=f'generated {len(new_keys)} {duration} key(s) and copied to clipboard')

    def _copy_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        keys = [self.tree.item(i, 'values')[0] for i in sel]
        self.clipboard_clear()
        self.clipboard_append('\n'.join(keys))
        self.status.config(text=f'copied {len(keys)} key(s) to clipboard')

    def _ban_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        banned_count = 0
        for i in sel:
            key, duration, status = self._get_entry(i)
            if status == 'ACTIVE':
                self.db['active'] = [x for x in self.db['active'] if (x['key'] if isinstance(x, dict) else x) != key]
                self.db['banned'].append({'key': key, 'duration': duration})
                banned_count += 1
        if banned_count > 0:
            save_db(self.db)
            self._refresh()
            self.status.config(text=f'banned {banned_count} key(s) - pushing live...')
            self.after(10, self._push_live)

    def _push_live(self):
        gist_id, err = push_bans_to_gist(self.db['banned'])
        cfg = load_config()
        if err:
            self.status.config(text=f'ban saved locally - {err}')
        else:
            if cfg.get('raw_url'):
                self.gist_label.config(text='connected', fg='#e878b4')
            self.status.config(text=f'banned key(s) pushed live - ban is active now')

if __name__ == '__main__':
    App().mainloop()

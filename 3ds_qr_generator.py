import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import qrcode
from PIL import Image, ImageTk
import os
import requests
from bs4 import BeautifulSoup
import webbrowser
import http.server
import socketserver
import threading
import socket

class LocalServerHandler(http.server.SimpleHTTPRequestHandler):
    """Handler personnalisé pour le serveur HTTP local"""
    def __init__(self, *args, directory=None, **kwargs):
        self.directory = directory
        super().__init__(*args, directory=directory, **kwargs)
    
    def log_message(self, format, *args):
        """Désactive les logs dans la console"""
        pass

class QRCodeGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("3DS QR Code Generator - Multi-serveur + Serveur Local")
        self.root.geometry("1300x850")
        self.root.configure(bg="#1a1a2e")
        
        self.games = []
        self.filtered_games = []
        self.selected_game = None
        self.qr_image = None
        
        # Serveur local
        self.server = None
        self.server_thread = None
        self.server_running = False
        self.server_port = 8000
        self.local_files_dir = os.path.join(os.getcwd(), "3ds_files")
        
        # Créer le dossier local s'il n'existe pas
        if not os.path.exists(self.local_files_dir):
            os.makedirs(self.local_files_dir)
        
        # URLs de serveurs prédéfinis
        self.preset_servers = {
            "🏠 Serveur Local": f"http://localhost:{self.server_port}",
            "Internet Archive - 3DS CIAs": "https://archive.org/download/nintendo3dscias",
            "Internet Archive - 3DS Complete": "https://archive.org/download/3ds-complete-collection",
            "Internet Archive - No-Intro": "https://archive.org/download/no-intro_20200517",
            "Personnalisé": ""
        }
        
        self.current_url = ""
        
        # Créer l'interface
        self.create_widgets()
        
        # Bind pour redimensionner le QR code quand la fenêtre change
        self.root.bind('<Configure>', self.on_window_resize)
        
        # Gérer la fermeture de la fenêtre
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_window_resize(self, event):
        """Redimensionne le QR code quand la fenêtre est redimensionnée"""
        if self.selected_game and hasattr(self, 'qr_canvas'):
            # Attendre un peu pour éviter trop de redimensionnements
            if hasattr(self, '_resize_timer'):
                self.root.after_cancel(self._resize_timer)
            self._resize_timer = self.root.after(300, self.generate_qr_code)
    
    def get_local_ip(self):
        """Obtient l'adresse IP locale"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def start_local_server(self):
        """Démarre le serveur HTTP local"""
        if self.server_running:
            messagebox.showinfo("Info", "Le serveur est déjà en cours d'exécution")
            return
        
        try:
            # Créer le handler avec le répertoire
            handler = lambda *args, **kwargs: LocalServerHandler(
                *args, directory=self.local_files_dir, **kwargs
            )
            
            # Créer le serveur
            self.server = socketserver.TCPServer(("", self.server_port), handler)
            
            # Démarrer le serveur dans un thread
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            self.server_running = True
            self.start_server_btn.config(text="🛑 Arrêter le serveur", bg="#e74c3c")
            
            local_ip = self.get_local_ip()
            msg = f"✅ Serveur démarré !\n\n"
            msg += f"📍 Adresse locale: http://localhost:{self.server_port}\n"
            msg += f"🌐 Adresse réseau: http://{local_ip}:{self.server_port}\n\n"
            msg += f"📁 Dossier: {self.local_files_dir}\n\n"
            msg += "Utilisez l'adresse réseau pour accéder depuis votre 3DS !"
            
            messagebox.showinfo("Serveur démarré", msg)
            self.server_status_label.config(
                text=f"🟢 Serveur actif sur http://{local_ip}:{self.server_port}",
                fg="#27ae60"
            )
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de démarrer le serveur:\n{str(e)}")
    
    def stop_local_server(self):
        """Arrête le serveur HTTP local"""
        if not self.server_running:
            messagebox.showinfo("Info", "Le serveur n'est pas en cours d'exécution")
            return
        
        try:
            self.server.shutdown()
            self.server.server_close()
            self.server_running = False
            self.start_server_btn.config(text="🚀 Démarrer le serveur local", bg="#27ae60")
            self.server_status_label.config(text="🔴 Serveur arrêté", fg="#e74c3c")
            messagebox.showinfo("Serveur arrêté", "Le serveur local a été arrêté")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'arrêt du serveur:\n{str(e)}")
    
    def toggle_server(self):
        """Active/désactive le serveur"""
        if self.server_running:
            self.stop_local_server()
        else:
            self.start_local_server()
    
    def add_file_to_server(self):
        """Ajoute un fichier au serveur local"""
        filenames = filedialog.askopenfilenames(
            title="Sélectionnez des fichiers 3DS",
            filetypes=[
                ("Fichiers 3DS", "*.cia;*.3ds;*.3dsx"),
                ("Archives", "*.zip;*.7z;*.rar"),
                ("Tous les fichiers", "*.*")
            ]
        )
        
        if filenames:
            copied = 0
            for filepath in filenames:
                try:
                    import shutil
                    filename = os.path.basename(filepath)
                    dest = os.path.join(self.local_files_dir, filename)
                    
                    if os.path.exists(dest):
                        if not messagebox.askyesno("Fichier existant", f"{filename} existe déjà.\nRemplacer ?"):
                            continue
                    
                    shutil.copy2(filepath, dest)
                    copied += 1
                except Exception as e:
                    messagebox.showerror("Erreur", f"Erreur lors de la copie de {filename}:\n{str(e)}")
            
            if copied > 0:
                messagebox.showinfo("Succès", f"{copied} fichier(s) ajouté(s) au serveur local !")
                # Recharger si on affiche déjà les fichiers locaux
                if "localhost" in self.url_entry.get():
                    self.load_local_files()
    
    def load_local_files(self):
        """Charge les fichiers du serveur local"""
        try:
            self.games = []
            
            # Lister les fichiers dans le dossier
            valid_extensions = ['.cia', '.3ds', '.3dsx', '.zip', '.7z', '.rar']
            
            for filename in os.listdir(self.local_files_dir):
                if any(filename.lower().endswith(ext) for ext in valid_extensions):
                    # Nettoyer le nom
                    name = filename
                    for ext in valid_extensions:
                        if name.lower().endswith(ext):
                            name = name[:-len(ext)]
                            break
                    
                    name = name.replace('_', ' ').replace('-', ' ')
                    
                    # URL de téléchargement
                    local_ip = self.get_local_ip()
                    download_url = f"http://{local_ip}:{self.server_port}/{filename}"
                    
                    # Extraire région
                    region = 'Unknown'
                    if any(x in name.upper() for x in ['(USA)', '[USA]', 'USA']):
                        region = 'USA'
                    elif any(x in name.upper() for x in ['(EUR)', '[EUR]', 'EUROPE']):
                        region = 'EUR'
                    elif any(x in name.upper() for x in ['(JPN)', '[JPN]', 'JAPAN']):
                        region = 'JPN'
                    
                    file_type = filename.split('.')[-1].upper()
                    
                    self.games.append({
                        'id': str(len(self.games)),
                        'name': name.strip(),
                        'region': region,
                        'download_url': download_url,
                        'filename': filename,
                        'type': file_type
                    })
            
            if len(self.games) == 0:
                messagebox.showinfo("Aucun fichier", f"Aucun fichier trouvé dans:\n{self.local_files_dir}\n\nUtilisez le bouton '➕ Ajouter fichier(s)' pour ajouter des jeux.")
            else:
                self.games.sort(key=lambda x: x['name'])
                self.filtered_games = self.games
                self.update_game_list()
                self.status_label.config(text=f"✅ {len(self.games)} fichier(s) local(aux) chargé(s)")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement:\n{str(e)}")
    
    def open_local_folder(self):
        """Ouvre le dossier local dans l'explorateur"""
        if os.name == 'nt':  # Windows
            os.startfile(self.local_files_dir)
        elif os.name == 'posix':  # macOS et Linux
            import subprocess
            subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', self.local_files_dir])
    
    def load_from_server(self):
        """Charge la liste depuis le serveur configuré"""
        url = self.url_entry.get().strip()
        
        if not url:
            messagebox.showwarning("Attention", "Veuillez entrer une URL valide")
            return
        
        # Si c'est le serveur local, charger directement
        if "localhost" in url or "127.0.0.1" in url:
            self.load_local_files()
            return
        
        self.current_url = url
        self.status_label.config(text=f"Chargement depuis {url}...")
        self.root.update()
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            self.games = []
            links = soup.find_all('a', href=True)
            
            valid_extensions = ['.cia', '.3ds', '.3dsx', '.zip', '.7z', '.rar']
            
            for link in links:
                href = link.get('href', '')
                
                if any(href.lower().endswith(ext) for ext in valid_extensions):
                    name = os.path.basename(href)
                    original_name = name
                    
                    for ext in valid_extensions:
                        if name.lower().endswith(ext):
                            name = name[:-len(ext)]
                            break
                    
                    name = name.replace('_', ' ').replace('-', ' ')
                    
                    if href.startswith('http'):
                        download_url = href
                    else:
                        download_url = f"{url.rstrip('/')}/{href.lstrip('/')}"
                    
                    region = 'Unknown'
                    if any(x in name.upper() for x in ['(USA)', '[USA]', 'USA']):
                        region = 'USA'
                    elif any(x in name.upper() for x in ['(EUR)', '[EUR]', 'EUROPE', 'EUR']):
                        region = 'EUR'
                    elif any(x in name.upper() for x in ['(JPN)', '[JPN]', 'JAPAN', 'JPN']):
                        region = 'JPN'
                    
                    file_type = original_name.split('.')[-1].upper()
                    
                    self.games.append({
                        'id': str(len(self.games)),
                        'name': name.strip(),
                        'region': region,
                        'download_url': download_url,
                        'filename': original_name,
                        'type': file_type
                    })
            
            if len(self.games) == 0:
                messagebox.showwarning("Attention", f"Aucun fichier de jeu trouvé sur:\n{url}")
                self.status_label.config(text="❌ Aucun jeu trouvé")
            else:
                self.games.sort(key=lambda x: x['name'])
                self.filtered_games = self.games[:100]
                self.update_game_list()
                self.status_label.config(text=f"✅ {len(self.games)} jeux chargés depuis le serveur")
                messagebox.showinfo("Succès", f"{len(self.games)} jeux chargés avec succès !")
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Erreur réseau", f"Impossible de se connecter au serveur:\n{str(e)}")
            self.status_label.config(text="❌ Erreur de connexion")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement:\n{str(e)}")
            self.status_label.config(text="❌ Erreur de chargement")
    
    def on_server_select(self, event):
        """Gère la sélection d'un serveur prédéfini"""
        selected = self.server_combo.get()
        
        if selected == "Personnalisé":
            self.url_entry.config(state="normal")
            self.url_entry.delete(0, tk.END)
            self.url_entry.focus()
        elif selected == "🏠 Serveur Local":
            local_ip = self.get_local_ip()
            url = f"http://{local_ip}:{self.server_port}"
            self.url_entry.config(state="normal")
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)
        else:
            url = self.preset_servers.get(selected, "")
            self.url_entry.config(state="normal")
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)
    
    def create_widgets(self):
        """Crée l'interface graphique"""
        # Titre
        title = tk.Label(
            self.root,
            text="3DS QR Code Generator - Serveur Local Intégré",
            font=("Arial", 20, "bold"),
            bg="#1a1a2e",
            fg="#00d4ff"
        )
        title.pack(pady=8)
        
        # Frame serveur local
        local_server_frame = tk.LabelFrame(
            self.root,
            text="🏠 Serveur Local",
            font=("Arial", 11, "bold"),
            bg="#16213e",
            fg="#00d4ff",
            relief="ridge",
            bd=2
        )
        local_server_frame.pack(pady=8, padx=20, fill="x")
        
        # Boutons serveur local
        local_btn_frame = tk.Frame(local_server_frame, bg="#16213e")
        local_btn_frame.pack(pady=10, padx=10)
        
        self.start_server_btn = tk.Button(
            local_btn_frame,
            text="🚀 Démarrer le serveur local",
            command=self.toggle_server,
            bg="#27ae60",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=8
        )
        self.start_server_btn.pack(side="left", padx=5)
        
        tk.Button(
            local_btn_frame,
            text="➕ Ajouter fichier(s)",
            command=self.add_file_to_server,
            bg="#3498db",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=8
        ).pack(side="left", padx=5)
        
        tk.Button(
            local_btn_frame,
            text="📁 Ouvrir dossier",
            command=self.open_local_folder,
            bg="#9b59b6",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=8
        ).pack(side="left", padx=5)
        
        tk.Button(
            local_btn_frame,
            text="🔄 Charger fichiers locaux",
            command=self.load_local_files,
            bg="#f39c12",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=8
        ).pack(side="left", padx=5)
        
        # Statut serveur
        self.server_status_label = tk.Label(
            local_server_frame,
            text="🔴 Serveur arrêté",
            font=("Arial", 10),
            bg="#16213e",
            fg="#e74c3c"
        )
        self.server_status_label.pack(pady=5)
        
        # Frame serveur distant
        server_frame = tk.LabelFrame(
            self.root,
            text="🌐 Serveurs Distants",
            font=("Arial", 11, "bold"),
            bg="#16213e",
            fg="white",
            relief="ridge",
            bd=2
        )
        server_frame.pack(pady=8, padx=20, fill="x")
        
        # Serveurs prédéfinis
        preset_frame = tk.Frame(server_frame, bg="#16213e")
        preset_frame.pack(pady=8, padx=10, fill="x")
        
        tk.Label(
            preset_frame,
            text="Serveurs:",
            font=("Arial", 10),
            bg="#16213e",
            fg="white"
        ).pack(side="left", padx=5)
        
        self.server_combo = ttk.Combobox(
            preset_frame,
            values=list(self.preset_servers.keys()),
            state="readonly",
            font=("Arial", 10),
            width=35
        )
        self.server_combo.set("🏠 Serveur Local")
        self.server_combo.pack(side="left", padx=5)
        self.server_combo.bind('<<ComboboxSelected>>', self.on_server_select)
        
        # Barre URL
        url_frame = tk.Frame(server_frame, bg="#16213e")
        url_frame.pack(pady=8, padx=10, fill="x")
        
        tk.Label(
            url_frame,
            text="URL:",
            font=("Arial", 10),
            bg="#16213e",
            fg="white"
        ).pack(side="left", padx=5)
        
        self.url_entry = tk.Entry(
            url_frame,
            font=("Arial", 10),
            bg="#0f3460",
            fg="white",
            insertbackground="white",
            relief="flat",
            width=55
        )
        local_ip = self.get_local_ip()
        self.url_entry.insert(0, f"http://{local_ip}:{self.server_port}")
        self.url_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        tk.Button(
            url_frame,
            text="🔄 Charger",
            command=self.load_from_server,
            bg="#27ae60",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=5
        ).pack(side="left", padx=5)
        
        # Recherche
        search_frame = tk.Frame(self.root, bg="#1a1a2e")
        search_frame.pack(pady=8, padx=20, fill="x")
        
        tk.Label(
            search_frame,
            text="🔍",
            font=("Arial", 12),
            bg="#1a1a2e",
            fg="white"
        ).pack(side="left", padx=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search)
        
        tk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=("Arial", 11),
            bg="#16213e",
            fg="white",
            insertbackground="white",
            relief="flat"
        ).pack(side="left", padx=5, fill="x", expand=True)
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg="#1a1a2e")
        main_frame.pack(pady=8, padx=20, fill="both", expand=True)
        
        # Liste
        list_frame = tk.Frame(main_frame, bg="#16213e", relief="ridge", bd=2)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        tk.Label(
            list_frame,
            text="📦 Fichiers",
            font=("Arial", 13, "bold"),
            bg="#16213e",
            fg="white"
        ).pack(pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.game_listbox = tk.Listbox(
            list_frame,
            font=("Arial", 9),
            bg="#0f3460",
            fg="white",
            selectbackground="#6c5ce7",
            selectforeground="white",
            yscrollcommand=scrollbar.set,
            relief="flat"
        )
        self.game_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.game_listbox.bind('<<ListboxSelect>>', self.on_game_select)
        
        scrollbar.config(command=self.game_listbox.yview)
        
        # QR Code
        qr_frame = tk.Frame(main_frame, bg="#16213e", relief="ridge", bd=2)
        qr_frame.pack(side="right", fill="both", expand=True)
        
        self.qr_title = tk.Label(
            qr_frame,
            text="Démarrez le serveur local",
            font=("Arial", 12, "bold"),
            bg="#16213e",
            fg="white",
            wraplength=350
        )
        self.qr_title.pack(pady=8)
        
        self.info_label = tk.Label(
            qr_frame,
            text="Ajoutez des fichiers et générez des QR codes",
            font=("Arial", 9),
            bg="#16213e",
            fg="#a8dadc",
            justify="center",
            wraplength=350
        )
        self.info_label.pack(pady=5)
        
        self.qr_canvas = tk.Canvas(
            qr_frame,
            width=320,
            height=320,
            bg="white",
            relief="flat"
        )
        self.qr_canvas.pack(pady=8)
        
        btn_container = tk.Frame(qr_frame, bg="#16213e")
        btn_container.pack(pady=8)
        
        self.save_btn = tk.Button(
            btn_container,
            text="💾 Sauvegarder QR",
            command=self.save_qr_code,
            bg="#6c5ce7",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=8,
            state="disabled"
        )
        self.save_btn.pack(pady=3)
        
        self.browser_btn = tk.Button(
            btn_container,
            text="🌐 Ouvrir lien",
            command=self.open_in_browser,
            bg="#e67e22",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=8,
            state="disabled"
        )
        self.browser_btn.pack(pady=3)
        
        tk.Label(
            qr_frame,
            text="📱 Scannez avec FBI sur votre 3DS",
            font=("Arial", 9),
            bg="#16213e",
            fg="#a8dadc"
        ).pack(pady=8)
        
        # Statut
        self.status_label = tk.Label(
            self.root,
            text="Prêt",
            font=("Arial", 9),
            bg="#0f3460",
            fg="white",
            anchor="w"
        )
        self.status_label.pack(side="bottom", fill="x", padx=5, pady=5)
    
    def update_game_list(self):
        self.game_listbox.delete(0, tk.END)
        for game in self.filtered_games:
            display = f"{game['name']}"
            if game['region'] != 'Unknown':
                display += f" [{game['region']}]"
            display += f" ({game['type']})"
            self.game_listbox.insert(tk.END, display)
    
    def on_search(self, *args):
        search_term = self.search_var.get().lower()
        if not search_term:
            self.filtered_games = self.games[:100]
        else:
            self.filtered_games = [
                game for game in self.games
                if search_term in game['name'].lower() or
                   search_term in game['region'].lower() or
                   search_term in game['type'].lower()
            ][:100]
        self.update_game_list()
        self.status_label.config(text=f"🔍 {len(self.filtered_games)} fichier(s)")
    
    def on_game_select(self, event):
        selection = self.game_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        self.selected_game = self.filtered_games[index]
        
        self.qr_title.config(text=self.selected_game['name'])
        
        info_text = f"Type: {self.selected_game['type']}\n"
        info_text += f"Région: {self.selected_game['region']}\n"
        info_text += f"Fichier: {self.selected_game['filename']}\n\n"
        info_text += f"URL: {self.selected_game['download_url']}"
        
        self.info_label.config(text=info_text)
        self.generate_qr_code()
        
        self.save_btn.config(state="normal")
        self.browser_btn.config(state="normal")
    
    def generate_qr_code(self):
        if not self.selected_game:
            return
        
        # Obtenir la taille du canvas
        canvas_width = self.qr_canvas.winfo_width()
        canvas_height = self.qr_canvas.winfo_height()
        
        # Utiliser une taille par défaut si le canvas n'est pas encore rendu
        if canvas_width <= 1:
            canvas_width = 400
        if canvas_height <= 1:
            canvas_height = 400
        
        # Calculer la taille du QR code (90% de la taille du canvas)
        qr_size = int(min(canvas_width, canvas_height) * 0.9)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.selected_game['download_url'])
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        
        self.qr_image = ImageTk.PhotoImage(img)
        self.qr_canvas.delete("all")
        self.qr_canvas.create_image(canvas_width//2, canvas_height//2, image=self.qr_image)
    
    def save_qr_code(self):
        if not self.selected_game:
            return
        
        safe_name = "".join(c for c in self.selected_game['name'] if c.isalnum() or c in (' ', '-', '_'))
        default_name = f"{safe_name}_QR.png"
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        
        if filename:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.selected_game['download_url'])
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(filename)
            
            messagebox.showinfo("✅ Succès", f"QR Code sauvegardé:\n{filename}")
    
    def open_in_browser(self):
        if self.selected_game:
            webbrowser.open(self.selected_game['download_url'])
    
    def on_closing(self):
        """Gère la fermeture de l'application"""
        if self.server_running:
            self.stop_local_server()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = QRCodeGenerator(root)
    root.mainloop()

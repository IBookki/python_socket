import socket
import threading
import time
import tkinter as tk

HOST = "127.0.0.1"
PORT = 5000
FORMAT = "utf-8"
TAILLE_HEADER = 4

FOND = "#1a1d23"
FOND_HEADER = "#22262e"
FOND_ZONE = "#1a1d23"
FOND_BARRE = "#22262e"
FOND_CHAMP = "#2c313a"
TEXTE = "#d4d7dd"
TEXTE_PALE = "#6b7280"
ACCENT = "#5b8dd6"
VERT = "#4ade80"
ROUGE = "#f87171"
VIOLET = "#c084fc"
JAUNE = "#fbbf24"

COULEURS_PSEUDOS = ["#60a5fa", "#34d399", "#fbbf24", "#f472b6",
                    "#a78bfa", "#fb923c", "#22d3ee", "#f87171"]


def recevoir_exact(sock, n):
    donnees = b""
    while len(donnees) < n:
        morceau = sock.recv(n - len(donnees))
        if not morceau:
            return None
        donnees = donnees + morceau
    return donnees


def recevoir(sock):
    header = recevoir_exact(sock, TAILLE_HEADER)
    if header is None:
        return None
    taille = int.from_bytes(header, "big")
    message = recevoir_exact(sock, taille)
    if message is None:
        return None
    return message.decode(FORMAT, errors="replace")


def envoyer(sock, texte):
    message = texte.encode(FORMAT)
    taille = len(message).to_bytes(TAILLE_HEADER, "big")
    sock.sendall(taille + message)


def couleur_pseudo(pseudo):
    total = 0
    for lettre in pseudo:
        total = total + ord(lettre)
    return COULEURS_PSEUDOS[total % len(COULEURS_PSEUDOS)]


class Fenetre:

    def __init__(self):
        self.en_marche = True
        self.pseudos_vus = {}

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((HOST, PORT))
        except:
            print("Impossible de joindre le serveur")
            return

        self.fenetre = tk.Tk()
        self.fenetre.title("Chat")
        self.fenetre.geometry("620x560")
        self.fenetre.minsize(480, 400)
        self.fenetre.configure(bg=FOND)

        self.construire_header()
        self.construire_zone()
        self.construire_barre()

        self.fenetre.protocol("WM_DELETE_WINDOW", self.fermer)

        thread = threading.Thread(target=self.ecouter)
        thread.daemon = True
        thread.start()

        self.fenetre.mainloop()


    def construire_header(self):
        header = tk.Frame(self.fenetre, bg=FOND_HEADER, height=54)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        gauche = tk.Frame(header, bg=FOND_HEADER)
        gauche.pack(side="left", padx=16)

        tk.Label(gauche, text="Chat", bg=FOND_HEADER, fg=TEXTE,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(8, 0))

        self.sous_titre = tk.Label(gauche, text="salon : general",
                                   bg=FOND_HEADER, fg=TEXTE_PALE,
                                   font=("Segoe UI", 8))
        self.sous_titre.pack(anchor="w")

        droite = tk.Frame(header, bg=FOND_HEADER)
        droite.pack(side="right", padx=16)

        self.statut = tk.Label(droite, text="● connecte", bg=FOND_HEADER,
                               fg=VERT, font=("Segoe UI", 9))
        self.statut.pack(pady=16)

        tk.Frame(self.fenetre, bg="#2c313a", height=1).pack(side="top", fill="x")

    def construire_zone(self):
        conteneur = tk.Frame(self.fenetre, bg=FOND_ZONE)
        conteneur.pack(side="top", fill="both", expand=True)

        self.zone = tk.Text(conteneur, state="disabled", wrap="word",
                            bg=FOND_ZONE, fg=TEXTE, font=("Segoe UI", 10),
                            relief="flat", padx=16, pady=12,
                            spacing1=3, spacing3=3, cursor="arrow",
                            highlightthickness=0)
        self.zone.pack(side="left", fill="both", expand=True)

        barre = tk.Scrollbar(conteneur, command=self.zone.yview,
                             bg=FOND_ZONE, troughcolor=FOND_ZONE,
                             activebackground=TEXTE_PALE, relief="flat",
                             width=8, borderwidth=0)
        barre.pack(side="right", fill="y")
        self.zone.config(yscrollcommand=barre.set)

        self.zone.tag_config("systeme", foreground=TEXTE_PALE,
                             font=("Segoe UI", 9, "italic"), justify="center",
                             spacing1=8, spacing3=8)
        self.zone.tag_config("prive_entete", foreground=VIOLET,
                             font=("Segoe UI", 9, "bold"))
        self.zone.tag_config("prive_corps", foreground=VIOLET)
        self.zone.tag_config("moi_entete", foreground=ACCENT,
                             font=("Segoe UI", 9, "bold"))
        self.zone.tag_config("corps", foreground=TEXTE)
        self.zone.tag_config("heure", foreground="#4b5563",
                             font=("Segoe UI", 8))
        self.zone.tag_config("erreur", foreground=ROUGE,
                             font=("Segoe UI", 9), justify="center",
                             spacing1=8, spacing3=8)
        self.zone.tag_config("info", foreground=JAUNE,
                             font=("Segoe UI", 9), justify="center",
                             spacing1=8, spacing3=8)

    def construire_barre(self):
        tk.Frame(self.fenetre, bg="#2c313a", height=1).pack(side="bottom", fill="x")

        bas = tk.Frame(self.fenetre, bg=FOND_BARRE, height=64)
        bas.pack(side="bottom", fill="x")
        bas.pack_propagate(False)

        cadre = tk.Frame(bas, bg=FOND_CHAMP)
        cadre.pack(side="left", fill="x", expand=True, padx=(14, 8), pady=13)

        self.champ = tk.Entry(cadre, bg=FOND_CHAMP, fg=TEXTE,
                              font=("Segoe UI", 10), relief="flat",
                              insertbackground=ACCENT, highlightthickness=0)
        self.champ.pack(fill="both", expand=True, padx=12, pady=9)
        self.champ.bind("<Return>", self.envoyer_message)
        self.champ.focus()

        self.bouton = tk.Button(bas, text="Envoyer", command=self.envoyer_message,
                                bg=ACCENT, fg="white", font=("Segoe UI", 9, "bold"),
                                relief="flat", padx=18, pady=8, cursor="hand2",
                                activebackground="#4a7bc0", activeforeground="white",
                                borderwidth=0)
        self.bouton.pack(side="right", padx=(0, 14), pady=13)

        self.bouton.bind("<Enter>", lambda e: self.bouton.config(bg="#4a7bc0"))
        self.bouton.bind("<Leave>", lambda e: self.bouton.config(bg=ACCENT))


    def ecrire(self, texte, tag):
        self.zone.config(state="normal")
        self.zone.insert("end", texte, tag)
        self.zone.config(state="disabled")
        self.zone.see("end")

    def afficher_message(self, pseudo, corps, est_moi=False):
        """Affiche un message avec l'entete colore et l'heure."""
        self.zone.config(state="normal")

        if pseudo not in self.pseudos_vus:
            nom_tag = "pseudo_" + pseudo
            couleur = ACCENT if est_moi else couleur_pseudo(pseudo)
            self.zone.tag_config(nom_tag, foreground=couleur,
                                 font=("Segoe UI", 9, "bold"))
            self.pseudos_vus[pseudo] = nom_tag

        self.zone.insert("end", pseudo, self.pseudos_vus[pseudo])
        self.zone.insert("end", "  " + time.strftime("%H:%M") + "\n", "heure")
        self.zone.insert("end", corps + "\n\n", "corps")

        self.zone.config(state="disabled")
        self.zone.see("end")

    def afficher_prive(self, entete, corps):
        self.zone.config(state="normal")
        self.zone.insert("end", entete, "prive_entete")
        self.zone.insert("end", "  " + time.strftime("%H:%M") + "\n", "heure")
        self.zone.insert("end", corps + "\n\n", "prive_corps")
        self.zone.config(state="disabled")
        self.zone.see("end")


    def envoyer_message(self, event=None):
        message = self.champ.get().strip()
        if message == "":
            return

        self.champ.delete(0, "end")

        try:
            envoyer(self.client, message)
        except:
            self.ecrire("Erreur d'envoi\n", "erreur")
            return

        if message[0:6] == "/join ":
            self.sous_titre.config(text="salon : " + message[6:].strip())
        elif message == "/leave":
            self.sous_titre.config(text="salon : general")

        if message == "/quit":
            self.fermer()

    def ecouter(self):
        while self.en_marche:
            try:
                message = recevoir(self.client)
            except:
                break

            if message == None:
                break

            self.traiter(message)

        self.en_marche = False
        self.statut.config(text="● deconnecte", fg=ROUGE)
        self.ecrire("Connexion fermee\n", "erreur")

    def traiter(self, message):
        if message == "CLEAR:":
            self.zone.config(state="normal")
            self.zone.delete("1.0", "end")
            self.zone.config(state="disabled")

        elif message[0:5] == "PING:":
            depart = float(message[5:])
            ms = (time.time() - depart) * 1000
            self.ecrire("Ping : " + str(round(ms, 1)) + " ms\n", "info")

        elif message[0:10] == "[SERVEUR] ":
            corps = message[10:]
            if corps[0:6] == "Erreur":
                self.ecrire(corps + "\n", "erreur")
            else:
                self.ecrire(corps + "\n", "info")

        elif message[0:4] == "[MP ":
            fin = message.find("]")
            entete = message[1:fin]
            corps = message[fin + 2:]
            self.afficher_prive(entete, corps)

        elif message[0:6] == "moi : ":
            self.afficher_message("moi", message[6:], True)

        elif " : " in message:
            coupe = message.find(" : ")
            self.afficher_message(message[0:coupe], message[coupe + 3:])

        else:
            self.ecrire(message + "\n", "systeme")

    def fermer(self):
        self.en_marche = False
        try:
            self.client.close()
        except:
            pass
        self.fenetre.destroy()


Fenetre()

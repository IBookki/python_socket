import socket
import threading
import json
import os
import time

HOST = "127.0.0.1"
PORT = 5000
FORMAT = "utf-8"
TAILLE_HEADER = 4
TIMEOUT = 120

clients = {}
verrou = threading.Lock()
ips_bannies = []


def charger_json():
    if os.path.exists("users.json"):
        try:
            f = open("users.json", "r")
            data = json.load(f)
            f.close()
            return data
        except:
            return {}
    return {}


def sauver_json(pseudo, role):
    data = charger_json()
    data[pseudo] = {"role": role}
    f = open("users.json", "w")
    json.dump(data, f, indent=2)
    f.close()


def role_sauvegarde(pseudo):
    data = charger_json()
    if pseudo in data:
        return data[pseudo]["role"]
    return None


def envoyer(sock, texte):
    try:
        message = texte.encode(FORMAT)
        taille = len(message).to_bytes(TAILLE_HEADER, "big")
        sock.sendall(taille + message)
    except:
        pass


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
    if taille <= 0 or taille > 60000:
        return None
    message = recevoir_exact(sock, taille)
    if message is None:
        return None
    return message.decode(FORMAT, errors="replace")


def broadcast(texte, salon=None, sauf=None):
    verrou.acquire()
    liste = list(clients.items())
    verrou.release()

    for element in liste:
        sock = element[0]
        infos = element[1]
        if sock == sauf:
            continue
        if salon != None and infos["salon"] != salon:
            continue
        envoyer(sock, texte)


def message_serveur(sock, texte):
    envoyer(sock, "[SERVEUR] " + texte)


def chercher_client(pseudo):
    verrou.acquire()
    for sock in clients:
        if clients[sock]["pseudo"] == pseudo:
            verrou.release()
            return sock
    verrou.release()
    return None


def pseudo_valide(pseudo):
    if len(pseudo) < 1 or len(pseudo) > 20:
        return False
    for lettre in pseudo:
        if not (lettre.isalnum() or lettre == "_" or lettre == "-"):
            return False
    return True


def est_modo(infos):
    if infos["role"] == "moderateur" or infos["role"] == "admin":
        return True
    return False


def traiter_commande(sock, infos, message):
    morceaux = message.split()
    commande = morceaux[0].lower()
    args = morceaux[1:]

    if commande == "/quit":
        return False

    elif commande == "/moi":
        message_serveur(sock, "Pseudo : " + infos["pseudo"] + " | Role : " + infos["role"] + " | Salon : " + infos["salon"])

    elif commande == "/nick":
        if len(args) == 0 or not pseudo_valide(args[0]) or chercher_client(args[0]) != None:
            message_serveur(sock, "Pseudo refuse")
        else:
            ancien = infos["pseudo"]
            infos["pseudo"] = args[0]
            ancien_role = role_sauvegarde(args[0])
            if ancien_role != None:
                infos["role"] = ancien_role
            sauver_json(args[0], infos["role"])
            broadcast(ancien + " s'appelle maintenant " + args[0], infos["salon"])

    elif commande == "/mp":
        if len(args) < 2:
            message_serveur(sock, "Erreur")
        else:
            cible = chercher_client(args[0])
            if cible == None:
                message_serveur(sock, "Erreur : joueur introuvable")
            else:
                texte = " ".join(args[1:])
                envoyer(cible, "[MP de " + infos["pseudo"] + "] " + texte)
                envoyer(sock, "[MP a " + args[0] + "] " + texte)

    elif commande == "/time":
        message_serveur(sock, time.strftime("%d/%m/%Y %H:%M:%S"))

    elif commande == "/ping":
        envoyer(sock, "PING:" + str(time.time()))

    elif commande == "/clear":
        envoyer(sock, "CLEAR:")

    elif commande == "/join":
        if len(args) == 0:
            message_serveur(sock, "Erreur")
        else:
            broadcast(infos["pseudo"] + " a quitte le salon", infos["salon"], sock)
            infos["salon"] = args[0]
            broadcast(infos["pseudo"] + " a rejoint le salon", args[0])

    elif commande == "/leave":
        if infos["salon"] != "general":
            broadcast(infos["pseudo"] + " a quitte le salon", infos["salon"], sock)
            infos["salon"] = "general"
            broadcast(infos["pseudo"] + " est revenu dans general", "general")

    elif commande == "/kick" or commande == "/ban" or commande == "/mute" or commande == "/unmute":
        if not est_modo(infos):
            message_serveur(sock, "Erreur : reserve aux moderateurs")
            return True
        if len(args) == 0:
            message_serveur(sock, "Erreur : il faut un pseudo")
            return True

        cible = chercher_client(args[0])
        if cible == None:
            message_serveur(sock, "Erreur : joueur introuvable")
            return True

        infos_cible = clients[cible]

        if infos_cible["role"] == "admin" and infos["role"] != "admin":
            message_serveur(sock, "Erreur : tu ne peux pas viser un admin")
            return True

        if commande == "/mute":
            infos_cible["muet"] = True
            message_serveur(cible, "Tu as ete rendu muet")

        elif commande == "/unmute":
            infos_cible["muet"] = False
            message_serveur(cible, "Tu peux reparler")

        elif commande == "/kick":
            envoyer(cible, "Tu as ete expulse")
            broadcast(args[0] + " a ete expulse")
            try:
                cible.shutdown(socket.SHUT_RDWR)
            except:
                pass

        elif commande == "/ban":
            ips_bannies.append(infos_cible["ip"])
            envoyer(cible, "Tu as ete banni")
            broadcast(args[0] + " a ete banni")
            try:
                cible.shutdown(socket.SHUT_RDWR)
            except:
                pass

    elif commande == "/setadmin" or commande == "/setmodo" or commande == "/remadmin" or commande == "/remmodo":
        if infos["role"] != "admin":
            message_serveur(sock, "Erreur : reserve aux admins")
            return True
        if len(args) == 0:
            message_serveur(sock, "Erreur : il faut un pseudo")
            return True

        cible = chercher_client(args[0])
        if cible == None:
            message_serveur(sock, "Erreur : joueur introuvable")
            return True

        if commande == "/setadmin":
            nouveau_role = "admin"
        elif commande == "/setmodo":
            nouveau_role = "moderateur"
        else:
            nouveau_role = "user"

        clients[cible]["role"] = nouveau_role
        sauver_json(args[0], nouveau_role)
        message_serveur(cible, "Ton role est maintenant : " + nouveau_role)

    else:
        message_serveur(sock, "Commande inconnue")

    return True


def gerer_client(sock, adresse):
    ip = adresse[0]

    if ip in ips_bannies:
        sock.close()
        return

    sock.settimeout(TIMEOUT)
    print("[SERVEUR] Nouvelle connexion " + str(adresse))

    pseudo = "user" + str(adresse[1])

    role = role_sauvegarde(pseudo)
    if role == None:
        verrou.acquire()
        if len(clients) == 0:
            role = "admin"
        else:
            role = "user"
        verrou.release()

    infos = {"pseudo": pseudo, "role": role, "salon": "general", "muet": False, "ip": ip}

    verrou.acquire()
    clients[sock] = infos
    verrou.release()

    sauver_json(pseudo, role)
    message_serveur(sock, "Bienvenue " + pseudo + " ! Ton role : " + role)
    broadcast(pseudo + " a rejoint le chat", None, sock)

    try:
        while True:
            try:
                message = recevoir(sock)
            except socket.timeout:
                message_serveur(sock, "Deconnecte pour inactivite")
                break

            if message == None:
                break

            message = message.strip()
            if message == "":
                continue

            if message[0] == "/":
                if traiter_commande(sock, infos, message) == False:
                    break
            elif not infos["muet"]:
                broadcast(infos["pseudo"] + " : " + message, infos["salon"], sock)
                envoyer(sock, "moi : " + message)

    except:
        pass

    verrou.acquire()
    if sock in clients:
        del clients[sock]
    verrou.release()

    sock.close()
    broadcast(infos["pseudo"] + " a quitte le chat")
    print("[SERVEUR] " + str(adresse) + " deconnecte")


def lancer():
    serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serveur.bind((HOST, PORT))
    serveur.listen()
    print("[SERVEUR] En ecoute sur " + HOST + ":" + str(PORT))

    while True:
        (sock, adresse) = serveur.accept()
        thread = threading.Thread(target=gerer_client, args=(sock, adresse))
        thread.daemon = True
        thread.start()


lancer()

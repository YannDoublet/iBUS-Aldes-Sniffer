# iBUS Aldes Sniffer/Sender
# Copyright (c) 2026 Yann Doublet
# Licensed under the MIT License - see LICENSE file for details

VERSION = "1.1.0"

from machine import Pin, UART, reset, RTC
import network
import socket
import time

serial_input = []
frame_history = []  # Historique des trames reçues [(timestamp, data), ...]
MAX_HISTORY = 20    # Nombre max de trames conservées (limité pour la mémoire)

# Initialisation RTC
rtc = RTC()

# Configuration UART pour Raspberry Pi Pico avec inversion TX
uart0 = UART(0, baudrate=2400, bits=8, parity=0, stop=1, tx=Pin(0), rx=Pin(1), invert=UART.INV_TX)

ssid = 'your_ssid'
password = 'your_password'

def get_timestamp():
    """Retourne l'heure actuelle formatée HH:MM:SS"""
    t = rtc.datetime()
    return "{:02d}:{:02d}:{:02d}".format(t[4], t[5], t[6])

def add_to_history(data):
    """Ajoute une trame à l'historique avec horodatage"""
    global frame_history
    timestamp = get_timestamp()
    frame_history.insert(0, (timestamp, list(data)))  # Insérer en début de liste
    if len(frame_history) > MAX_HISTORY:
        frame_history.pop()  # Supprimer la plus ancienne

def send_ibus_frame(hex_string):
    """Envoie une trame sur le bus depuis une chaîne hexa"""
    try:
        # Nettoyer la chaîne (enlever espaces, 0x, etc.)
        hex_clean = hex_string.replace(" ", "").replace("0x", "").replace(",", "")
        
        # Convertir en bytes
        frame = bytes.fromhex(hex_clean)
        
        # Attendre que le bus soit libre
        time.sleep_ms(50)
        
        # Envoyer sur le bus (signal TX inversé automatiquement)
        uart0.write(frame)
        
        print("TX envoyé:", ' '.join('{:02X}'.format(x) for x in frame))
        return True, "Trame envoyée: {}".format(' '.join('{:02X}'.format(x) for x in frame))
    except Exception as e:
        print("Erreur TX:", e)
        return False, "Erreur: {}".format(str(e))

def send_html_part(client, html):
    """Envoie une partie de HTML au client"""
    try:
        client.send(html.encode('utf-8'))
    except:
        pass

def send_web_page(client, message=""):
    """Envoie la page web par morceaux pour économiser la mémoire"""
    import gc
    gc.collect()
    
    if serial_input:
        data_hex = ' '.join('{:02X}'.format(x) for x in serial_input)
        data_dec = ' '.join(str(x) for x in serial_input)
    else:
        data_hex = "En attente..."
        data_dec = ""
    
    # Envoyer l'en-tête HTTP
    client.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n')
    
    # Partie 1: Head et CSS (simplifié)
    send_html_part(client, """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>iBUS Sniffer</title><style>
body{font-family:monospace;background:#1e1e1e;color:#d4d4d4;padding:20px;max-width:1200px;margin:0 auto}
.frame{background:#2d2d2d;padding:15px;margin:10px 0;border-left:4px solid #007acc}
.hframe{background:#2d2d2d;padding:15px;margin:10px 0;border-left:4px solid #dcdcaa}
h1{color:#569cd6}h2{color:#4ec9b0}h3{color:#dcdcaa}.label{color:#9cdcfe;font-weight:bold}
input{width:100%;padding:10px;background:#1e1e1e;border:1px solid #007acc;color:#d4d4d4;font-family:monospace;box-sizing:border-box}
button{background:#007acc;color:white;border:none;padding:10px 20px;cursor:pointer;margin-top:10px}
.bclear{background:#ce9178}.msg{background:#2d2d2d;padding:10px;margin:10px 0;border-left:4px solid #4ec9b0;color:#4ec9b0}
table{width:100%;border-collapse:collapse;margin-top:10px}th,td{padding:6px;text-align:left;border-bottom:1px solid #3d3d3d}
th{background:#1e1e1e;color:#9cdcfe}.ts{color:#ce9178}.hc{max-height:300px;overflow-y:auto}
.rf{background:#252526;padding:10px;text-align:center}.rf a{color:#007acc}
</style></head><body>""")
    
    # Partie 2: Message si présent
    if message:
        send_html_part(client, '<div class="msg">{}</div>'.format(message))
    
    # Partie 3: Dernière trame
    send_html_part(client, """<h1>iBUS Sniffer/Sender <small style="color:#6a9955">v{}</small></h1>
<div class="frame"><h2>Derniere trame</h2>""".format(VERSION) + """
<p><span class="label">HEX:</span> {}</p>
<p><span class="label">DEC:</span> {}</p>
<p><span class="label">Taille:</span> {} bytes</p></div>""".format(data_hex, data_dec, len(serial_input)))
    
    gc.collect()
    
    # Partie 4: Historique - header
    send_html_part(client, """<div class="hframe"><h3>Historique ({} trames)</h3>
<div class="hc"><table><tr><th>Heure</th><th>Trame</th><th>Taille</th></tr>""".format(len(frame_history)))
    
    # Partie 5: Lignes de l'historique une par une
    if frame_history:
        for timestamp, data in frame_history:
            hex_str = ' '.join('{:02X}'.format(x) for x in data)
            send_html_part(client, '<tr><td class="ts">{}</td><td>{}</td><td>{}B</td></tr>'.format(
                timestamp, hex_str, len(data)))
    else:
        send_html_part(client, '<tr><td colspan="3">Aucune trame</td></tr>')
    
    # Partie 6: Fin historique et formulaire
    send_html_part(client, """</table></div>
<form method="POST" action="/clear"><button type="submit" class="bclear">Effacer</button></form></div>""")
    
    gc.collect()
    
    # Partie 7: Formulaire envoi et footer
    send_html_part(client, """<div class="frame"><h2>Envoyer</h2>
<form method="POST" action="/send">
<p><span class="label">HEX:</span></p>
<input type="text" name="hex_data" placeholder="FD A0 09 A0 FF 01 FF FF 9F 75" required>
<button type="submit">Envoyer</button></form></div>
<div class="rf"><a href="/">Rafraichir</a> | v{}</div></body></html>""".format(VERSION))

# Connexion WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    print("Connexion au WiFi: {}".format(ssid))
    wlan.connect(ssid, password)
    
    timeout = 0
    while not wlan.isconnected() and timeout < 20:
        print('.', end="")
        time.sleep_ms(500)
        timeout += 1
    
    if not wlan.isconnected():
        print("\nEchec WiFi, redemarrage...")
        time.sleep(2)
        reset()

print("\nWiFi OK:", wlan.ifconfig()[0])

# Serveur web
socketServeur = None
try:
    socketServeur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socketServeur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socketServeur.bind(('', 80))
    socketServeur.listen(5)
    print("Serveur demarre sur http://{}".format(wlan.ifconfig()[0]))
except OSError as e:
    print("Erreur socket:", e)
    time.sleep(2)
    reset()

# Boucle principale
last_message = ""

while True:
    connexionClient = None
    try:
        # Lecture continue du bus iBUS
        if uart0.any():
            data = uart0.read()
            if data:
                serial_input = list(data)
                add_to_history(data)  # Ajouter à l'historique
                print("iBUS RX:", ' '.join('{:02X}'.format(x) for x in serial_input))
        
        # Serveur web non-bloquant avec timeout court
        socketServeur.settimeout(0.05)  # Réduit à 50ms pour éviter les timeouts
        try:
            connexionClient, adresse = socketServeur.accept()
            print("Client connecte:", adresse)
            
            # Timeout réduit pour la réception
            connexionClient.settimeout(2.0)
            
            try:
                requete = connexionClient.recv(1024).decode('utf-8')
                print("Requete recue")
                
                # Traiter la requête POST pour envoi de données
                if "POST /send" in requete:
                    # Extraire les données du formulaire
                    if "hex_data=" in requete:
                        # Trouver la ligne avec les données
                        lines = requete.split('\r\n')
                        for line in lines:
                            if line.startswith("hex_data="):
                                hex_data = line.split('=', 1)[1]  # split avec limite pour éviter problèmes
                                # Décoder l'URL encoding
                                hex_data = hex_data.replace('+', ' ').replace('%20', ' ')
                                
                                # Envoyer sur le bus
                                success, msg = send_ibus_frame(hex_data)
                                last_message = msg
                                break
                
                # Traiter la requête POST pour effacer l'historique
                elif "POST /clear" in requete:
                    frame_history.clear()
                    last_message = "Historique effacé"
                
            except OSError as e:
                if e.args[0] == 110:  # ETIMEDOUT
                    print("Timeout reception requete (normal si GET simple)")
                else:
                    print("Erreur OSError:", e)
            except Exception as e:
                print("Erreur traitement requete:", e)
            
            # Envoyer la réponse HTTP par morceaux
            try:
                send_web_page(connexionClient, last_message)
            except Exception as e:
                print("Erreur envoi page:", e)
            
            try:
                connexionClient.close()
            except:
                pass
            
            # Réinitialiser le message après affichage
            last_message = ""
            
        except OSError as e:
            if e.args[0] != 11:  # Ignorer EAGAIN (pas de connexion en attente)
                pass
        
    except KeyboardInterrupt:
        print("\nArret...")
        break
    except Exception as e:
        print("Erreur boucle principale:", e)
        if connexionClient:
            try:
                connexionClient.close()
            except:
                pass

if socketServeur:
    socketServeur.close()
# iBUS Aldes Sniffer/Sender
# Copyright (c) 2024 Yann Doublet
# Licensed under the MIT License - see LICENSE file for details

from machine import Pin, UART, reset
import network
import socket
import time

serial_input = []

# Configuration UART pour Raspberry Pi Pico avec inversion TX
uart0 = UART(0, baudrate=2400, bits=8, parity=0, stop=1, tx=Pin(0), rx=Pin(1), invert=UART.INV_TX)

ssid = 'your_wifi_ssid'
password = 'your_wifi_password'

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

def web_page(message=""):
    if serial_input:
        data_hex = ' '.join('{:02X}'.format(x) for x in serial_input)
        data_dec = ' '.join(str(x) for x in serial_input)
    else:
        data_hex = "En attente de données..."
        data_dec = ""
    
    # Afficher le message de statut si présent
    status_html = ""
    if message:
        status_html = '<div class="message">{}</div>'.format(message)
    
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>iBUS Aldes Sniffer/Sender</title>
    <style>
        body {{ 
            font-family: monospace; 
            background: #1e1e1e; 
            color: #d4d4d4; 
            padding: 20px; 
            max-width: 1200px;
            margin: 0 auto;
        }}
        .frame {{ 
            background: #2d2d2d; 
            padding: 15px; 
            margin: 10px 0; 
            border-left: 4px solid #007acc; 
        }}
        .send-frame {{
            background: #2d2d2d;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid #4ec9b0;
        }}
        h1 {{ color: #569cd6; }}
        h2 {{ color: #4ec9b0; }}
        .label {{ color: #9cdcfe; font-weight: bold; }}
        input[type="text"] {{
            width: 100%;
            padding: 10px;
            background: #1e1e1e;
            border: 1px solid #007acc;
            color: #d4d4d4;
            font-family: monospace;
            font-size: 14px;
            box-sizing: border-box;
        }}
        button {{
            background: #007acc;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 14px;
            cursor: pointer;
            margin-top: 10px;
        }}
        button:hover {{
            background: #005a9e;
        }}
        .message {{
            background: #2d2d2d;
            padding: 10px;
            margin: 10px 0;
            border-left: 4px solid #4ec9b0;
            color: #4ec9b0;
        }}
        .examples {{
            color: #6a9955;
            font-size: 12px;
            margin-top: 10px;
        }}
        .refresh {{
            background: #252526;
            padding: 10px;
            margin: 10px 0;
            text-align: center;
            color: #6a9955;
        }}
        .refresh a {{
            color: #007acc;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <h1>🔌 iBUS Aldes Sniffer/Sender (Raspberry Pi Pico)</h1>
    
    {}
    
    <div class="frame">
        <h2>📥 Données reçues</h2>
        <p><span class="label">HEX:</span> {}</p>
        <p><span class="label">DEC:</span> {}</p>
        <p><span class="label">Longueur:</span> {} bytes</p>
    </div>
    
    <div class="send-frame">
        <h2>📤 Envoyer une trame</h2>
        <form method="POST" action="/send">
            <p><span class="label">Données en hexadécimal:</span></p>
            <input type="text" name="hex_data" placeholder="Ex: FD A0 09 A0 FF 01 FF FF 9F 75" required>
            <button type="submit">Envoyer sur le bus</button>
        </form>
        <div class="examples">
            <p><strong>Exemples de trames:</strong></p>
            <p>• Mode Auto: FD A0 09 A0 FF 01 FF FF 9F 75</p>
            <p>• Mode Boost: FD A0 09 A0 FF 02 FF FF 9F 76</p>
            <p>Format accepté: espaces optionnels, avec ou sans 0x</p>
        </div>
    </div>
    
    <div class="refresh">
        <a href="/">🔄 Rafraîchir</a> | Auto-refresh désactivé pour permettre l'envoi de commandes
    </div>
</body>
</html>""".format(status_html, data_hex, data_dec, len(serial_input))
    return html

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
                
            except OSError as e:
                if e.args[0] == 110:  # ETIMEDOUT
                    print("Timeout reception requete (normal si GET simple)")
                else:
                    print("Erreur OSError:", e)
            except Exception as e:
                print("Erreur traitement requete:", e)
            
            # Envoyer la réponse HTTP (toujours, même si timeout)
            try:
                connexionClient.send(b'HTTP/1.1 200 OK\r\n')
                connexionClient.send(b'Content-Type: text/html; charset=utf-8\r\n')
                connexionClient.send(b'Connection: close\r\n\r\n')
                reponse = web_page(last_message)
                connexionClient.sendall(reponse.encode('utf-8'))
            except:
                pass  # Ignorer les erreurs d'envoi
            
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

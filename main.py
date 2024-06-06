import g4f.Provider
from g4f.client import Client
from g4f.Provider import RetryProvider, Phind, FreeChatgpt, Liaobots
import g4f
import os.path
from g4f.cookies import set_cookies_dir, read_cookie_files
from g4f.cookies import set_cookies
import g4f.debug
import speech_recognition as sr
import sqlite3
import time
from gtts import gTTS

# Cookies
cookies_dir = os.path.join(os.path.dirname(__file__), "har_and_cookies")
set_cookies_dir(cookies_dir)
read_cookie_files(cookies_dir)
g4f.debug.logging = True
# Conexión a la base de datos
conn = sqlite3.connect('conversation_history.db')
cursor = conn.cursor()

# Crear tabla si no existe
cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT,
        content TEXT
    )
''')

# Obtener historial anterior si existe
cursor.execute("SELECT role, content FROM conversation ORDER BY id")
rows = cursor.fetchall()
historia = [{"role": row[0], "content": row[1]} for row in rows]

# Agregar mensaje predeterminado si el historial está vacío
if not historia:
    historia.append({"role": "system", "content": "Eres una IA que habla muy resumidamente"})

# Inicializar reconocedor de voz
recognizer = sr.Recognizer()
mic = sr.Microphone()

contador = 0

# Bucle principal
while True:
    try:
        if contador == 0:
            historia = [
                {"role": "system", "content": "Eres una IA que habla muy resumidamente"},
                {"role": "user", "content": "Presentate, di tu nombre y función se breve, nunca superes en la conversación los 255 caracteres. Insisto jamas superes los 255 caracteres"}
            ]

        if contador > 0:
            with mic as source:
                audio = recognizer.listen(source)
                recognizer.adjust_for_ambient_noise(mic)
                p = recognizer.recognize_google(audio, language="es-ES")
            if p == "salir":
                break
            historia.append({"role": "user", "content": p})
            cursor.execute("INSERT INTO conversation (role, content) VALUES (?, ?)", ("user", p))
            conn.commit()
            print("Usuario: " + p)

        # Cliente
        client = Client(provider=g4f.Provider.OpenaiChat)
        response = client.chat.completions.create(
            model= "",
            messages=historia,
            stream=False
        )
        #Buscar limitación de caracteres
        assistant_message = response.choices[0].message.content[:255]

        historia.append({"role": "assistant", "content": assistant_message})
        cursor.execute("INSERT INTO conversation (role, content) VALUES (?, ?)",
                       (historia[-1]["role"], historia[-1]["content"]))
        conn.commit()

        # Convertir texto a voz usando GTTS
        speech = gTTS(text=assistant_message, lang="es", slow=False)
        speech.save("response.mp3")
        os.system("cvlc --play-and-exit response.mp3")

        print(assistant_message)

        contador += 1

    except Exception as e:
        print("Se produjo un error:", e)
        print("Reiniciando la conversación...")
        time.sleep(5)  # Esperar 5 segundos antes de reiniciar la conversación
        contador = 0  # Reiniciar el contador

import requests
import json

# Nodos activos
nodos = ["http://127.0.0.1:5002", "http://127.0.0.1:5003", "http://127.0.0.1:5004"]
nodos_data = {"direccion_nodos": nodos}
# Cabecera JSON (comun a todas)
cabecera = {"Content-type": "application/json", "Accept": "text/plain"}

# datos transaccion
transaccion_nueva = {"origen": "nodoA", "destino": "nodoB", "cantidad": 10}

r = requests.post(
    "http://127.0.0.1:5001/transacciones/nueva",
    data=json.dumps(transaccion_nueva),
    headers=cabecera,
)
print(r.text)

r = requests.get("http://127.0.0.1:5001/minar")
print(r.text)

r = requests.get("http://127.0.0.1:5001/chain")
print(r.text)

# Añadir nodos a la red
r = requests.post(
    "http://127.0.0.1:5001/nodos/registrar",
    data=json.dumps(nodos_data),
    headers=cabecera,
)
print(r.text)

# Comprobación de ping y pong
r = requests.get("http://127.0.0.1:5001/ping")
print(r.text)

# Comprobar que la blockchain esta actualizada
for nodo in nodos:
    r = requests.get(f"{nodo}/chain")
    print(r.text)

# Comprobar los conlifctos
# Primero añado una transacción y mino un bloque en otro nodo distinto al principal
r = requests.post(
    "http://127.0.0.1:5002/transacciones/nueva",
    data=json.dumps(transaccion_nueva),
    headers=cabecera,
)
print(r.text)

r = requests.get("http://127.0.0.1:5002/minar")
print(r.text)

r = requests.get("http://127.0.0.1:5002/chain")
print(r.text)

# Ahora trato de crear una transacción y minar en el nodo principal
r = requests.post(
    "http://127.0.0.1:5001/transacciones/nueva",
    data=json.dumps(transaccion_nueva),
    headers=cabecera,
)
print(r.text)

r = requests.get("http://127.0.0.1:5001/minar")
print(r.text)

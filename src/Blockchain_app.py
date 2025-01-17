import BlockChain
from uuid import uuid4
import socket
from flask import Flask, jsonify, request
from argparse import ArgumentParser
import requests
import json
from multiprocessing import Process
import time
from threading import Thread, Lock
import platform
from datetime import datetime
import os

# Instancia del nodo
app = Flask(__name__)

# Instanciacion de la aplicacion
blockchain = BlockChain.Blockchain()
nodos_red = set()

# Para saber mi ip
mi_ip = "192.168.1.56"  # ifconfig | grep "inet " to get it

# Lock para evitar conflictos
lock = Lock()


@app.route("/transacciones/nueva", methods=["POST"])
def nueva_transaccion():
    values = request.get_json()
    # Comprobamos que todos los datos de la transaccion estan
    required = ["origen", "destino", "cantidad"]
    if not all(k in values for k in required):
        return "Faltan valores", 400

    # Creamos una nueva transaccion
    indice = blockchain.nueva_transaccion(
        values["origen"], values["destino"], values["cantidad"]
    )
    response = {
        "mensaje": f"La transaccion se incluira en el bloque con indice {indice}"
    }
    return jsonify(response), 201


@app.route("/chain", methods=["GET"])
def blockchain_completa():
    response = {
        # Solamente permitimos la cadena de aquellos bloques finales que tienen hash
        "chain": blockchain.to_json(),
        "longitud": len(blockchain.bloques),
    }
    return jsonify(response), 200


@app.route("/minar", methods=["GET"])
def minar():
    # No hay transacciones
    if len(blockchain.transacciones_no_confirmadas) == 0:
        response = {
            "mensaje": "No es posible crear un nuevo bloque. No hay transacciones"
        }
    else:
        # Hay transaccion, por lo tanto ademas de minar el bloque, recibimos recompensa
        # Recibimos un pago por minar el bloque. Creamos una nueva transaccion con:
        # Dejamos como origen el 0
        # Destino nuestra ip
        # Cantidad = 1
        blockchain.nueva_transaccion(origen=0, destino=mi_ip, cantidad=1)
        # Antes de crear el nuevo bloque e integrarlo resuelvo conflictos
        conflicto = resuelve_conflictos()

        if not conflicto:
            # Ahora voy a crear el nuevo bloque e integrarlo
            previous_hash = blockchain.bloques[-1].hash_bloque
            bloque_nuevo = blockchain.nuevo_bloque(previous_hash)
            hash_nuevo = blockchain.prueba_trabajo(bloque_nuevo)
            integrar_bloque = blockchain.integra_bloque(
                bloque_nuevo=bloque_nuevo, hash_prueba=hash_nuevo
            )

            if integrar_bloque:
                response = {
                    "Nuevo bloque": bloque_nuevo.toDict(),
                    "mensaje": "Nuevo bloque minado",
                }

        else:
            # En caso de no ser la cadena correcta
            response = {
                "mensaje": "Ha habido un conflicto. Esta cadena se ha actualizado a una vesrsion mas larga"
            }

    return jsonify(response), 200


@app.route("/nodos/registrar", methods=["POST"])
def registrar_nodos_completo():
    values = request.get_json()
    global blockchain
    global nodos_red
    nodos_nuevos = values.get("direccion_nodos")

    if nodos_nuevos is None:
        return "Error: No se ha proporcionado una lista de nodos", 400

    puerto_host = "5001"
    nodo_host = f"http://{mi_ip}:{puerto_host}"
    all_correct = True
    # nodos_red.add(nodo_host) #Update mejor
    [nodos_red.add(n) for n in nodos_nuevos]
    blockchain_json = blockchain.to_json()
    status_codes = []
    lista_nodos = [nodo_host]
    for nodo in nodos_nuevos:
        data = {
            "nodos_direcciones": [
                lista_nodos.append(n) for n in nodos_nuevos if n != nodo
            ],
            "blockchain": blockchain_json,
        }
        response = requests.post(
            nodo + "/nodos/registro_simple",
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
        status_codes.append(response.status_code)

    if not 400 in status_codes:
        response = {
            "mensaje": "Se han incluido nuevos nodos en la red",
            "nodos_totales": list(nodos_red),
        }
    else:
        response = {
            "mensaje": "Error notificando el nodo estipulado",
        }
    return jsonify(response), 201


@app.route("/nodos/registro_simple", methods=["POST"])
def registrar_nodo_actualiza_blockchain():
    # Obtenemos la variable global de blockchain
    global blockchain
    nodos_red = set()
    read_json = request.get_json()
    nodos_recibidos = read_json.get("nodos_direcciones")
    [nodos_red.add(n) for n in nodos_recibidos]
    blockchain_json = read_json.get("blockchain")
    blockchain_leida = BlockChain.Blockchain()
    blockchain_leida.json_to_blockchain(blockchain_json)
    puerto = request.environ.get("REMOTE_PORT")  #!Revisar
    if blockchain_leida is None:
        return "El blockchain de la red esta currupto", 400
    else:
        blockchain = blockchain_leida
        return (
            "La blockchain del nodo"
            + str(mi_ip)
            + ":"
            + str(puerto)
            + "ha sido correctamente actualizada",
            200,
        )


@app.route("/ping", methods=["GET"])
def comprobacion_ping():
    host = request.remote_addr
    puerto_host = request.environ["SERVER_PORT"]
    mensaje_ping = {
        "ip_puerto_origen": f"{host}:{puerto_host}",
        "mensaje": "PING",
        "timestamp": time.time(),
    }
    respuestas_nodos = []
    respuesta_final = {"respuesta_final": f"#Ping de {host}:{puerto_host}"}

    for nodo in nodos_red:
        try:
            print(mensaje_ping, nodo + "/pong")
            response = requests.post(
                nodo + "/pong",
                data=json.dumps(mensaje_ping),
                headers={"Content-Type": "application/json"},
            )
            json_data = response.json()
            print(json_data["Respuesta"])
            respuestas_nodos.append(json_data["Respuesta"])
        except requests.exceptions.JSONDecodeError:
            respuestas_nodos.append({"error": "Invalid JSON response"})

    print(respuestas_nodos)
    for res in respuestas_nodos:
        respuesta_final["respuesta_final"] += " " + str(res)

    if len(respuestas_nodos) == len(nodos_red):
        respuesta_final["mensaje"] = "Todos los nodos responden"

    return jsonify(respuesta_final), 200


@app.route("/pong", methods=["POST"])
def comprobacion_pong():
    datos = request.get_json()
    host = datos.get("ip_puerto_origen")
    mensaje_ping = datos.get("mensaje")
    timestamp_ping = int(datos.get("timestamp"))

    nodo_actual = request.remote_addr
    puerto_actual = request.environ["SERVER_PORT"]

    delay = time.time() - timestamp_ping

    response = {
        "Respuesta": f"Respuesta: PONG{nodo_actual}:{puerto_actual} Retardo: {delay}",
    }

    return jsonify(response), 200


@app.route("/system", methods=["GET"])
def get_system_details():
    system_details = {
        "maquina": platform.machine(),
        "nombre_sistema": platform.system(),
        "version": platform.version(),
    }
    return jsonify(system_details), 200


def run_app(puerto):
    app.run(host="0.0.0.0", port=puerto)


def copia_seguridad(ip, puerto):
    global lock

    os.makedirs("backups", exist_ok=True)
    while True:
        time.sleep(60)

        lock.acquire()
        response = requests.get(str(f"http://{ip}:{puerto}") + "/chain")
        data = response.json()
        response = {
            # Solamente permitimos la cadena de aquellos bloques finales que tienen hash
            "chain": data["chain"],
            "longitud": data["longitud"],
            "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }
        nom_archivo = f"respaldo-nodo{ip}_{puerto}.json"
        output = os.path.join("backups", nom_archivo)

        with open(output, "w") as file:
            json.dump(response, file, indent=4)

        file.close()

        lock.release()


def resuelve_conflictos():
    """
    Mecanismo para establecer el consenso y resolver los conflictos
    """
    global blockchain
    longitud_actual = len(blockchain.bloques)
    cadena_mas_larga = None   

    for nodo in nodos_red:
        response = requests.get(str(nodo) + "/chain")
        if response.status_code == 200:
            data = response.json()
            if data["longitud"] > longitud_actual:
                cadena_mas_larga = data

    if cadena_mas_larga:
        return True
    else:
        return False


if __name__ == "__main__":
    num_instances = 4
    puerto1 = 5001
    instances = []
    [instances.append(puerto1 + i) for i in range(num_instances)]
    ps = []
    ths = []
    for instance in instances:
        th = Thread(
            target=copia_seguridad,
            args=(
                mi_ip,
                instance,
            ),
        )
        p = Process(target=run_app, args=(instance,))
        th.start()
        p.start()
        ths.append(th)
        ps.append(p)

    for th in ths:
        th.join()

    for p in ps:
        p.join()

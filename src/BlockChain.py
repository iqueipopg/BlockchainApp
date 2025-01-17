import json
import hashlib
import time


class Bloque:
    def __init__(
        self,
        indice: int,
        transacciones: list,
        timestamp: int,
        hash_previo: str,
        prueba: int = 0,
    ):
        """
        Constructor de la clase `Bloque`.
        :param indice: ID unico del bloque.
        :param transacciones: Lista de transacciones.
        :param timestamp: Momento en que el bloque fue generado.
        :param hash_previo hash previo
        :param prueba: prueba de trabajo
        """
        self.indice = indice
        self.transacciones = transacciones
        self.timestamp = timestamp
        self.hash_previo = hash_previo
        self.prueba = prueba
        self.hash_bloque = None

    def calcular_hash(self):
        """
        Metodo que devuelve el hash de un bloque
        """
        block_dict = {
            key: value for key, value in self.__dict__.items() if key != "hash_bloque"
        }
        block_string = json.dumps(block_dict, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def toDict(self):
        dic = {
            "hash_bloque": self.hash_bloque,
            "hash_previo": self.hash_previo,
            "indice": self.indice,
            "timestamp": self.timestamp,
            "prueba": self.prueba,
            "transacciones": self.transacciones,
        }

        return dic

    def __str__(self):
        return f"hash_bloque: {self.hash_bloque}, hash_previo: {self.hash_previo}, indice: {self.indice}, prueba: {self.prueba}, timestamp: {self.timestamp}, transacciones: {self.transacciones}"


class Blockchain(object):
    def __init__(self):
        self.dificultad = 4
        self.transacciones_no_confirmadas = []
        self.bloques = self.primer_bloque()

    def primer_bloque(self):
        bloque = Bloque(
            indice=1, transacciones=None, hash_previo=1, timestamp=time.time()
        )
        bloque.hash_bloque = bloque.calcular_hash()
        return [bloque]

    def nuevo_bloque(self, hash_previo: str) -> Bloque:
        """
        Crea un nuevo bloque a partir de las transacciones que no estan
        confirmadas
        :param hash_previo: el hash del bloque anterior de la cadena
        :return: el nuevo bloque
        """

        bloque = Bloque(
            indice=(len(self.bloques) + 1),
            transacciones=self.transacciones_no_confirmadas,
            timestamp=time.time(),
            hash_previo=hash_previo,
        )
        bloque.hash_bloque = bloque.calcular_hash()
        return bloque

    def nueva_transaccion(self, origen: str, destino: str, cantidad: int) -> int:
        """Crea una nueva transaccion a partir de un origen, un destino y una
        cantidad y la incluye en las listas de transacciones

        :param origen: <str> el que envia la transaccion
        :param destino: <str> el que recibe la transaccion
        :param cantidad: <int> la candidad
        :return: <int> el indice del bloque que va a almacenar la transaccion
        """
        transaccion = {
            "origen": origen,
            "destino": destino,
            "cantidad": cantidad,
            "timestamp": time.time(),
        }
        self.transacciones_no_confirmadas.append(transaccion)

        return len(self.bloques) + 1

    def prueba_trabajo(self, bloque: Bloque) -> str:
        """Algoritmo simple de prueba de trabajo:
        - Calculara el hash del bloque hasta que encuentre un hash que empiece por tantos ceros como dificultad .
        - Cada vez que el bloque obtenga un hash que no sea adecuado, incrementara en uno el campo de ``prueba'' del bloque

        :param bloque: objeto de tipo bloque
        :return: el hash del nuevo bloque (dejara el campo de hash del bloque sin modificar)
        """

        bloque.prueba = 0
        prueba = "0" * self.dificultad
        hash = bloque.calcular_hash()

        while hash[: self.dificultad] != prueba:
            bloque.prueba += 1
            hash = bloque.calcular_hash()

        return hash

    def prueba_valida(self, bloque: Bloque, hash_bloque: str) -> bool:
        """
        Metodo que comprueba si el hash_bloque comienza con tantos ceros como la
        dificultad estipulada en el blockchain
        Ademas comprobara que hash_bloque coincide con el valor devuelvo del metodo de calcular hash del bloque.
        Si cualquiera de ambas comprobaciones es falsa, devolvera falso y en caso contrario verdadero

        :param bloque:
        :param hash_bloque:
        :return:
        """
        if (hash_bloque[: self.dificultad] == "0" * self.dificultad) and (
            bloque.calcular_hash() == hash_bloque
        ):
            return True

        else:
            return False

    def integra_bloque(self, bloque_nuevo: Bloque, hash_prueba: str) -> bool:
        """
        Metodo para integrar correctamente un bloque a la cadena de bloques.
        Debe comprobar que hash_prueba es valida y que el hash del bloque ultimo de la cadena
        coincida con el hash_previo del bloque que se va a integrar.
        Si pasa las comprobaciones, actualiza el hash del bloque nuevo a integrar con hash_prueba, lo inserta en la cadena y
        hace un reset de las transacciones no confirmadas (vuelve a dejar la lista de transacciones no confirmadas a una lista vacia)

        :param bloque_nuevo: el nuevo bloque que se va a integrar
        :param hash_prueba: la prueba de hash
        :return: True si se ha podido ejecutar bien y False en caso contrario (si no ha pasado alguna prueba)
        """
        if (self.prueba_valida(bloque=bloque_nuevo, hash_bloque=hash_prueba)) and (
            self.bloques[-1].hash_bloque == bloque_nuevo.hash_previo
        ):
            bloque_nuevo.hash_bloque = hash_prueba
            self.transacciones_no_confirmadas = []
            self.bloques.append(bloque_nuevo)
            return True

        else:
            return False

    def to_json(self):
        """
        Código para pasar la blockchain a un json
        """
        blockchain_json = []

        for bloque in self.bloques:
            block_json = bloque.toDict()
            blockchain_json.append(block_json)

        return blockchain_json

    def json_to_blockchain(self, blockchain_json):
        self.bloques[0].timestamp = blockchain_json[0]["timestamp"]
        self.bloques[0].hash_bloque = self.bloques[0].calcular_hash()

        for bloque in blockchain_json:
            if bloque["indice"] > 1:
                bloque_nuevo = Bloque(
                    bloque["indice"],
                    bloque["transacciones"],
                    bloque["timestamp"],
                    bloque["hash_previo"],
                    bloque["prueba"],
                )

                hash_nuevo = bloque_nuevo.calcular_hash()
                integracion = self.integra_bloque(bloque_nuevo, hash_nuevo)
                if not integracion:
                    return f"Ha ocurrido un error integrando el siguiente bloque en la blockchain {bloque_nuevo}"
        return f"Blockchain creada correctamente"

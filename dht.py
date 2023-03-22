import simpy
import random
from enum import Enum

class MessageType(Enum):
    JOIN_REQUEST = 1
    UPDATE_NEIGHBORS = 2

class Message:
    
    def __init__(self, type, value = None):
        self.type = type
        self.value = value

class DHT:

    network = {}

    def __init__(self, env):
        self.env = env


    def generate_unique_id(self):
        exclude = [node.id for node in DHT.network.values()]
        new_id = random.randint(0,1000)
        while new_id in exclude:
            new_id = random.randint(0,1000)
            
        return new_id
    
    def generate_unique_ip(self):
        exclude = [ip for ip in DHT.network.keys()]
        new_ip = random.randint(0,100000)
        while new_ip in exclude:
            new_ip = random.randint(0,100000)
            
        return new_ip

    def create_node(self, env):
        id = self.generate_unique_id()
        ip = self.generate_unique_ip()

        node = Node(env, id, ip)

        node.join(DHT.network.keys())

        DHT.network[ip] = node # Ajouter node a la table des adresses
        
        

class Node:
    
    def __init__(self, env, id, ip):
        self.env = env
        self.id = id
        self.ip = ip
        self.leftNeighbors = []
        self.rightNeighbors = []
        self.wait_for_message_proc = env.process(self.wait_for_message())
        self.wait_for_message_reactivate = env.event()

    def wait_for_message(self):
        while True:
            print(DHT.network)
            print(self.rightNeighbors)
            print(self.leftNeighbors)
            message = yield self.wait_for_message_reactivate # LA enfait soucis
            print("jai passé")
            self.receive_message(message)

    def join(self, ips):
        if not len(ips): # Cas particulier 1 noeud
            self.leftNeighbors = [self.ip]
            self.rightNeighbors = [self.ip]
            return 
        
        if len(ips) == 1: # Cas particulier 2 noeuds
            ip_neighbor = list(DHT.network.keys())[0] # Get node ip
            self.leftNeighbors =  [ip_neighbor]
            self.rightNeighbors = [ip_neighbor]
            message = Message(MessageType.UPDATE_NEIGHBORS, [self.ip, "both"])
            print(str(self.env.now) + " j'envoie")
            self.send_message(ip_neighbor, message)
            # Retour message ?
            return 



        # ip_to_contact = random.choice(list(ips))
        # self.send_message(ip_to_contact)
        
        # Gérer la suite

    def send_message(self, ip, message):
        node = DHT.network[ip]
        print(str(self.env.now) + " " + str(self.ip)  + " en train'envoyer à " + str(ip))
        print(node.wait_for_message_reactivate.triggered)
        node.wait_for_message_reactivate.succeed(message) # TESTS nécessaires ici
        print(node.wait_for_message_reactivate.triggered)
        node.wait_for_message_reactivate = self.env.event()

    def receive_message_proc(self, message): # Transformer en process
    
        if message.type == MessageType.UPDATE_NEIGHBORS:
            self.handle_update_neighbors(message.value)

        return    

    def handle_update_neighbors(self, value):
        ip = value[0]
        which = value[1] # left, right, or both
        if which == "both":
            self.leftNeighbors = ip
            self.rightNeighbors = ip

        elif which == "left":
            self.leftNeighbors = ip

        elif which == "right":
            self.rightNeighbors = ip

        return True

    def leave(self):
        pass
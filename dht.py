import simpy
import random
from enum import Enum
import logging

class MessageType(Enum):
    JOIN_REQUEST = 1
    UPDATE_NEIGHBORS = 2
    OK = 3
    CAN_JOIN = 4

class Message:
    
    def __init__(self, type, sender, value = None):
        self.type = type
        self.value = value
        self.sender = sender 

class DHT:

    network = {}

    def __init__(self, env):
        self.env = env

    
    def __str__(self):
        start_node = list(DHT.network.values())[0]
        string = ""
        node = start_node
        string += f"{node.id}<-->"
        while DHT.network[node.rightNeighbors[0]] != start_node:
            node = DHT.network[node.rightNeighbors[0]]
            string += f"{node.id}<-->"
        
        return string

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
        DHT.network[ip] = node # Ajouter node a la table des adresses de la DHT
        logging.debug(f"{env.now} - CREATING NODE FOR {ip} WITH VALUE {id}")
        env.process(node.join(DHT.network.keys()))


def transport(env, dest, message):
    yield env.timeout(1)
    dest.receive_message(message)
        
        

class Node:
    
    def __init__(self, env, id, ip):
        self.env = env
        self.id = id
        self.ip = ip
        self.leftNeighbors = []
        self.rightNeighbors = []
        self.alive = True
        self.ok_received = env.event()
        self.can_join = env.event()

    def join(self, ips):

        join_delay = self.env.timeout(1)

        logging.debug(f"{self.env.now} - {self.ip} trying to join network of length {len(DHT.network)}")

        if len(ips) == 1: # Cas particulier 1 noeud
            self.leftNeighbors = [self.ip]
            self.rightNeighbors = [self.ip]
            return 
            
        ip_to_contact = random.choice(list(DHT.network.keys()))
        message = Message(MessageType.JOIN_REQUEST, self.ip, (self.ip, self.id))
        self.env.process(self.send_message(ip_to_contact, message))

        yield self.can_join & join_delay # Join delay

        
    

    def send_message(self, ip_dest, message):
        logging.debug(f"{self.env.now} - {self.ip} sending {message.type.name} to {ip_dest}")
        dest = DHT.network[ip_dest]
        self.env.process(transport(self.env, dest, message))
        time_out = self.env.timeout(100) 
        ok = yield self.ok_received | time_out #regarder valeur ok pour svaoir crash

    def send_ok(self, ip_dest):
        dest = DHT.network[ip_dest]
        message = Message(MessageType.OK, self.ip)
        logging.debug(f"{self.env.now} - {self.ip} sending {message.type.name} to {ip_dest}")
        self.env.process(transport(self.env ,dest, message))
    

    def receive_message(self, message):
        logging.debug(f"{self.env.now} - {self.ip} received {message.type.name} from {message.sender}")
        if message.type == MessageType.JOIN_REQUEST:
            self.handle_join_request(message.value[0], message.value[1])
            logging.warning("aled")
            # A prendre en compte si un noeud crash pendant le ok
            # self.send_ok(message.sender)

        elif message.type == MessageType.UPDATE_NEIGHBORS:
            self.update_neighbors(**message.value)
            self.send_ok(message.sender)

        elif message.type == MessageType.CAN_JOIN:
            self.can_join.succeed()
            self.can_join = self.env.event()
            self.send_ok(message.sender)
           
        
        elif message.type == MessageType.OK:
            self.ok_received.succeed(message.sender)
            self.ok_received = self.env.event()


    def handle_join_request(self, ip_requester, id_requester):
        # Cas particulier 1 noeud
        if self.rightNeighbors == self.leftNeighbors:
            self.update_neighbors(left = ip_requester, right = ip_requester)
            message = Message(MessageType.UPDATE_NEIGHBORS, self.ip, {"left" : self.ip, "right" : self.ip})
            self.env.process(self.send_message(ip_requester, message))
            self.env.process(self.send_message(ip_requester, Message(MessageType.CAN_JOIN, self.ip)))

        

    def update_neighbors(self, **kwargs):
        if "left" in kwargs:
            self.leftNeighbors = [kwargs["left"]]
        if "right" in kwargs:
            self.rightNeighbors = [kwargs["right"]]
        logging.debug(f"{self.env.now} - updated neighbors {kwargs}")

            
        



    def leave(self):
        pass
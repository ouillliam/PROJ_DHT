import simpy
import random
from enum import Enum
import logging

class MessageType(Enum):
    JOIN_REQUEST = 1
    UPDATE_NEIGHBORS = 2
    OK = 3
    CAN_JOIN = 4
    DUMMY = 5


class Message:
    
    def __init__(self, type, sender, value = None, **kwargs):
        self.type = type
        self.value = value
        self.sender = sender 
        self.trace = kwargs["trace"] if "trace" in kwargs.keys() else []


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

    def create_node(self, env, id = None):
        if id is None:
            id = self.generate_unique_id()
        ip = self.generate_unique_ip()
        node = Node(env, id, ip)
        DHT.network[ip] = node # Ajouter node a la table des adresses de la DHT
        logging.debug(f"{env.now} - CREATING NODE FOR {ip} WITH VALUE {id}")
        env.process(node.join(DHT.network.keys()))
        return node 


# Simulate transport delay
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

    def join(self, ips, ip_debug = None):

        join_delay = self.env.timeout(1)

        logging.debug(f"{self.env.now} - {self.ip} trying to join network of length {len(DHT.network) - 1}")

        if len(ips) == 1: # Cas particulier 1 noeud
            self.leftNeighbors = [self.ip]
            self.rightNeighbors = [self.ip]
            return 
            
        # Selection d'un noeud au hasard à contacter qui n'est pas moi
        ip_to_contact = ip_debug
        if ip_debug is None:
            ip_to_contact = random.choice(list(DHT.network.keys()))
        while ip_to_contact == self.ip:
            ip_to_contact = random.choice(list(DHT.network.keys()))

        message = Message(MessageType.JOIN_REQUEST, self.ip, {"ip_dest" : self.ip,"id_dest" : self.id})
        self.env.process(self.send_message(ip_to_contact, message))

        yield self.can_join & join_delay # Join delay
        logging.info(f"{self.env.now} - JOIN : ({self.ip}, {self.id})")
   

    def deliver_message(self, id_dest, message):
        logging.debug(f"{self.env.now} - {self.id} DELIVERING {message.type.name} to {id_dest}")
        message.value["id_dest"] = id_dest
        self.route_message(message)


    def send_message(self, ip_dest, message): # REWORK DEST
        logging.debug(f"{self.env.now} - {self.ip} sending {message.type.name} to {ip_dest}")
        dest = DHT.network[ip_dest]
        message.trace.append((self.ip, self.id))
        self.env.process(transport(self.env, dest, message))
        if message.type == MessageType.OK:
            return 
        ok = yield self.ok_received  #regarder valeur ok pour svaoir crash

    def send_ok(self, ip_dest):
        message = Message(MessageType.OK, self.ip)
        self.env.process(self.send_message(ip_dest, message))
    

    def receive_message(self, message):
        logging.debug(f"{self.env.now} - {self.ip} received {message.type.name} from {message.sender}")
        if message.type == MessageType.JOIN_REQUEST:
            self.handle_join_request(message)
            self.send_ok(message.sender)

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

        elif message.type == MessageType.DUMMY:
            if message.value["id_dest"] == self.id:
                logging.debug(f"{self.env.now} - {self.id} received dummy {message.type.name} from {message.sender}")
                return
            self.route_message(message)
            


    def handle_join_request(self, message):

        ip_requester = message.value["ip_dest"]
        id_requester = message.value["id_dest"] 

        if self.rightNeighbors == self.leftNeighbors:
            # Cas particulier 1 noeuds
            if self.ip in self.rightNeighbors:
                self.update_neighbors(left = ip_requester, right = ip_requester)
                message = Message(MessageType.UPDATE_NEIGHBORS, self.ip, {"left" : self.ip, "right" : self.ip})
                self.env.process(self.send_message(ip_requester, message))

            # Cas particulier 2 noeuds
            else:
                self.insert_neighbor("left", ip_requester)
            self.env.process(self.send_message(ip_requester, Message(MessageType.CAN_JOIN, self.ip)))

        # Cas général
        else:
            direction_to_insert = self.check_can_be_inserted(id_requester)
            if  direction_to_insert is not None:
                self.insert_neighbor(direction_to_insert, ip_requester)
                self.env.process(self.send_message(ip_requester, Message(MessageType.CAN_JOIN, self.ip)))
                return

            self.route_message(message)
            

    def route_message(self, message):

        id_dest = message.value["id_dest"] 

        all_neighbors_ip = [*self.rightNeighbors, *self.leftNeighbors]

        all_neighbors_id_sorted = sorted([ DHT.network[ip].id for ip in all_neighbors_ip ])
        next_node_id = next( (neighbor_id for neighbor_id in all_neighbors_id_sorted[::-1] if neighbor_id < id_dest ) , all_neighbors_id_sorted[::-1][-1] )
        next_node_ip = [ip for ip, node in DHT.network.items() if node.id == next_node_id][0]

        # Remettre la condition d emort 

        # Avoid loop
        # while (next_node_ip, next_node_id) in message.trace:
        #     next_node_id = next( (neighbor_id for neighbor_id in all_neighbors_id_sorted[::-1] if neighbor_id < id_dest ) , all_neighbors_id_sorted[::-1][-1] )
        #     next_node_ip = [ip for ip, node in DHT.network.items() if node.id == next_node_id][0]
        print(list((neighbor_id for neighbor_id in all_neighbors_id_sorted[::-1] if neighbor_id < id_dest )))
        
        self.env.process(self.send_message(next_node_ip, message))

    def check_can_be_inserted(self, id_to_insert):
        
        id_left = DHT.network[self.leftNeighbors[0]].id
        id_right = DHT.network[self.rightNeighbors[0]].id

        # Cas particulier bout de cycle
        if (id_left > self.id and id_right > self.id ) or (id_left < self.id and id_right < self.id):
            # Si id to inster compris entre les bornes des voisins -> pas inserable ici
            if ( id_left > id_to_insert > id_right ) or ( id_left < id_to_insert < id_right ):
                return None
            # Si c'est inserable
            else :
                if self.id > max([id_left, id_right]): # Si on est sur le max de la DHT        
                    if id_to_insert > max([id_left, id_right]) and id_to_insert < self.id:
                        return "left" if max([id_left, id_right]) == id_left else "right"
                    else:
                        return "right" if max([id_left, id_right]) == id_left else "left"
                else: # Si on est sur le min de la DHT
                    if id_to_insert > self.id and id_to_insert < min([id_left, id_right]):
                        return "left" if min([id_left, id_right]) == id_left else "right"
                    else:
                        return "right" if min([id_left, id_right]) == id_left else "left"

        # Cas général
        if id_to_insert > self.id:
            if id_to_insert > max([id_left, id_right]):
                return None
            
            return "left" if max([id_left, id_right]) == id_left else "right"
        
        else:
            if id_to_insert < min([id_left, id_right]):
                return None

            return "left" if min([id_left, id_right]) == id_left else "right"

        
    def insert_neighbor(self, direction, ip_to_insert):

        # Contacter mon neighbor
        past_neighbor = None
        direction_neighbor = ""
        
        if direction == "left":
            past_neighbor = self.leftNeighbors[0]
            direction_neighbor = "right"
        else :
            past_neighbor = self.rightNeighbors[0]
            direction_neighbor = "left"

        message = Message(MessageType.UPDATE_NEIGHBORS, self.ip, {direction_neighbor : ip_to_insert})    
        self.env.process(self.send_message(past_neighbor, message))

        # Update mes neighbors
        kwargs = {}
        kwargs[direction] = ip_to_insert
        self.update_neighbors(**kwargs)  

        # Contacter le noeud qui rejoint
        neighbors_new_node = { "left" : past_neighbor, "right" : self.ip} if direction == "left" else { "left" : self.ip, "right" : past_neighbor}
        message = Message(MessageType.UPDATE_NEIGHBORS, self.ip, neighbors_new_node)    
        self.env.process(self.send_message(ip_to_insert, message))
        

    def update_neighbors(self, **kwargs):
        if "left" in kwargs:
            self.leftNeighbors = [kwargs["left"]]
        if "right" in kwargs:
            self.rightNeighbors = [kwargs["right"]]
        logging.debug(f"{self.env.now} - {self.ip} updated neighbors {kwargs}")

            

    def leave(self):
        logging.info(f"{self.env.now} - ({self.ip}, {self.id}) LEFT")
        if len(DHT.network) != 1:
            message = Message(MessageType.UPDATE_NEIGHBORS, self.ip, {"right" : self.rightNeighbors[0]})
            yield self.env.process(self.send_message(self.leftNeighbors[0], message))

            message = Message(MessageType.UPDATE_NEIGHBORS, self.ip, {"left" : self.leftNeighbors[0]})
            yield self.env.process(self.send_message(self.rightNeighbors[0], message))

        DHT.network.pop(self.ip)
        

import simpy
import random
from enum import Enum
import logging

# TO DO - GERE DATA INEXISTANT - GERER DATA AVEC LEAVE/AJOUT

class MessageType(Enum):
    JOIN_REQUEST = 1
    UPDATE_NEIGHBORS = 2
    OK = 3
    CAN_JOIN = 4
    DUMMY = 5
    STORE_DATA = 6
    REPLICATE = 7
    GET_DATA = 8
    RESPONSE_DATA = 9
    DELETE_DATA = 10
    DEPARTURE = 11
    RELOCATE = 12



class Message:
    
    def __init__(self, type, sender, value = None, **kwargs):
        self.type = type
        self.value = value
        self.sender = sender 
        self.trace = kwargs["trace"] if "trace" in kwargs.keys() else []

class Data:

    def __init__(self, value, **kwargs):
        if "id" in kwargs.keys(): 
            self.id = kwargs["id"]
        else: 
            self.id = self.generate_unique_data_id()
        
        self.value = value

    def generate_unique_data_id(self):
        exclude = [datum.id for datum in DHT.data.values()]
        new_id = random.randint(0,1000)
        while new_id in exclude:
            new_id = random.randint(0,1000)
            
        return new_id



class DHT:

    network = {}
    data = {}

    def __init__(self, env):
        self.env = env

    
    def __str__(self):
        start_node = list(DHT.network.values())[0]
        string = ""
        node = start_node
        string += f"{node.id}{list(node.data.keys())}<-->"
        while DHT.network[node.rightNeighbors[0]] != start_node:
            node = DHT.network[node.rightNeighbors[0]]
            string += f"{node.id}{list(node.data.keys())}<-->"
        
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

    # Simuler creation noeud et insertion
    def create_node(self, env, id = None):
        if id is None:
            id = self.generate_unique_id()
        ip = self.generate_unique_ip()
        node = Node(env, id, ip)
        DHT.network[ip] = node # Ajouter node a la table des adresses de la DHT
        logging.debug(f"{env.now} - CREATING NODE FOR {ip} WITH VALUE {id}")
        env.process(node.join(DHT.network.keys()))
        return node 
    
    # Simuler storage
    def store_data(self, env, value, id):
        datum = Data(value, id = id)
        node = random.choice(list(DHT.network.values()))
        logging.debug(f"{env.now} - TRYING TO STORE {datum.id} WITH VALUE {datum.value}")
        node.upload_data(datum)
        DHT.data[datum.id] = datum


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
        self.data = {}

    # Cette fonction existe pour simuler un individu qui lance un premier upload de data
    # Et donc creation d'un message correspondant
    def upload_data(self, data):
        if self.check_if_can_store(data):
            self.store(data)
            return 
        
        message = Message(MessageType.STORE_DATA, self.ip, {"id_dest" : data.id, "data" : data})
        self.route_message(message)


    def handle_store(self, message):
        data = message.value["data"]
        if self.check_if_can_store(data):
            self.store(data)
            message_replicate = Message(MessageType.REPLICATE, self.ip, {"data" : data})
            self.env.process(self.send_message(self.leftNeighbors[0], message_replicate))
            self.env.process(self.send_message(self.rightNeighbors[0], message_replicate))
            return

        self.route_message(message)

    def check_if_can_store(self, data):
        all_neighbors_ip = [*self.rightNeighbors, *self.leftNeighbors]
        all_neighbors_id = [ DHT.network[ip].id for ip in all_neighbors_ip ]

        diff_self = abs(data.id - self.id)
        diff_neighbors = [ abs(data.id - id_neighbor) for id_neighbor in all_neighbors_id]

        if all([diff_self <= diff_n for diff_n in diff_neighbors]):
            return True
        
        return False

    def store(self, data):
        if data in self.data.values():
            logging.info(f"{self.env.now} - ({data.id}, {data.value}) data already present in {self.id}")
            return 
        logging.info(f"{self.env.now} - {self.id} STORING ({data.id}, {data.value})")
        self.data[data.id] = data


    def get_data(self, id_data):
        message = Message(MessageType.GET_DATA, self.ip, {"id_dest" : id_data, "ip_requester" : self.ip})
        self.route_message(message)


    def handle_get_data(self, message):
        # Prendre en compte id inexistant ?
        id_data = message.value["id_dest"]
        ip_requester = message.value["ip_requester"]

        if id_data in self.data.keys():
            self.env.process(self.send_message(ip_requester, Message(MessageType.RESPONSE_DATA, self.ip, {"data" : self.data[id_data]})))
            return 
        
        self.route_message(message)

    def join(self, ips, ip_debug = None):

        logging.debug(f"{self.env.now} - ({self.ip}, {self.id}) trying to join network of length {len(DHT.network) - 1}")

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

        join_delay = self.env.timeout(1)
        yield self.can_join & join_delay
        self.relocate_fitting_data()
        logging.info(f"{self.env.now} - JOIN : ({self.ip}, {self.id})")
   
    def relocate_fitting_data(self):
        adjacent_neighbors_ip = [self.leftNeighbors[0], self.rightNeighbors[0]]
        adjacent_neighbors = [DHT.network[ip] for ip in adjacent_neighbors_ip]
        for neighbor in adjacent_neighbors:
            # Itérer sur les données originales du voisin
            for data in (data for data in neighbor.data.values() if data not in neighbor.get_replicated_data()):
                if self.check_if_can_store(data):
                    logging.debug(f"{self.env.now} - ({self.ip}, {self.id}) RELOCATING DATA {data.id}")
                    self.data[data.id] = data
                    



    def deliver_message(self, id_dest, message):
        logging.debug(f"{self.env.now} - {self.id} DELIVERING {message.type.name} to {DHT.network[id_dest].id}")
        message.value["id_dest"] = id_dest
        self.route_message(message)


    def send_message(self, ip_dest, message): # REWORK DEST
        logging.debug(f"{self.env.now} - {self.id} sending {message.type.name} to {DHT.network[ip_dest].id}")
        dest = DHT.network[ip_dest]
        message.trace.append((self.ip, self.id))
        self.env.process(transport(self.env, dest, message))
        if message.type == MessageType.OK:
            return 
        ok = yield self.ok_received  #regarder valeur ok pour svaoir crash

    def send_ok(self, ip_dest, in_response_to = None):
        message = Message(MessageType.OK, self.ip)
        self.env.process(self.send_message(ip_dest, message))

    

    def receive_message(self, message):
        logging.debug(f"{self.env.now} - {self.id} received {message.type.name} from {DHT.network[message.sender].id}")
        if message.type == MessageType.JOIN_REQUEST:
            self.handle_join_request(message)
            self.send_ok(message.sender, message)

        elif message.type == MessageType.UPDATE_NEIGHBORS:
            self.update_neighbors(**message.value)
            self.send_ok(message.sender, message)

        elif message.type == MessageType.CAN_JOIN:
            self.can_join.succeed()
            self.can_join = self.env.event()
            self.send_ok(message.sender, message)
           
        elif message.type == MessageType.OK:
            self.ok_received.succeed(message.sender)
            self.ok_received = self.env.event()

        elif message.type == MessageType.DUMMY:
            if message.value["id_dest"] == self.id:
                logging.debug(f"{self.env.now} - SUCCESSFUL DELIVERY TO {self.id} from {message.trace[0]}")
                return
            self.route_message(message)
            self.send_ok(message.sender, message)

        elif message.type == MessageType.STORE_DATA:
            self.handle_store(message)
            self.send_ok(message.sender, message)

        elif message.type == MessageType.REPLICATE:
            self.store(message.value["data"])
            self.send_ok(message.sender, message)

        elif message.type == MessageType.GET_DATA:
            self.handle_get_data(message)
            self.send_ok(message.sender, message)

        elif message.type == MessageType.RESPONSE_DATA:
            logging.info(f"{self.env.now} - {self.id} RECEIVED DATA {message.value['data'].id}")
            
        elif message.type == MessageType.DEPARTURE:
            self.handle_departure(message)
            self.send_ok(message.sender, message)
        
        elif message.type == MessageType.DELETE_DATA:
            self.handle_delete_data(message)
            self.send_ok(message.sender, message)

        elif message.type == MessageType.RELOCATE:
            self.handle_relocate(message)
            self.send_ok(message.sender, message)


    def handle_delete_data(self, message):
        id_data = message.value["id_data"]
        self.data.pop(id_data)




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
       
        # reverse list to find first id that is smaller than id_dest, otherwise smallest neighbor
        smaller_neighbors_iter = (neighbor_id for neighbor_id in all_neighbors_id_sorted[::-1] if neighbor_id < id_dest )

        bigger_neighbors_iter = (neighbor_id for neighbor_id in all_neighbors_id_sorted if neighbor_id > id_dest )

        next_node_id = None
        next_node_ip = None

        order_cond = id_dest < self.id

        while (next_node_ip, next_node_id) in message.trace or (next_node_ip, next_node_id) == (None, None) :
            # Si on est déjà passé par le noeud choisi, on essaie dans l'autre sens
            if (next_node_ip, next_node_id) in message.trace:
                order_cond = id_dest > self.id

            if order_cond:
                next_node_id = next( smaller_neighbors_iter, all_neighbors_id_sorted[::-1][-1] )
            else:
                next_node_id = next( bigger_neighbors_iter, all_neighbors_id_sorted[-1] )

            next_node_ip = [ip for ip, node in DHT.network.items() if node.id == next_node_id][0]
      
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

        past_neighbor = DHT.network[past_neighbor]

        message = Message(MessageType.UPDATE_NEIGHBORS, self.ip, {direction_neighbor : ip_to_insert})    
        self.env.process(self.send_message(past_neighbor.ip, message))

        # Update mes neighbors
        kwargs = {}
        kwargs[direction] = ip_to_insert
        self.update_neighbors(**kwargs)  
        

        # Contacter le noeud qui rejoint
        neighbors_new_node = { "left" : past_neighbor.ip, "right" : self.ip} if direction == "left" else { "left" : self.ip, "right" : past_neighbor.ip}
        message = Message(MessageType.UPDATE_NEIGHBORS, self.ip, neighbors_new_node)    
        self.env.process(self.send_message(ip_to_insert, message))
        

    def update_neighbors(self, **kwargs):

        if "left" in kwargs:
            self.leftNeighbors = [kwargs["left"]]
        if "right" in kwargs:
            self.rightNeighbors = [kwargs["right"]]

        logging.debug(f"{self.env.now} - {self.ip} updated neighbors {kwargs}")
        
    
    def get_replicated_data(self):
        # Données répliquées sur moi = données sur moi et un voisin mais pas l'autre
        return [ data for data in self.data.values() if ( data in DHT.network[self.leftNeighbors[0]].data.values() and data not in DHT.network[self.rightNeighbors[0]].data.values() ) or
                            ( data not in DHT.network[self.leftNeighbors[0]].data.values() and data in DHT.network[self.rightNeighbors[0]].data.values()) ]

        
        
    def handle_departure(self, message):
        replicated_data = message.value["replicated_data"]
        for data in replicated_data:
           self.store(data)
               
            


    def leave(self):
        logging.info(f"{self.env.now} - ({self.ip}, {self.id}) LEFT")
        
        if len(DHT.network) != 1:
            #Mettre à jour les voisins des voisins
            message = Message(MessageType.UPDATE_NEIGHBORS, self.ip, {"right" : self.rightNeighbors[0]})
            yield self.env.process(self.send_message(self.leftNeighbors[0], message))

            message = Message(MessageType.UPDATE_NEIGHBORS, self.ip, {"left" : self.leftNeighbors[0]})
            yield self.env.process(self.send_message(self.rightNeighbors[0], message))
            
            # Restocker mes données répliquées
            message = Message(MessageType.DEPARTURE, self.ip, {"replicated_data" : self.get_replicated_data()} )
            yield self.env.process(self.send_message(self.leftNeighbors[0], message))
            yield self.env.process(self.send_message(self.rightNeighbors[0], message))     
            
            # Restocker mes données originales
            for data in (data for data in self.data.values() if data not in self.get_replicated_data()):
                message = Message(MessageType.STORE_DATA, self.ip, {"id_dest" : data.id, "data" : data})
                yield self.env.process(self.send_message(self.leftNeighbors[0], message))
                
                
                
        
        

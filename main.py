from dht import Node, DHT, MessageType, Message
import simpy
import logging



env = simpy.Environment()
logging.basicConfig(filename='logs.txt', filemode='w', format='%(levelname)s - %(message)s', level=logging.DEBUG)
num_nodes = 5
dht = DHT(env)
for i in range(num_nodes):
    dht.create_node(env, i * 10)
    env.run()
node = dht.create_node(env, 50)
env.run()
node.deliver_message(20, Message(MessageType.DUMMY, node.ip, {}))
env.run()

print(dht)

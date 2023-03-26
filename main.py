from dht import Node, DHT, MessageType, Message, Data
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
dht.store_data(env, 'test', 25)
env.run()
node = node = dht.create_node(env, 17)
env.run()
node.get_data(25)
env.run()
print(dht)

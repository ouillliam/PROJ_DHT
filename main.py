from dht import Node, DHT
import simpy
import logging



env = simpy.Environment()
logging.basicConfig(filename='logs.txt', filemode='w', format='%(levelname)s - %(message)s', level=logging.DEBUG)
num_nodes = 3
dht = DHT(env)
for i in range(num_nodes):
    dht.create_node(env)
    env.run()
node = dht.create_node(env)
env.run()
print(dht)
env.process(node.leave())
env.run()
print(dht)
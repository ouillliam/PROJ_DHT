from dht import Node, DHT, MessageType, Message, Data
import simpy
import logging

with open('logs.txt', 'w+'):
    pass

env = simpy.Environment()
logging.basicConfig(filename='logs.txt', filemode='w', format='%(levelname)s - %(message)s')
num_nodes = 5
dht = DHT(env)
for i in range(num_nodes):
    dht.create_node(env, i * 10)
    env.run()
node = dht.create_node(env, 50)
env.run()
node = dht.create_node(env, 17)
env.run()
dht.store_data(env, 'test', 24)
env.run()
node.get_data(24)
dht.store_data(env, 'fefe', 14)
env.run()
env.process(node.leave())
env.run()
DHT.network.pop(node.ip)
print(dht)
print((list( node for node in DHT.network.values() if node.id == 0))[0].data)


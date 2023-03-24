from dht import Node, DHT
import simpy
import logging



env = simpy.Environment()
logging.basicConfig(filename='logs.txt', filemode='w', format='%(levelname)s - %(message)s', level=logging.DEBUG)
dht = DHT(env)
dht.create_node(env)
env.run()
dht.create_node(env)
env.run()

print(dht)
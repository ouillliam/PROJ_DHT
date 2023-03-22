from dht import Node, DHT
import simpy

env = simpy.Environment()

dht = DHT(env)
dht.create_node(env)
dht.create_node(env)
env.run(until=10)
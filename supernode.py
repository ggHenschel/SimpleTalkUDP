import argparse
import json
import pickle
import threading
import struct

#DEFINES
CONNECT_REQUEST = "1"
DISCONNECT_MESSAGE = "2"
MESSAGE_SINGLE = "41"
MESSAGE_ALL = "42"
REQUEST_LIST = "43"
LIST_SENT = "44"
UNAUTHORIZED = "401"
FORBIDDEN = "403"
OK = "200"
NOT_FOUND = "404"
PAYMENT_REQUIRED = "402"

class Supernode:

    def __init__(self,UDP_IP,UDP_PORT,data='data'):
        import socket

        ttl = struct.pack('b',1)
        self.multicastgroup = ("224.168.3.5",30056)
        self.group = socket.inet_aton(self.multicastgroup[0])

        self.m_sock = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP
        self.m_multicas_socket = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)
        try:
            self.m_sock.bind((UDP_IP, UDP_PORT))
            self.m_multicas_socket.setsockopt(socket.IPPROTO_IP,socket.IP_MULTICAST_TTL,32)
            self.m_multicas_socket.settimeout(0.2)
        except:
            print("Failed To Bind to port",UDP_PORT,"... Shuting Down")
            quit(-1)

        self.registred = dict()

        with open(data,'r') as fdata:
            clients = [json.loads(u) for u in fdata]
            for client in clients:
                self.registred[client["user"]]=client["pass"]

        self.connected_ips = dict()

    def run(self):
        while True:
            data, addr = self.m_sock.recvfrom(1024)  # buffer size is 1024 bytes
            code, d_data = pickle.loads(data)
            handler = Handler(addr,code,d_data,self)
            if addr[0] in self.connected_ips:
                th = threading.Thread(target=handler.handle_connected)
            else:
                th = threading.Thread(target=handler.handle_not_connected)
            th.start()

    def check_client(self,client,password,ip,port):
        if client in self.registred and self.registred[client] == password:
            if self.check_if_connected(client) and client != self.connected_ips[ip][0]:
                self.m_sock.sendto(pickle.dumps((UNAUTHORIZED, '')), (ip, port))
                return False

            self.connected_ips[ip]=(client,port)
            self.m_sock.sendto(pickle.dumps((OK,self.multicastgroup)),(ip,port))
            #DO MULTICAST
            return True
        else:
            self.m_sock.sendto(pickle.dumps((UNAUTHORIZED, '')),(ip,port))
            return False

    def check_if_connected(self,client):
        for _,(i_client,_) in self.connected_ips.items():
            if i_client == client:
                return True

        return False

    def send_forbiden(self,ip):
        port = self.connected_ips[ip][1]
        self.m_sock.sendto(pickle.dumps((FORBIDDEN, '')),(ip,port))

    def disconnect_client(self,ip):
        client, port = self.connected_ips[ip]
        self.connected_ips.pop(ip)
        self.m_sock.sendto(pickle.dumps((DISCONNECT_MESSAGE, 'OK')), (ip, port))
        print("Client", ip, client, "Disconnected")
        f_msg = "SERVER Warning: " + client + " disconnected with ip :" + ip + " ."
        self.m_multicas_socket.sendto(pickle.dumps((MESSAGE_ALL, f_msg)), self.multicastgroup)

    def send_list_to(self,ip):
        list = []
        port = self.connected_ips[ip][1]
        for l_ip,(user,l_port) in self.connected_ips.items():
            list.append((user,l_ip,l_port))
        self.m_sock.sendto(pickle.dumps((LIST_SENT, list)), (ip, port))

    def multicast_message(self,ip,message):
        client = self.connected_ips[ip][0]
        f_msg="From "+client+"("+ip+"):"+message
        self.m_multicas_socket.sendto(pickle.dumps((MESSAGE_ALL,f_msg)),self.multicastgroup)

    def multicast_connect(self,ip):
        client = self.connected_ips[ip][0]
        f_msg = "SERVER Warning: "+client+" connect with ip: "+ip+" ."
        self.m_multicas_socket.sendto(pickle.dumps((MESSAGE_ALL, f_msg)), self.multicastgroup)



class Handler:
    def __init__(self,addr,code,d_data,super_node):
        self.addr, self.port = addr
        self.code = code
        self.d_data = d_data
        self.super_node = super_node

    def handle_connected(self):
        if self.code == CONNECT_REQUEST:
            client, passw, port = self.d_data
            if self.super_node.check_client(client, passw, self.addr, port):
                print("Existing client", self.addr, client,"reconnect.")
                self.super_node.multicast_connect(self.addr)
            else:
                self.super_node.disconnect_client(self.addr)
        elif self.code == REQUEST_LIST:
            self.super_node.send_list_to(self.addr)
        elif self.code == DISCONNECT_MESSAGE:
            self.super_node.disconnect_client(self.addr)
        elif self.code == MESSAGE_SINGLE:
            self.super_node.send_forbiden(self.addr)
        elif self.code == MESSAGE_ALL:
            self.super_node.multicast_message(self.addr,self.d_data)




    def handle_not_connected(self):
        if self.code == CONNECT_REQUEST:
            client, passw, port = self.d_data
            if self.super_node.check_client(client,passw,self.addr,port):
                print("new client",self.addr, client)
                self.super_node.multicast_connect(self.addr)
            else:
                print("new client failed to connect", self.addr)
        else:
            print("Not connect Message from", self.addr)
            self.super_node.send_forbiden(self.addr,self.port)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-uf','--userfile',dest='userfile',default='data',help='path to new user files (old one will be replaced)')
    parser.add_argument('-rp','--recevingPort',dest='rport',default=5005,type=int,help='listening port for supernode')

    args = parser.parse_args()

    key = "SuperDuperKey"

    if not args.userfile == 'data':
        with open('data','w') as data_file, open(args.userfile,'r') as uf:
            data_file.write(uf.read())

    super_node = Supernode('',args.rport)
    super_node.run()

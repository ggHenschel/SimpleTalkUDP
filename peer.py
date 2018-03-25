import socket, pickle
import getpass
import threading as th
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

class Client:
    def __init__(self,server_ip,server_port=5005,client_port=5006):
        self.sock_out = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP

        self.server_ip=server_ip
        self.server_port=server_port
        self.own_port=client_port

        try:
            self.sock_in = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP
            self.sock_in.bind(('',client_port))
            self.sock_multi = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM,
                             socket.IPPROTO_IP)
            try:
                self.sock_multi.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except AttributeError:
                pass
            self.sock_multi.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
            self.sock_multi.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        except Exception as e:
            print(e)
            quit(-1)

    def open_connection(self):
        count = 0
        while count<3:
            user = input("Username:")
            passw = getpass.getpass("Password:")
            connect_msg = (CONNECT_REQUEST,(user,passw,self.own_port))
            self.sock_out.sendto(pickle.dumps(connect_msg), (self.server_ip, self.server_port))
            try:
                data, addr = self.sock_in.recvfrom(1024)
            except Exception as e:
                print(e)

            code, d_data = pickle.loads(data)
            if code == OK:
                print("Welcome!")
                self.multicastgroup, self.multicastport = d_data
                self.m_connected = True
                self.group = socket.inet_aton(self.multicastgroup)
                self.mreq = struct.pack('4sL',self.group,socket.INADDR_ANY)
                self.sock_multi.bind((self.multicastgroup,self.multicastport))
                try:
                    host = socket.gethostbyname(socket.gethostname())
                except:
                    host = '192.168.3.1'
                print(host)
                self.sock_multi.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(host))
                self.sock_multi.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP,
                                socket.inet_aton(self.multicastgroup) + socket.inet_aton(host))
                break
            elif code == UNAUTHORIZED:
                print("Access Denied. Wrong User/Password")
                count += 1
            else:
                print("Unknown Error. Please Try Again")

        #start listening
        if self.m_connected:
            listener = th.Thread(target=self.client_listener)
            listener.start()
            listener_m = th.Thread(target=self.multicast_listener)
            listener_m.start()
            #start
            print("Type command /c to message all, /list to request ips, /m IP:PORT message to message someone, /quit to leave server")

        while self.m_connected:
            console = input()
            try:
                s1, s2 = console.split(' ',maxsplit=1)
            except:
                s1 = console

            if s1 == '/c':
                code = MESSAGE_ALL
                data = s2
                ip = self.server_ip
                port = self.server_port
                msg_to_send = True
            elif s1 == '/list':
                code = REQUEST_LIST
                data = ''
                ip = self.server_ip
                port = self.server_port
                msg_to_send = True
            elif s1 == '/m':
                addr , msg = s2.split(' ',maxsplit=1)
                ip , port = addr.split(':',maxsplit=1)
                code = MESSAGE_SINGLE
                data = msg
                msg_to_send = True
            elif s1 == '/quit':
                code = DISCONNECT_MESSAGE
                data = ''
                ip = self.server_ip
                port = self.server_port
                msg_to_send = True
                self.m_connected = False
            elif s1 == '/help' or s1 == '/h':
                print("Type command /c to message all, /list to request ips, /m IP:PORT message to message someone, /quit to leave server")
                msg_to_send = False
            else:
                print("Command not Found. Use /help or /h for usage.")
                msg_to_send = False

            if msg_to_send:
                self.sock_out.sendto(pickle.dumps((code,data)), (ip, int(port)))

        print("Bye")
        try:
            listener.join(timeout=10)
        except:
            listener._delete()

        try:
            self.sock_in.close()
        finally:
            self.sock_out.close()

    def multicast_listener(self):
        try:
            while self.m_connected:
                data, addr = self.sock_multi.recvfrom(1024)  # buffer size is 1024 bytes
                code, d_data = pickle.loads(data)
                if code == MESSAGE_ALL:
                    print(d_data)
                else:
                    print("unkown code received from multicast port")
        except KeyboardInterrupt:
            pass
        finally:
            self.sock_multi.close()

    def client_listener(self):
        try:
            while self.m_connected:
                data, addr = self.sock_in.recvfrom(1024)  # buffer size is 1024 bytes
                code, d_data = pickle.loads(data)
                if code == MESSAGE_SINGLE:
                    print("[p]",addr[0],":",d_data)
                elif code == LIST_SENT:
                    print(d_data)
                elif code == DISCONNECT_MESSAGE:
                    print("You have been Disconnect.")
                    self.m_connected = False
                elif code == FORBIDDEN:
                    print("Your last Message was flagged as Forbidden\nYou may not have rights to do your last action\nOr you tried to message the server.")
                else:
                    print("unkown code received")
        except KeyboardInterrupt:
            pass
        finally:
            self.sock_in.close()





#Hard Coded
UDP_IP = "192.168.3.241"
UDP_PORT = 5005


print("UDP target IP:", UDP_IP)
print("UDP target port:", UDP_PORT)

client = Client(UDP_IP,UDP_PORT)
client.open_connection()


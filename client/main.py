import socket
import os
import hashlib
import time

CHUNK_SIZE = 1024
PORT = 12345
SERVER_HOST = '127.0.0.1'
MODE = dict(send=0, recv=1)
USER = 'ARYA'

def calculate_checksum(file_path):
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def client():

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_HOST, PORT))
        client_socket.sendall(USER.encode())
        time.sleep(.5)
        mode = input("Enter mode (send/receive): ")
        client_socket.sendall(mode.encode('utf-8'))
        time.sleep(.5)
        mode = MODE.get(mode)

        if mode == 0:
            file_path = input("Enter the path of the file to send: ")
            if not os.path.exists(file_path):
                print("File does not exist.")
                return

            file_size = os.path.getsize(file_path)
            file_name = file_path.split('/')[-1]
            client_socket.sendall(file_name.encode())
            time.sleep(.5)
            time.sleep(.5)
            total_chunks = (file_size // CHUNK_SIZE) + (1 if file_size % CHUNK_SIZE != 0 else 0)
            client_socket.sendall(str(total_chunks).encode('utf-8'))
            sent_chunks = set()
            chunks = {}

            with open(file_path, 'rb') as f:
                for i in range(total_chunks):
                    chunks[i] = f.read(CHUNK_SIZE)

            ack_or_retrans = None
            for chunk_num in range(total_chunks):
                seq_num_header = f"{chunk_num:<16}".encode('utf-8')
                client_socket.sendall(seq_num_header + chunks[chunk_num])
                time.sleep(.5)
                sent_chunks.add(chunk_num)
                ack_or_retrans = client_socket.recv(1024).decode('utf-8')

                if ack_or_retrans.startswith("RE"):
                    retrans_chunk_num = int(ack_or_retrans.split(' ')[1])
                    print(f"Retransmitting chunk {retrans_chunk_num}")
                    retrans_seq_num_header = f"{retrans_chunk_num:<16}".encode('utf-8')
                    client_socket.sendall(retrans_seq_num_header + chunks[retrans_chunk_num])
                    time.sleep(.5)
                else:
                    print("Server Acked: ", ack_or_retrans, "chunk number", chunk_num)
            

            checksum = calculate_checksum(file_path)
            client_socket.sendall(checksum.encode('utf-8'))
            time.sleep(.5)

        elif mode == 1:
            file_name = client_socket.recv(1024).decode('utf-8')
            file_path = os.path.join('received/', file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            print("File name: ", file_name)
            file_path = os.path.join('received', file_name)

            with open(file_path, 'wb') as f:
                chunks_received = {}
                expected_chunks = int(client_socket.recv(1024).decode('utf-8'))
                print(f"Expecting {expected_chunks} chunks from client")

                while len(chunks_received) < expected_chunks:
                    data = client_socket.recv(CHUNK_SIZE + 16)
                    if not data:
                        break
                    seq_num = int(data[:16].decode('utf-8').strip())
                    chunk = data[16:]
                    chunks_received[seq_num] = chunk

                    print(f"Received chunk {seq_num} Progress {int((seq_num/expected_chunks)*100)} %")
                    client_socket.sendall(f"ACK {seq_num}".encode('utf-8'))
                    time.sleep(.5)

                for seq_num in sorted(chunks_received.keys()):
                    f.write(chunks_received[seq_num])

            print("File received successfully.")


        client_socket.close()
    except Exception as e:
        print('Exception Caught', e.__str__())

if __name__ == "__main__":
    client()

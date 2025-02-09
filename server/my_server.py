import socket
import os
import hashlib
import time
import random
import sys
import re

RETRANSMIT = False
if len(sys.argv) > 1 and sys.argv[1] == "test":
    print('retransmit Active')
    RETRANSMIT = True
CHUNK_SIZE = 1024
MAX_CHUNKS = 5
PORT = 12345
SERVER_HOST = '127.0.0.1'
MODE = dict(send=0, recv=1)

def calculate_checksum(file_path):
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, PORT))
    server_socket.listen(5)
    print(f"Server listening on {SERVER_HOST}:{PORT}")

    conn, addr = server_socket.accept()
    print(f"Connection established with {addr}")
    try:
        client_name = conn.recv(1024).decode()
        mode = conn.recv(1024).decode('utf-8')
        print(f"Mode received from client: {mode}")

        mode = MODE.get(mode)

        if mode == 0:
            file_name = conn.recv(1024).decode('utf-8')
            file_path = os.path.join('received/' + client_name, file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            print("File name: ", file_name)
            file_path = os.path.join('received/' + client_name, file_name)

            with open(file_path, 'wb') as f:
                chunks_received = {}
                total_chunks_from_client = conn.recv(1024).decode('utf-8')
                expected_chunks = int(total_chunks_from_client)
                print(f"Expecting {expected_chunks} chunks from client")

                while len(chunks_received) < expected_chunks:
                    data = conn.recv(CHUNK_SIZE + 16)
                    if not data:
                        break
                    
                    temp = data[:16].decode('utf-8').strip()
                    if temp.isdigit():
                        seq_num = int(temp)
                    else:
                        break
                    if RETRANSMIT and random.choice([False, True]) and len(chunks_received) > 1:
                        conn.sendall(f'RE {seq_num}'.encode('utf-8'))
                        time.sleep(.5)
                        retransmitted_data = conn.recv(CHUNK_SIZE + 16).decode('utf-8')
                        retrans_seq_num = int(retransmitted_data.split(' ')[0])
                        retrans_chunk = retransmitted_data[16:]
                        chunks_received[retrans_seq_num] = retrans_chunk
                        print(f"Received chunk {retrans_seq_num} Progress {int((retrans_seq_num/expected_chunks)*100)} %aaa")
                        conn.sendall(f"ACK {retrans_seq_num}".encode('utf-8'))
                        time.sleep(.5)
                        print(f"Received retransmitted chunk {retrans_seq_num}")
                        continue

                    chunk = data[16:]
                    chunks_received[seq_num] = chunk

                    print(f"Received chunk {seq_num} Progress {int((seq_num/expected_chunks)*100)} %")
                    conn.sendall(f"ACK {seq_num}".encode('utf-8'))
                    time.sleep(.5)
                    

                for seq_num in sorted(chunks_received.keys()):
                    f.write(chunks_received[seq_num])

            print("File received successfully.")

            checksum = conn.recv(1024).decode('utf-8')
            local_checksum = calculate_checksum(file_path)
            if checksum == local_checksum:
                print("Checksum verified successfully.")
            else:
                print("Checksum mismatch detected.")

        elif mode == 1:
            file_path = input("Enter the path of the file to send: ")
            if not os.path.exists(file_path):
                print("File does not exist.")
                return

            file_size = os.path.getsize(file_path)
            file_name = file_path.split('/')[-1]
            conn.sendall(file_name.encode())
            time.sleep(.5)
            total_chunks = (file_size // CHUNK_SIZE) + (1 if file_size % CHUNK_SIZE != 0 else 0)
            conn.sendall(str(total_chunks).encode('utf-8'))
            time.sleep(.5)
            sent_chunks = set()
            chunks = {}

            with open(file_path, 'rb') as f:
                for i in range(total_chunks):
                    chunks[i] = f.read(CHUNK_SIZE)

            for chunk_num in range(total_chunks):
                seq_num_header = f"{chunk_num:<16}".encode('utf-8')
                conn.sendall(seq_num_header + chunks[chunk_num])
                time.sleep(.5)
                sent_chunks.add(chunk_num)
                ack = conn.recv(1024).decode('utf-8')
                print("Server Acked: ", ack, "chuck number", chunk_num)

            checksum = calculate_checksum(file_path)
            conn.sendall(checksum.encode('utf-8'))
            time.sleep(.5)

        conn.close()
        server_socket.close()
    except Exception as e:
        exc_type, exc_value, exc_tb = sys.exc_info()
        line_number = exc_tb.tb_lineno
        print(f"Exception occurred on line {line_number}: {e}")
        conn.close()
        server_socket.close()

if __name__ == "__main__":
    server()

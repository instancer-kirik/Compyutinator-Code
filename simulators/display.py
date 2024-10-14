import hashlib
import time

def proof_of_work(last_proof):
    proof = 0
    while valid_proof(last_proof, proof) is False:
        proof += 1
    return proof

def valid_proof(last_proof, proof):
    guess = f'{last_proof}{proof}'.encode()
    guess_hash = hashlib.sha256(guess).hexdigest()
    return guess_hash[:4] == "0000"

def simulate_mining():
    last_proof = 100
    start_time = time.time()
    proof = proof_of_work(last_proof)
    end_time = time.time()
    print(f"Mining simulated! Proof: {proof}")
    print(f"Time taken: {end_time - start_time} seconds")
from simulators.block_chain_simulator import BlockchainSimulator
from simulators.display import proof_of_work

class SimulatorModule:
    def __init__(self):
        self.blockchain = BlockchainSimulator()

    def simulate_block_creation(self):
        last_block = self.blockchain.last_block
        last_proof = last_block['proof']
        proof = proof_of_work(last_proof)
        self.blockchain.new_block(proof, None)
        print("New block simulated and added to the chain!")

    def simulate_transaction(self, sender, recipient, amount):
        index = self.blockchain.new_transaction(sender, recipient, amount)
        print(f"Transaction will be added to Block {index}")

    def view_chain(self):
        return self.blockchain.chain
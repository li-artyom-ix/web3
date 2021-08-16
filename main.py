from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/811ec3f711634180b065f03510610a5e'))
n = 13000000
txs = []
while n <=13000010:
    block = w3.eth.get_block(n).transactions
    for i in range(len(block)):
        txs.append(block[i].hex())
        print('Tx hash: '+txs[i])
    n += 1
print(len(txs))
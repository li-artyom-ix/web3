from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/811ec3f711634180b065f03510610a5e'))
startBlock = 13043889
endBlock = 13043890
coinbase4 = '0x3cD751E6b0078Be393132286c442345e5DC49699'
txs = []

while startBlock <= endBlock:
    block = w3.eth.get_block(startBlock).transactions
    for i in range(len(block)):
        txs.append(block[i].hex())
    startBlock += 1
for j in range(len(txs)):
    tx = w3.eth.get_transaction(txs[j])
    if tx['from'] == coinbase4 and tx['value'] < 50000000000000000 and tx['value'] > 0:
        print('Coinbase4 send ', w3.fromWei(tx['value'], 'ether'), ' to ', tx['to'])
        print('Etherscan link: https://etherscan.io/tx/', end='')
        print(tx['hash'].hex())
        print('\n')
    else:
        None

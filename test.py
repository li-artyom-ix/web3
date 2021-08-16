from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/811ec3f711634180b065f03510610a5e'))
addr = '0x3cD751E6b0078Be393132286c442345e5DC49699'


tx = '0xd9fea5d2eb47d9c7c35fe709eb53afca546a41d2724e84d5b24187e4b6c7382c'
o = w3.eth.get_transaction(tx)
value = w3.fromWei(o.value, 'ether')
print(o.from)

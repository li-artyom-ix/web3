import json
import time
import telebot
import secrets
import requests
from web3 import Web3
from eth_account import Account



# -------------------------------------
# |              Classes               |
# -------------------------------------


class Chain():
    def __init__(self, rpc, chain_id, stargate_chain_id, usdt_contract, usdc_contract, inch_contract,
                 susdt_contract, susdc_contract, stargate_router):
        self.rpc = rpc
        self.chain_id = chain_id
        self.stargate_chain_id = stargate_chain_id
        self.usdt_contract = usdt_contract
        self.usdc_contract = usdc_contract
        self.inch_contract = inch_contract
        self.susdt_contract = susdt_contract
        self.susdc_contract = susdc_contract
        self.stargate_router = stargate_router


class Acc():
    def __init__(self, private_key):
        self.private_key = private_key
        self.address = Account.privateKeyToAccount(private_key).address

    def balanceOf(self, chain, token_address):
        w3 = Web3(Web3.HTTPProvider(chain.rpc))
        token_abi = get_json_abi_from_file('erc20_abi.json')
        contract = w3.eth.contract(address=Web3.toChecksumAddress(token_address), abi=token_abi)
        function = contract.functions.balanceOf(Web3.toChecksumAddress(self.address)).call()
        return function

    def allowance(self, chain, token_address, spender_address):
        w3 = Web3(Web3.HTTPProvider(chain.rpc))
        token_abi = get_json_abi_from_file('erc20_abi.json')
        contract = w3.eth.contract(address=Web3.toChecksumAddress(token_address), abi=token_abi)
        function = contract.functions.allowance(Web3.toChecksumAddress(self.address),
                                                Web3.toChecksumAddress(spender_address)).call()
        return function

    def approve(self, chain, token_address, spender_address, amount):
        w3 = Web3(Web3.HTTPProvider(chain.rpc))
        token_abi = get_json_abi_from_file('erc20_abi.json')
        contract = w3.eth.contract(address=w3.toChecksumAddress(token_address), abi=token_abi)
        # Получите функцию из контракта
        function = contract.functions.approve(w3.toChecksumAddress(spender_address), amount)
        # Создайте транзакцию
        tx = function.buildTransaction({
            'from': self.address,
            'nonce': w3.eth.getTransactionCount(self.address),
            'gasPrice': w3.eth.gasPrice
        })
        tx_hash = sign_tx(w3, tx, self.private_key)
        check_transaction(w3, tx_hash)
        return tx_hash

    def swap_1inch(self, chain, fromTokenAddress, toTokenAddress, amount):
        w3 = Web3(Web3.HTTPProvider(chain.rpc))
        fromAddress = self.address
        slippage = '0.12'

        url = (f"https://api.1inch.io/v5.0/{chain.chain_id}/swap?fromTokenAddress={fromTokenAddress}&" +
               f"toTokenAddress={toTokenAddress}&" +
               f"amount={amount}&fromAddress={fromAddress}&slippage={slippage}")

        response = requests.get(url)
        data = json.loads(response.text)

        if 'tx' in data:
            tx = data['tx']
            tx['gasPrice'] = w3.eth.gasPrice
            tx['to'] = w3.toChecksumAddress(tx['to'])
            tx['gas'] = int(tx['gas'])
            tx['value'] = int(tx['value'])
            tx['nonce'] = w3.eth.getTransactionCount(self.address)
            tx['chainId'] = chain.chain_id

            tx_hash = sign_tx(w3, tx, self.private_key)
            check_transaction(w3, tx_hash)
            return tx_hash

        else:
            print(data['description'])
            return None  # или какое-то другое действие

    def lz_swap(self, chain, dstChain, asset, amount, poolId):
        lz_abi = get_json_abi_from_file('lz_abi.json')
        w3 = Web3(Web3.HTTPProvider(chain.rpc))
        contract = w3.eth.contract(address=chain.stargate_router, abi=lz_abi)
        _dstChainId = dstChain.stargate_chain_id
        _functionType = 1
        _toAddress = Web3.toChecksumAddress(self.address)
        _transferAndCallPayload = b'\x00'
        _lzTxParams = {'dstGasForCall': 0, 'dstNativeAmount': 0, 'dstNativeAddr': b'\x00'}
        function = contract.functions.quoteLayerZeroFee(_dstChainId, _functionType, _toAddress, _transferAndCallPayload,
                                                        _lzTxParams).call()
        feeWei = function[0]

        _srcPoolId = poolId
        _dstPoolId = poolId
        _refundAddress = _toAddress
        _amountLD = amount
        _minAmountLD = int(_amountLD * 0.987)
        _payload = b'\x00'

        function = contract.functions.swap(
            _dstChainId,
            _srcPoolId,
            _dstPoolId,
            _refundAddress,
            _amountLD,
            _minAmountLD,
            _lzTxParams,
            _toAddress,
            _payload)

        # Создайте транзакцию
        tx = function.buildTransaction({
            'from': self.address,
            'nonce': w3.eth.getTransactionCount(self.address),
            'gasPrice': w3.eth.gasPrice,
            'value': feeWei
        })

        tx_hash = sign_tx(w3, tx, self.private_key)
        check_transaction(w3, tx_hash)
        return tx_hash

    def lz_addLiq(self, chain, asset, amount, poolId):
        lz_abi = get_json_abi_from_file('lz_abi.json')
        w3 = Web3(Web3.HTTPProvider(chain.rpc))
        contract = w3.eth.contract(address=chain.stargate_router, abi=lz_abi)
        function = contract.functions.addLiquidity(poolId, amount, Web3.toChecksumAddress(self.address))
        tx = function.buildTransaction({
            'from': self.address,
            'nonce': w3.eth.getTransactionCount(self.address),
            'gasPrice': w3.eth.gasPrice
        })
        tx_hash = sign_tx(w3, tx, self.private_key)
        check_transaction(w3, tx_hash)
        return tx_hash

    def lz_removeLiq(self, chain, asset, amount, poolId):
        lz_abi = get_json_abi_from_file('lz_abi.json')
        w3 = Web3(Web3.HTTPProvider(chain.rpc))
        contract = w3.eth.contract(address=chain.stargate_router, abi=lz_abi)
        function = contract.functions.instantRedeemLocal(poolId, amount, Web3.toChecksumAddress(self.address))
        tx = function.buildTransaction({
            'from': self.address,
            'nonce': w3.eth.getTransactionCount(self.address),
            'gasPrice': w3.eth.gasPrice
        })
        tx_hash = sign_tx(w3, tx, self.private_key)
        check_transaction(w3, tx_hash)
        return tx_hash


# -------------------------------------
# |              Methods                |
# -------------------------------------


def get_json_abi_from_file(path):
    with open(path, 'r') as abi_file:
        token_abi = json.load(abi_file)
    return token_abi


def sign_tx(w3, tx, private_key):
    signed_transaction = w3.eth.account.signTransaction(tx, private_key)
    tx_hash = w3.eth.sendRawTransaction(signed_transaction.rawTransaction)
    return tx_hash


def check_transaction(w3, tx_hash):
    time.sleep(1)
    # Ждем, пока транзакция не будет включена в блок
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    # Проверяем статус транзакции
    # Если статус равен 1, то транзакция успешно выполнена
    # Если статус равен 0, то транзакция не была успешно выполнена
    if receipt.status:
        print("Транзакция успешно выполнена")
    else:
        print("Транзакция не была успешно выполнена")


def get_all_stable_balances(account):
    avax_usdt_balance = account.balanceOf(avax, avax.usdt_contract)
    avax_usdc_balance = account.balanceOf(avax, avax.usdc_contract)
    avax_susdt_balance = account.balanceOf(avax, avax.susdt_contract)
    avax_susdc_balance = account.balanceOf(avax, avax.susdc_contract)

    arb_usdt_balance = account.balanceOf(arb, arb.usdt_contract)
    arb_usdc_balance = account.balanceOf(arb, arb.usdc_contract)
    arb_susdt_balance = account.balanceOf(arb, arb.susdt_contract)
    arb_susdc_balance = account.balanceOf(arb, arb.susdc_contract)

    balances = {
        'avax_usdt': avax_usdt_balance,
        'avax_usdc': avax_usdc_balance,
        'avax_susdt': avax_susdt_balance,
        'avax_susdc': avax_susdc_balance,
        'arb_usdt': arb_usdt_balance,
        'arb_usdc': arb_usdc_balance,
        'arb_susdt': arb_susdt_balance,
        'arb_susdc': arb_susdc_balance,
    }

    print(f'Balance {account.address}: \n'
          f'Avalanche: {avax_usdt_balance / (10 ** 6)} USDT\n'
          f'Avalanche: {avax_usdc_balance / (10 ** 6)} USDC\n'
          f'Avalanche: {avax_susdt_balance / (10 ** 6)} USDT в ликвидности\n'
          f'Avalanche: {avax_susdc_balance / (10 ** 6)} USDC в ликвидности\n\n'
          f'Arbitrum: {arb_usdt_balance / (10 ** 6)} USDT\n'
          f'Arbitrum: {arb_usdc_balance / (10 ** 6)} USDC\n'
          f'Arbitrum: {arb_susdt_balance / (10 ** 6)} USDT в ликвидности\n'
          f'Arbitrum: {arb_susdc_balance / (10 ** 6)} USDC в ликвидности\n'
          )
    return balances


def generate_accounts(n, filename):
    accounts = []
    # Генерация n аккаунтов
    for _ in range(n):
        # Генерация случайной строки энтропии
        entropy = secrets.token_hex(32)  # 32 байта энтропии

        # Создание нового аккаунта
        new_account = Account.create(entropy)
        private_key = new_account.privateKey
        public_key = new_account.address

        accounts.append((public_key, private_key.hex()))

    # Открытие файла в режиме добавления
    with open(filename, 'a') as file:
        for account in accounts:
            file.write(f"{account[0]}:{account[1]}\n")
    return accounts


def read_from_file(filename):
    accounts = []

    # Открытие файла в режиме чтения
    with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
            # Удаление символа новой строки и разделение строки по двоеточию
            address, private_key = line.strip().split(":")
            accounts.append((address, private_key))
    return accounts

#Пока не используется
#Позволяет отправить любое сообщение в мой бот
def send_message(message):
    botTimeWeb = telebot.TeleBot('6161757026:AAFsT82CKYwcZ4ni-bTCf1OigE33YZuDTlw')
    botTimeWeb.send_message(chat_id="199857246", text=message)


def divider(amount):
    return amount / (10 ** 6)


if __name__ == "__main__":
    avax = Chain('https://rpc.ankr.com/avalanche', 43114, 106,
                 '0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7',
                 '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E',
                 '0x1111111254eeb25477b68fb85ed929f73a960582',
                 '0x29e38769f23701A2e4A8Ef0492e19dA4604Be62c',
                 '0x1205f31718499dBf1fCa446663B532Ef87481fe1',
                 '0x45A01E4e04F14f7A4a6702c74187c5F6222033cd'
                 )

    arb = Chain('https://arb-mainnet.g.alchemy.com/v2/mKv5VU8h-oXFQxTWL-vAoeOU02g2fhU-',
                42161, 110,
                '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9',
                '0xff970a61a04b1ca14834a43f5de4533ebddb5cc8',
                '0x1111111254eeb25477b68fb85ed929f73a960582',
                '0xB6CfcF89a7B22988bfC96632aC2A9D6daB60d641',
                '0x892785f33CdeE22A30AEF750F285E18c18040c3e',
                '0x53Bf833A5d6c4ddA888F69c22C88C9f356a41614')

    private_key = ''

    account = Acc(private_key)

    amount = account.balanceOf(avax, avax.usdc_contract)
    print(f'Avalanche USDC: {divider(amount)}')
    print('Проверяем разрешение на трату USDC для 1inch')
    allowance = account.allowance(avax, avax.usdc_contract, avax.inch_contract)
    if allowance > amount:
        print(f'Достаточно разрешения {divider(allowance)} USDC для обмена {divider(amount)} USDC')
    else:
        print(f'Не достаточно разрешения. Текущее кол-во: {divider(allowance)} USDC, необходимо {divider(amount)} USDC')
        print('Даем разрешение на трату')
        account.approve(avax, avax.usdc_contract, avax.inch_contract, amount)
    print(f'Меняем {divider(amount)} USDC на USDT')
    account.swap_1inch(avax, avax.usdc_contract, avax.usdt_contract, amount)

    amount = account.balanceOf(avax, avax.usdt_contract)
    print(f'Avalanche USDT: {divider(amount)} \n')
    allowance = account.allowance(avax, avax.usdt_contract, avax.stargate_router)
    if allowance > amount:
        print(f'Достаточно разрешения {divider(allowance)} USDT для отправки на Arbitrum')
    else:
        print(f'Не достаточно разрешения. Текущее кол-во: {divider(allowance)} USDT, необходимо {divider(amount)} USDT')
        print('Даем разрешение на трату')
        account.approve(avax, avax.usdt_contract, avax.stargate_router, amount)
    print(f'Отправляем {divider(amount)} USDT в Arbitrum')
    account.lz_swap(avax, arb, avax.usdt_contract, amount, 2)

    amount = account.balanceOf(arb, arb.usdc_contract)
    print(f'Arbitrum USDC: {divider(amount)} \n')
    allowance = account.allowance(arb, arb.usdc_contract, arb.inch_contract)
    if allowance > amount:
        print(f'Достаточно разрешения {divider(allowance)} USDC для обмена на USDT')
    else:
        print(f'Не достаточно разрешения. Текущее кол-во: {divider(allowance)} USDC, необходимо {divider(amount)} USDC')
        print('Даем разрешение на трату')
        account.approve(arb, arb.usdc_contract, arb.inch_contract, amount)
    print(f'Меняем {divider(amount)} USDC на USDT')
    account.swap_1inch(arb, arb.usdc_contract, arb.usdt_contract, amount)

    amount = account.balanceOf(arb, arb.usdt_contract)
    print(f'Arbitrum USDT: {divider(amount)} \n')
    allowance = account.allowance(arb, arb.usdt_contract, arb.stargate_router)
    if allowance > amount:
        print(f'Достаточно разрешения {divider(allowance)} USDT для добавления в пул stargate')
    else:
        print(f'Не достаточно разрешения. Текущее кол-во: {divider(allowance)} USDC, необходимо {divider(amount)} USDC')
        print('Даем разрешение на трату')
        account.approve(arb, arb.usdt_contract, arb.stargate_router, amount)
    print(f'Меняем {divider(amount)} USDC на USDT')
    print(f'Добавляем {divider(amount)} USDT в пул stargate')
    account.lz_addLiq(arb, arb.usdt_contract, amount, 2)

    get_all_stable_balances(account)
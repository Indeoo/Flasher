import asyncio
import copy

from config import AETHIR_ABI, CYBERV_ABI, TOKENS_PER_CHAIN
from modules import Logger, Aggregator
from settings import MEMCOIN_AMOUNT, CYBERV_NFT_COUNT, NODE_COUNT, NODE_TIER_MAX, NODE_TIER_BUY, NODE_TRYING_WITHOUT_REF
from utils.tools import helper, get_wallet_for_deposit


class Custom(Logger, Aggregator):
    def __init__(self, client):
        Logger.__init__(self)
        Aggregator.__init__(self, client)
        self.stop_flag = False
        self.signed_tx = None

    async def swap(self):
        pass

    @helper
    async def buy_memecoin_thruster(self):
        from functions import swap_thruster

        amount = MEMCOIN_AMOUNT
        amount_in_wei = self.client.to_wei(amount, 18)
        data = 'ETH', 'MEMCOIN', f"{amount:.2f}", amount_in_wei

        return await swap_thruster(self.client, swapdata=data)

    @helper
    async def sell_memecoin_thruster(self):
        from functions import swap_thruster

        await self.client.initialize_account()

        amount_in_wei, amount, _ = await self.client.get_token_balance('MEMCOIN', check_symbol=False)
        data = 'MEMCOIN', 'ETH', f"{amount:.2f}", amount_in_wei

        return await swap_thruster(self.client, swapdata=data)

    async def buy_node_util(self, contract_address, price, index, approve_mode, tx_params=None):

        node_contract = self.client.get_contract(contract_address, AETHIR_ABI)

        if not isinstance(NODE_COUNT, int):
            raise RuntimeError('NODE_COUNT should ne a digit! (NODE_COUNT = 10)')

        if not approve_mode:
            self.logger_msg(*self.client.acc_info, msg=f"Trying to buy Carv Node Tier #{index}")
        else:
            self.logger_msg(*self.client.acc_info, msg=f"Approve for buying Carv Node Tier #{index}")

        total_price = int(price * NODE_COUNT * 10 ** 18)
        total_count = int(NODE_COUNT * 10 ** 18)
        ref_flag = False

        weth_address = TOKENS_PER_CHAIN['Arbitrum']['WETH']

        if approve_mode:
            result = await self.client.check_for_approved(weth_address, node_contract.address, without_bal_check=True)
            await asyncio.sleep(1)
            return result

        try:
            transaction = await node_contract.functions.whitelistedPurchaseWithCode(
                total_price,
                [],
                total_price,
                'cryptoearn',
            ).build_transaction(tx_params)
            ref_flag = True
        except Exception as error:
            try:
                self.logger_msg(*self.client.acc_info, msg=f"Method#1. {error}", type_msg='error')
                transaction = await node_contract.functions.whitelistedPurchaseWithCode(
                    total_price,
                    [],
                    total_count,
                    'cryptoearn',
                ).build_transaction(tx_params)
                ref_flag = True
            except Exception as error:
                if NODE_TRYING_WITHOUT_REF:
                    try:
                        self.logger_msg(*self.client.acc_info, msg=f"Method#2. {error}", type_msg='error')
                        transaction = await node_contract.functions.whitelistedPurchase(
                            total_price,
                            [],
                            total_count,
                        ).build_transaction(tx_params)
                    except Exception as error:
                        try:
                            self.logger_msg(*self.client.acc_info, msg=f"Method#3. {error}", type_msg='error')
                            transaction = await node_contract.functions.whitelistedPurchase(
                                total_price,
                                [],
                                total_price,
                            ).build_transaction(tx_params)
                        except Exception as error:
                            self.logger_msg(*self.client.acc_info, msg=f"Method#4. {error}", type_msg='error')
                            return False
                else:
                    self.logger_msg(*self.client.acc_info, msg=f"Method#2. {error}", type_msg='error')
                    return False

        tx = await self.client.send_transaction(transaction)

        if tx:
            if ref_flag:
                self.logger_msg(
                    *self.client.acc_info, msg=f"Tier #{index} was bought with 10% discount", type_msg='success'
                )
            else:
                self.logger_msg(
                    *self.client.acc_info, msg=f"Tier #{index} was bought", type_msg='success'
                )
            return True
        return False

    @helper
    async def buy_node(self, approve_mode: bool = False):
        nodes_data = {
            1: ("0x80adA4D9F18996c19df7d07aCfE78f9460BBC151", 0.1316),
            2: ("0x82720570AC1847FD161b5A01Fe6440c316e5742c", 0.1580),
            3: ("0x3F3C6DE3Bbe1F2fdFb4B43a49e599885B7Fb1a27", 0.1817),
            4: ("0xc674BEB2f5Cd94A748589A9Dadd838b9E09AABD4", 0.2071),
            5: ("0xF8a8A71d90f1AE2F17Aa4eE9319820B5F394f629", 0.2340),
            6: ("0x125711d6f0AAc9DFFEd75AD2B8C51bDaF5FAEd71", 0.2633),
            7: ("0x3371b74beC1dE3E115A4148956F94f55bEA8cD00", 0.2962),
            8: ("0xa1D3632C9Dc73e8EcEBAe99a8Ea00F50F226A8B9", 0.3332),
            9: ("0xD7C3E0C20Ab22f1e9A59e764B1b562E1dD7438B0", 0.3749)
        }

        if NODE_TIER_BUY != 0:
            new_nodes_data = copy.deepcopy(nodes_data[NODE_TIER_BUY])
        else:
            new_nodes_data = copy.deepcopy(nodes_data)

        if approve_mode:
            for index in range(1, 10):
                contract_address, price = nodes_data[index]
                await self.buy_node_util(
                    contract_address=contract_address, price=price, index=index, approve_mode=approve_mode
                )
            return True

        tx_params = await self.client.prepare_transaction()

        if isinstance(new_nodes_data, tuple):
            contract_address, price = new_nodes_data
            while True:
                result = await self.buy_node_util(
                    contract_address=contract_address, price=price, index=NODE_TIER_BUY, approve_mode=False,
                    tx_params=tx_params
                )
                if result:
                    break
        else:
            result = False
            while True:
                for index in range(1, NODE_TIER_MAX + 1):
                    contract_address, price = new_nodes_data[index]
                    result = await self.buy_node_util(
                        contract_address=contract_address, price=price, index=index, approve_mode=False,
                        tx_params=tx_params
                    )

                    if not result:
                        self.logger_msg(
                            *self.client.acc_info, msg=f"Can`t buy Carv Node Tier #{index}", type_msg='warning'
                        )
                    else:
                        break

                if result:
                    break

        return True

    @helper
    async def buy_cyberv(self, public_mode:bool = False):
        mint_addresses = '0x67CE4afa08eBf2D6d1f31737cc5D54Ff116205e9'
        sale_price = int(127000000000000000 * CYBERV_NFT_COUNT)

        url = f'https://api-nft.gmnetwork.ai/nft/whitelist/?collection_name=CyberV&address={self.client.address}'

        response = await self.make_request(url=url)

        if response['success']:

            if response['result']['signature'] != '' or public_mode:
                signature = self.client.w3.to_bytes(hexstr=response['result']['signature'])

                self.logger_msg(
                    *self.client.acc_info, msg=f'Mint CyberV NFT, signature: {self.client.w3.to_hex(signature)[:10]}...'
                )

                signature = self.client.w3.to_bytes(hexstr=response['result']['signature'])
                mint_contract = self.client.get_contract(mint_addresses, CYBERV_ABI)

                transaction = await mint_contract.functions.mint(
                    CYBERV_NFT_COUNT,
                    signature if not public_mode else '0x'
                ).build_transaction(await self.client.prepare_transaction(value=sale_price))

                return await self.client.send_transaction(transaction)

            raise RuntimeError('Signature is not exist')
        raise RuntimeError('Bad request to CyberV API')

    async def claim_and_transfer_imx(self):
        claim_contract = '0x3f04d7a7297d5535595eE0a30071008B54E62A03'

        self.logger_msg(
            *self.client.acc_info, msg=f'Claim 3 daily gems on IMX.Community'
        )

        claim_tx = await self.client.prepare_transaction() | {
            'to': claim_contract,
            'data': '0xae56842b'
        }

        claim_result = await self.client.send_transaction(claim_tx)
        dep_address = get_wallet_for_deposit(self)

        imx_balance_in_wei, imx_balance, _ = await self.client.get_token_balance('IMX')
        imx_balance -= 0.001
        imx_balance_in_wei = self.client.to_wei(imx_balance)

        self.logger_msg(
            *self.client.acc_info, msg=f'Send {imx_balance} IMX to {dep_address}'
        )

        send_tx = await self.client.prepare_transaction(value=imx_balance_in_wei) | {
            'to': dep_address
        }

        dep_result = await self.client.send_transaction(send_tx)

        return all([claim_result, dep_result])





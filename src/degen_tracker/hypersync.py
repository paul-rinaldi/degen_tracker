import asyncio
import hypersync
import polars as pl
from dataclasses import dataclass, field
from typing import List
from hypersync import TransactionField, HypersyncClient, LogField


@dataclass
class Hypersync:
    client: HypersyncClient = field(
        default_factory=lambda: HypersyncClient("https://base.hypersync.xyz"))
    transactions: List[hypersync.TransactionField] = field(
        default_factory=list)
    blocks: List[hypersync.BlockField] = field(default_factory=list)

    def convert_hex_to_float(self, hex: str) -> float:
        """
        Converts hexadecimal values in a transaction dictionary to integers, skipping specific keys.

        Args:
        transaction (dict): A dictionary containing transaction data, where some values are hexadecimals.

        Returns:
        dict: A new dictionary with hexadecimals converted to integers, excluding specified keys.
        """
        # Only convert hex strings; leave other values as is
        if isinstance(hex, str) and hex.startswith("0x"):
            # Convert hex string to float
            return float(int(hex, 16))

    def sync_erc20s(self, sync_all=False) -> dict[str]:
        """
        sync_erc20s() is a synchronous wrapper function around the asynchronous fetch_erc20s() function.

        sync is a boolean value that determines whether to sync all erc20 transfers from block 0 or from the latest block. It is False by default. 
        If false, it will simply sync to the block head.

        Returns:
            dict: A dictionary containing the following keys:
                {
                    "tx_data": tx_data,
                    "decoded_log_data": decoded_log_data,
                    "log_data": log_data,
                    "block_data": block_data
                }
        """
        match sync_all:
            case True:
                return asyncio.run(self.fetch_erc20s(sync_all=True))
            case False:
                return asyncio.run(self.fetch_erc20s(sync_all=False))

    async def fetch_erc20s(self, sync_all=False) -> dict[str]:
        """
        - TODO get latest block header from lance database and update

        Returns:
            dict: A dictionary containing the following keys:
                {
                    "tx_data": tx_data,
                    "decoded_log_data": decoded_log_data,
                    "log_data": log_data,
                    "block_data": block_data
                }
        """
        # Get the current block height from the blockchain.
        height = await self.client.get_height()

        match sync_all:
            case True:
                query = hypersync.Query(
                    # Full sync
                    from_block=0,
                    to_block=height,
                    logs=[hypersync.LogSelection(
                        # We want All ERC20 transfers so no address filter and only a filter for the first topic
                        topics=[
                            ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]]
                    )],
                    field_selection=hypersync.FieldSelection(
                        log=[el.value for el in LogField],
                        transaction=[TransactionField.BLOCK_NUMBER,
                                     TransactionField.TRANSACTION_INDEX,
                                     TransactionField.HASH,
                                     TransactionField.FROM,
                                     TransactionField.TO
                                     ],
                        block=[el.value for el in hypersync.BlockField]
                    )
                )
            case False:
                query = hypersync.Query(
                    # Full sync
                    # from_block=0,
                    # to_block=height,
                    from_block=height - 3000,
                    logs=[hypersync.LogSelection(
                        # We want All ERC20 transfers so no address filter and only a filter for the first topic
                        topics=[
                            ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]]
                    )],
                    field_selection=hypersync.FieldSelection(
                        log=[el.value for el in LogField],
                        transaction=[TransactionField.BLOCK_NUMBER,
                                     TransactionField.TRANSACTION_INDEX,
                                     TransactionField.HASH,
                                     TransactionField.FROM,
                                     TransactionField.TO
                                     ],
                        block=[el.value for el in hypersync.BlockField]
                    )
                )

        print("Running the query...")

        # DATA ORGANIZTION
        tx_data = []
        decoded_log_data = []
        log_data = []
        block_data = []

        # While loop for pagination
        while True:
            res = await self.client.send_req(query)

            # ABI is required to decode logs
            with open('./abis/erc20.json', 'r') as json_file:
                abi = json_file.read()

            # Map of contract_address -> abi
            abis = {}

            for log in res.data.logs:
                abis[log.address] = abi

            # Create a decoder with our mapping
            decoder = hypersync.Decoder(abis)

            # Decode the log on a background thread so we don't block the event loop.
            # Can also use decoder.decode_logs_sync if it is more convenient.
            decoded_logs = await decoder.decode_logs(res.data.logs)

            tx_data += res.data.transactions
            decoded_log_data += decoded_logs
            log_data = res.data.logs
            block_data += res.data.blocks

            print('out of for loop?')
            # Check if the fetched data has reached the current archive height or next block.
            if res.archive_height < res.next_block:
                break

            # Update the query to fetch the next set of data starting from the next block.
            query.from_block = res.next_block
            print(f"Scanned up to block {query.from_block}")  # Log progress.

            print("# of logs", len(log_data))
            print('# of blocks', len(block_data))

            return {
                "tx_data": tx_data,
                "decoded_log_data": decoded_log_data,
                "log_data": log_data,
                "block_data": block_data
            }